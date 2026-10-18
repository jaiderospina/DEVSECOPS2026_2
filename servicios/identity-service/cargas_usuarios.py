"""Lotes Excel reanudables para ADMIN_SOPORTE. Cada fila confirma su propia transacción."""
import json
from contextlib import contextmanager
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine
from seguridad import requiere_roles, SESSION_INACTIVITY_MINUTES
from usuarios import IdentidadCrear, _crear_identidad
from correo import validar_configuracion_correo
from cargas_excel import ExcelInvalido, MAX_FILE_BYTES, leer_usuarios, plantilla_excel, resultado_excel

router = APIRouter(prefix="/usuarios/cargas", tags=["Carga masiva Excel"])
bulk_actor = requiere_roles("ADMIN_SOPORTE")
@contextmanager
def bulk_transaction():
    try:
        with engine.begin() as connection:
            yield connection
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo consultar el lote. Verifique la migración y la disponibilidad del servicio.") from None

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def soporte_vigente(connection, actor, compania_id=None):
    session_id = actor.get("session_id")
    if not session_id:
        raise HTTPException(403, "Se requiere una sesión de soporte con MFA.")
    active = connection.execute(text("""
        SELECT u.id FROM usuarios_plataforma u
        JOIN credenciales cr ON cr.usuario_id = u.id
        JOIN sesiones s ON s.usuario_id = u.id
        JOIN mfa_totp m ON m.usuario_id = u.id
        WHERE u.id = :uid AND s.id = :sid AND u.activo
          AND cr.activo AND NOT cr.bloqueado AND NOT cr.requiere_cambio_password
          AND (cr.password_expira_en IS NULL OR cr.password_expira_en > NOW())
          AND m.activo AND NOT s.revocada AND s.fecha_expiracion > NOW()
          AND COALESCE(s.ultima_actividad, s.fecha_inicio) >
              NOW() - (:idle * INTERVAL '1 minute')
        FOR SHARE OF u, cr, s, m
    """), {"uid": actor["id"], "sid": session_id, "idle": SESSION_INACTIVITY_MINUTES}).first()
    if not active:
        raise HTTPException(403, "La sesión no permite importar identidades.")
    roles = connection.execute(text("""
        SELECT r.nombre FROM usuario_roles_plataforma ur
        JOIN roles_plataforma r ON r.id = ur.rol_id
        WHERE ur.usuario_id = :uid AND r.activo
        FOR SHARE OF ur, r
    """), {"uid": actor["id"]}).scalars().all()
    if roles != ["ADMIN_SOPORTE"]:
        raise HTTPException(403, "Solo ADMIN_SOPORTE puede importar líderes.")
    if compania_id is not None:
        company = connection.execute(text("""
            SELECT c.id, c.codigo, c.nombre FROM companias c
            JOIN usuario_companias_plataforma uc ON uc.compania_id = c.id
            WHERE c.id = :cid AND uc.usuario_id = :uid AND c.activo
            FOR SHARE OF c, uc
        """), {"cid": compania_id, "uid": actor["id"]}).mappings().first()
        if not company:
            raise HTTPException(403, "La compañía no está activa o no pertenece a su alcance.")
        return dict(company)
    return None

def carga_propia(connection, carga_id, actor, lock=False):
    query = text("""
        SELECT * FROM cargas_usuarios WHERE id = :id AND actor_usuario_id = :uid
          AND conservar_hasta > NOW()
    """)
    if lock:
        query = text("""
            SELECT * FROM cargas_usuarios WHERE id = :id AND actor_usuario_id = :uid
              AND conservar_hasta > NOW() FOR UPDATE
        """)
    job = connection.execute(query, {"id": carga_id, "uid": actor["id"]}).mappings().first()
    if job is None:
        raise HTTPException(404, "Lote no encontrado o no disponible.")
    company = soporte_vigente(connection, actor, job["compania_id"])
    return dict(job), company

def filas(connection, carga_id):
    return [dict(row) for row in connection.execute(text("""
        SELECT fila, datos, estado, codigo, mensaje, usuario_id
        FROM cargas_usuario_filas WHERE carga_id = :id ORDER BY fila
    """), {"id": carga_id}).mappings()]

def respuesta(connection, job, company, include_rows=True):
    rows = filas(connection, job["id"])
    counts = {state.lower(): sum(row["estado"] == state for row in rows)
              for state in ("INVALIDA", "PENDIENTE", "CREADA", "ERROR")}
    return {"id": str(job["id"]), "estado": job["estado"],
            "compania": company, "creada_en": job["creada_en"].isoformat(),
            "confirmar_antes": job["confirmar_antes"].isoformat(),
            "resumen": {"total": len(rows), **counts},
            **({"filas": rows} if include_rows else {})}

def evento(connection, tipo, actor, company_id, carga_id, detalle=None, usuario_id=None):
    # Diccionario construido en servidor: no contiene correos, archivos ni credenciales.
    safe = {"carga_id": str(carga_id), **(detalle or {})}
    connection.execute(text("""
        INSERT INTO auditoria_outbox(
          evento_uuid, fecha_evento, servicio, evento, resultado,
          actor_usuario_id, objetivo_usuario_id, compania_id, detalle)
        VALUES (:event_id, NOW(), 'identity', :type, 'EXITO', :actor, :user, :company,
                CAST(:detail AS JSONB))
    """), {"event_id": uuid4(), "type": tipo, "actor": actor["id"], "user": usuario_id,
           "company": company_id, "detail": json.dumps(safe)})

@router.get("/plantilla")
def descargar_plantilla(actor=Depends(bulk_actor)):
    with bulk_transaction() as c:
        soporte_vigente(c, actor)
    return Response(plantilla_excel(), media_type=XLSX_TYPE,
                    headers={"Content-Disposition": 'attachment; filename="plantilla-usuarios.xlsx"',
                             "Cache-Control": "no-store"})

@router.post("/validar", status_code=201)
async def validar_excel(compania_id: int = Form(gt=0), archivo: UploadFile = File(),
                        actor=Depends(bulk_actor)):
    with bulk_transaction() as c:
        soporte_vigente(c, actor, compania_id)
    try:
        content = await archivo.read(MAX_FILE_BYTES + 1)
        rows = leer_usuarios(content, archivo.filename or "", compania_id)
    except ExcelInvalido as error:
        raise HTTPException(422, str(error)) from None
    finally:
        await archivo.close()
    load_id = uuid4()
    with bulk_transaction() as c:
        company = soporte_vigente(c, actor, compania_id)
        # Limpieza oportunista del historial de lotes; nunca elimina usuarios.
        c.execute(text("DELETE FROM cargas_usuarios WHERE conservar_hasta < NOW()"))
        c.execute(text("SELECT pg_advisory_xact_lock(837200, :uid)"), {"uid": actor["id"]})
        recent = c.execute(text("""
            SELECT count(*) FROM cargas_usuarios
            WHERE actor_usuario_id = :uid AND creada_en > NOW() - INTERVAL '10 minutes'
        """), {"uid": actor["id"]}).scalar_one()
        if recent >= 10:
            raise HTTPException(429, "Espere antes de validar otro lote.")
        valid = [row for row in rows if row["estado"] == "PENDIENTE"]
        if valid:
            existing = c.execute(text("""
                SELECT BTRIM(id_externo) AS id_externo, LOWER(BTRIM(email)) AS email
                FROM usuarios_plataforma
                WHERE BTRIM(id_externo) = ANY(:ids) OR LOWER(BTRIM(email)) = ANY(:emails)
            """), {"ids": [row["datos"]["id_externo"] for row in valid],
                   "emails": [row["datos"]["email"] for row in valid]}).mappings().all()
            ids = {row["id_externo"] for row in existing}
            emails = {row["email"] for row in existing}
            active_roles = set(c.execute(text(
                "SELECT nombre FROM roles_plataforma WHERE activo")).scalars())
            for row in valid:
                if row["datos"]["id_externo"] in ids or row["datos"]["email"] in emails:
                    row.update(estado="INVALIDA", codigo="YA_REGISTRADA",
                               mensaje="Identificación o correo ya registrado; no se modifica la cuenta existente.")
                elif row["datos"]["rol"] not in active_roles:
                    row.update(estado="INVALIDA", codigo="ROL_INACTIVO", mensaje="El rol no está disponible.")
        job = dict(c.execute(text("""
            INSERT INTO cargas_usuarios(id, actor_usuario_id, compania_id)
            VALUES (:id, :uid, :cid) RETURNING *
        """), {"id": load_id, "uid": actor["id"], "cid": compania_id}).mappings().one())
        c.execute(text("""
            INSERT INTO cargas_usuario_filas(carga_id, fila, datos, estado, codigo, mensaje)
            VALUES (:id, :fila, CAST(:datos AS JSONB), :estado, :codigo, :mensaje)
        """), [{"id": load_id, **{key: row[key] for key in ("fila", "estado", "codigo", "mensaje")},
               "datos": json.dumps(row["datos"])} for row in rows])
        evento(c, "CARGA_USUARIOS_VALIDADA", actor, compania_id, load_id,
               {"filas": len(rows), "validas": sum(row["estado"] == "PENDIENTE" for row in rows)})
        return respuesta(c, job, company)

@router.get("")
def listar_cargas(compania_id: int, actor=Depends(bulk_actor)):
    with bulk_transaction() as c:
        company = soporte_vigente(c, actor, compania_id)
        jobs = c.execute(text("""
            SELECT * FROM cargas_usuarios WHERE actor_usuario_id = :uid AND compania_id = :cid
              AND conservar_hasta > NOW() ORDER BY creada_en DESC LIMIT 10
        """), {"uid": actor["id"], "cid": compania_id}).mappings().all()
        return {"cargas": [respuesta(c, dict(job), company, False) for job in jobs]}

@router.get("/{carga_id}")
def obtener_carga(carga_id: UUID, actor=Depends(bulk_actor)):
    with bulk_transaction() as c:
        job, company = carga_propia(c, carga_id, actor)
        return respuesta(c, job, company)

@router.get("/{carga_id}/resultado")
def descargar_resultado(carga_id: UUID, actor=Depends(bulk_actor)):
    with bulk_transaction() as c:
        job, _ = carga_propia(c, carga_id, actor)
        rows = filas(c, job["id"])
    return Response(resultado_excel(rows), media_type=XLSX_TYPE,
                    headers={"Content-Disposition": 'attachment; filename="resultado-carga.xlsx"',
                             "Cache-Control": "no-store"})

class ConfirmarCarga(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmar: StrictBool

@router.post("/{carga_id}/confirmar")
def confirmar_carga(carga_id: UUID, datos: ConfirmarCarga, actor=Depends(bulk_actor)):
    if not datos.confirmar:
        raise HTTPException(400, "Confirme la importación de las filas válidas.")
    with bulk_transaction() as c:
        job, company = carga_propia(c, carga_id, actor, True)
        try:
            validar_configuracion_correo()
        except Exception:
            raise HTTPException(503, "Configure el correo de Identity antes de importar; no se han creado nuevas cuentas.") from None
        if job["estado"] == "VALIDADA":
            expired = c.execute(text(
                "SELECT confirmar_antes <= NOW() FROM cargas_usuarios WHERE id = :id"),
                {"id": carga_id}).scalar_one()
            if expired:
                raise HTTPException(409, "La validación venció. Vuelva a validar el Excel.")
            if not any(row["estado"] == "PENDIENTE" for row in filas(c, carga_id)):
                raise HTTPException(409, "El lote no tiene filas válidas pendientes.")
            c.execute(text("UPDATE cargas_usuarios SET estado = 'CONFIRMADA' WHERE id = :id"), {"id": carga_id})
            job["estado"] = "CONFIRMADA"
            evento(c, "CARGA_USUARIOS_CONFIRMADA", actor, job["compania_id"], carga_id)
        return respuesta(c, job, company)

class ContextoCarga:
    def __init__(self, carga_id, fila, actor):
        self.carga_id, self.fila, self.actor = carga_id, fila, actor

    def iniciar(self, connection):
        job, _ = carga_propia(connection, self.carga_id, self.actor)
        if job["estado"] != "CONFIRMADA":
            raise HTTPException(409, "Confirme primero las filas válidas del lote.")
        row = connection.execute(text("""
            SELECT * FROM cargas_usuario_filas WHERE carga_id = :id AND fila = :fila FOR UPDATE
        """), {"id": self.carga_id, "fila": self.fila}).mappings().first()
        if row is None:
            raise HTTPException(404, "Fila no encontrada.")
        if row["estado"] == "CREADA":
            return row["usuario_id"] or 0
        if row["estado"] != "PENDIENTE":
            raise HTTPException(409, "La fila ya tiene un resultado o no es importable.")
        self.compania_id = job["compania_id"]
        return None

    def completar(self, connection, usuario_id, rol, vistas_iniciales):
        connection.execute(text("""
            UPDATE cargas_usuario_filas SET estado = 'CREADA', codigo = 'CREADA',
              mensaje = 'Cuenta creada con las tres vistas de su área habilitadas; contraseña temporal enviada por el flujo de correo.',
              usuario_id = :uid, procesada_en = NOW()
            WHERE carga_id = :id AND fila = :fila
        """), {"uid": usuario_id, "id": self.carga_id, "fila": self.fila})
        evento(connection, "USUARIO_CREADO", self.actor, self.compania_id, self.carga_id,
               {"fila": self.fila, "rol": rol, "operacion_sync": "PROVISIONAR",
                "requiere_cambio_password": True, "vistas_iniciales_habilitadas": vistas_iniciales}, usuario_id)

@router.post("/{carga_id}/filas/{fila}")
def importar_fila(carga_id: UUID, fila: int, actor=Depends(bulk_actor)):
    with bulk_transaction() as c:
        job, _ = carga_propia(c, carga_id, actor)
        if job["estado"] != "CONFIRMADA":
            raise HTTPException(409, "Confirme primero el lote.")
        row = c.execute(text("""
            SELECT fila, datos, estado, codigo, mensaje, usuario_id
            FROM cargas_usuario_filas WHERE carga_id = :id AND fila = :fila
        """), {"id": carga_id, "fila": fila}).mappings().first()
        if row is None:
            raise HTTPException(404, "Fila no encontrada.")
        if row["estado"] != "PENDIENTE":
            return {"fila": dict(row)}
        data = IdentidadCrear(**row["datos"], compania_id=job["compania_id"])
    context = ContextoCarga(carga_id, fila, actor)
    failure = None
    try:
        _crear_identidad(data, actor, contexto_carga=context)
    except HTTPException as error:
        if error.status_code in (401, 403, 404):
            raise
        if error.status_code != 409:
            failure = ("CREACION_RECHAZADA", "No se pudo crear la cuenta con los datos y rol vigentes.")
        else:
            failure = ("CONFLICTO", "La fila cambió o la identificación/correo ya están registrados.")
    except Exception:
        # No incluir el texto de excepciones SMTP/SQL: puede contener datos sensibles.
        failure = ("CREACION_FALLIDA", "La creación no se confirmó. Revise correo/configuración antes de validar otro lote.")
    with bulk_transaction() as c:
        carga_propia(c, carga_id, actor)
        if failure:
            c.execute(text("""
                UPDATE cargas_usuario_filas SET estado = 'ERROR', codigo = :code,
                  mensaje = :message, procesada_en = NOW()
                WHERE carga_id = :id AND fila = :fila AND estado = 'PENDIENTE'
            """), {"id": carga_id, "fila": fila, "code": failure[0], "message": failure[1]})
        result = c.execute(text("""
            SELECT fila, datos, estado, codigo, mensaje, usuario_id
            FROM cargas_usuario_filas WHERE carga_id = :id AND fila = :fila
        """), {"id": carga_id, "fila": fila}).mappings().one()
        return {"fila": dict(result)}
