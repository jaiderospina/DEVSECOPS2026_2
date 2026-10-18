   # -----------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import engine
from seguridad import (
    requiere_compania,
    requiere_roles,
)
from auditoria import (
    registrar_evento,
    COMPANIA_ASIGNADA,
    COMPANIA_CREADA,
    COMPANIA_DESASIGNADA,
    COMPANIA_ESTADO_MODIFICADO,
    COMPANIA_MODIFICADA,
    COMPANIA_REASIGNADA,
)
from sync_jobs import encolar_sync_job


router = APIRouter(
    prefix="/companias",
    tags=["Compañías"]
)


# ============================================================
# MODELOS DE ENTRADA
# ============================================================

class CompaniaCrear(BaseModel):

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar_codigo(cls, valor):
        if isinstance(valor, str):
            return valor.strip().upper()
        return valor

    @field_validator("nombre", mode="before")
    @classmethod
    def normalizar_nombre(cls, valor):
        if isinstance(valor, str):
            return " ".join(valor.strip().split())
        return valor

    @field_validator("descripcion", mode="before")
    @classmethod
    def normalizar_descripcion(cls, valor):
        if isinstance(valor, str):
            valor = " ".join(valor.strip().split())
            return valor or None
        return valor
    # ---------------------------------------------------------
    # DATOS BÁSICOS DE LA COMPAÑÍA
    # ---------------------------------------------------------
    # Estas validaciones evitan recibir códigos o nombres
    # vacíos y limitan el tamaño de los datos antes de que
    # sean procesados y almacenados en PostgreSQL.
    # ---------------------------------------------------------

    codigo: str = Field(
        min_length=1,
        max_length=50
    )

    nombre: str = Field(
        min_length=1,
        max_length=150
    )

    descripcion: str | None = Field(
        default=None,
        max_length=500
    )


class CompaniaEstado(BaseModel):
    activo: bool


class CompaniaModificar(CompaniaCrear):
    # Reutiliza las mismas reglas de normalización y longitud
    # utilizadas al crear una compañía. El estado se mantiene
    # separado en /{compania_id}/estado.
    pass


class AsignarCompaniaUsuario(BaseModel):
    usuario_id: int
    compania_id: int


# ============================================================
# CREAR COMPAÑÍA
# ============================================================
# En el nuevo modelo académico, únicamente ADMIN_TI puede
# crear compañías.
#
# requiere_roles también comprueba que el usuario haya
# reemplazado su contraseña temporal antes de permitir
# operaciones administrativas.
# ============================================================

@router.post("", status_code=201)
def crear_compania(
    datos: CompaniaCrear,
    usuario_actual=Depends(
        requiere_roles("ADMIN_TI")
    )
):
    consulta = text("""
        INSERT INTO companias (
            codigo,
            nombre,
            descripcion,
            activo,
            fecha_creacion,
            fecha_modificacion
        )
        VALUES (
            :codigo,
            :nombre,
            :descripcion,
            TRUE,
            NOW(),
            NOW()
        )
        RETURNING
            id,
            codigo,
            nombre,
            descripcion,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    try:
        with engine.begin() as conexion:
            compania = conexion.execute(
                consulta,
                {
                    "codigo": datos.codigo,
                    "nombre": datos.nombre,
                    "descripcion": datos.descripcion
                }
            ).mappings().one()

        # ----------------------------------------------------
        # AUDITORÍA
        # ----------------------------------------------------
        # Se registra después del COMMIT exitoso. No se incluyen
        # credenciales ni información de autenticación.
        # ----------------------------------------------------

        registrar_evento(
            COMPANIA_CREADA,
            actor_usuario_id=usuario_actual["id"],
            compania_id=compania["id"],
            resultado="EXITO",
            detalle={
                "codigo": compania["codigo"],
                "nombre": compania["nombre"],
                "activo": compania["activo"],
            },
        )

        return dict(compania)

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="El código de compañía ya está registrado"
        )


# ============================================================
# EDITAR DATOS BÁSICOS DE COMPAÑÍA
# ============================================================
# Únicamente ADMIN_TI puede corregir código, nombre y
# descripción. El estado y las asignaciones de ADMIN_SOPORTE
# se administran mediante endpoints separados.
#
# Mantener estas responsabilidades separadas evita que una
# corrección de datos altere accidentalmente el alcance RBAC.
# ============================================================

@router.put("/{compania_id}")
def modificar_compania(
    compania_id: int,
    datos: CompaniaModificar,
    usuario_actual=Depends(
        requiere_roles("ADMIN_TI")
    )
):
    consulta = text("""
        UPDATE companias
        SET
            codigo = :codigo,
            nombre = :nombre,
            descripcion = :descripcion,
            fecha_modificacion = NOW()
        WHERE id = :compania_id
        RETURNING
            id,
            codigo,
            nombre,
            descripcion,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    try:
        with engine.begin() as conexion:
            compania = conexion.execute(
                consulta,
                {
                    "compania_id": compania_id,
                    "codigo": datos.codigo,
                    "nombre": datos.nombre,
                    "descripcion": datos.descripcion,
                },
            ).mappings().first()

        if compania is None:
            raise HTTPException(
                status_code=404,
                detail="Compañía no encontrada",
            )

        # ----------------------------------------------------
        # AUDITORÍA
        # ----------------------------------------------------
        # Se registran los campos administrativos modificados,
        # sin incorporar datos de autenticación o secretos.
        # ----------------------------------------------------

        registrar_evento(
            COMPANIA_MODIFICADA,
            actor_usuario_id=usuario_actual["id"],
            compania_id=compania_id,
            resultado="EXITO",
            detalle={
                "campos_modificados": [
                    "codigo",
                    "nombre",
                    "descripcion",
                ],
            },
        )

        return dict(compania)

    except HTTPException:
        raise

    except IntegrityError:
        # No se exponen nombres de restricciones o índices.
        raise HTTPException(
            status_code=409,
            detail="El código de compañía ya está registrado",
        )


# ============================================================
# LISTAR COMPAÑÍAS
# ============================================================
# ADMIN_TI:
#   Puede consultar todas las compañías, tanto activas como
#   inactivas. Esto es necesario porque también administra
#   su habilitación y deshabilitación.
#
# ADMIN_SOPORTE:
#   Únicamente puede consultar las compañías activas que
#   tenga expresamente asignadas.
#
# La separación mantiene el aislamiento multitenant y evita
# que un usuario de soporte descubra compañías fuera de su
# ámbito administrativo.
# ============================================================

@router.get("")
def obtener_companias(
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    roles_usuario = usuario_actual.get(
        "roles",
        []
    )

    # --------------------------------------------------------
    # ADMIN_TI — VISIBILIDAD GLOBAL
    # --------------------------------------------------------
    if "ADMIN_TI" in roles_usuario:
        consulta = text("""
            SELECT
                c.id,
                c.codigo,
                c.nombre,
                c.descripcion,
                c.activo,
                c.fecha_creacion,
                c.fecha_modificacion
            FROM companias c
            ORDER BY c.nombre
        """)

        with engine.connect() as conexion:
            resultado = conexion.execute(
                consulta
            )

            companias = [
                dict(compania)
                for compania in resultado.mappings().all()
            ]

        return {
            "total": len(companias),
            "companias": companias
        }

    # --------------------------------------------------------
    # ADMIN_SOPORTE — VISIBILIDAD MULTITENANT
    # --------------------------------------------------------
    # Solo se devuelven compañías:
    #
    # 1. asignadas explícitamente al usuario;
    # 2. que actualmente estén activas.
    #
    # DISTINCT evita duplicados defensivamente.
    # --------------------------------------------------------

    consulta = text("""
        SELECT DISTINCT
            c.id,
            c.codigo,
            c.nombre,
            c.descripcion,
            c.activo,
            c.fecha_creacion,
            c.fecha_modificacion
        FROM companias c
        JOIN usuario_companias_plataforma uc
            ON uc.compania_id = c.id
        WHERE uc.usuario_id = :usuario_id
          AND c.activo = TRUE
        ORDER BY c.nombre
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "usuario_id": usuario_actual["id"]
            }
        )

        companias = [
            dict(compania)
            for compania in resultado.mappings().all()
        ]

    return {
        "total": len(companias),
        "companias": companias
    }

# ============================================================
# ============================================================
# ASIGNAR / REASIGNAR COMPAÑÍA A ADMIN_SOPORTE
# ============================================================
# Únicamente ADMIN_TI puede administrar esta relación.
#
# REGLA DE SEGURIDAD / MÍNIMO PRIVILEGIO:
# - Un ADMIN_SOPORTE puede administrar varias compañías.
# - Cada compañía puede tener como máximo un ADMIN_SOPORTE
#   responsable a la vez.
# - Al reasignar una compañía, el ADMIN_SOPORTE anterior pierde
#   inmediatamente esa relación de autorización.
# - Las identidades internas de la compañía NO se eliminan.
#
# La reasignación se ejecuta dentro de una única transacción.
# Además, la fila de la compañía se bloquea con FOR UPDATE para
# serializar reasignaciones concurrentes sobre la misma compañía.
# ============================================================

@router.post("/asignaciones", status_code=201)
def asignar_compania(
    datos: AsignarCompaniaUsuario,
    usuario_actual=Depends(
        requiere_roles("ADMIN_TI")
    )
):
    # --------------------------------------------------------
    # CONSULTAS DE VALIDACIÓN
    # --------------------------------------------------------
    consulta_usuario = text("""
        SELECT
            u.id,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo,
            ARRAY_AGG(r.nombre ORDER BY r.nombre) AS roles
        FROM usuarios_plataforma u
        LEFT JOIN usuario_roles_plataforma ur
            ON ur.usuario_id = u.id
        LEFT JOIN roles_plataforma r
            ON r.id = ur.rol_id
           AND r.activo = TRUE
        WHERE u.id = :usuario_id
        GROUP BY
            u.id,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo
    """)

    # FOR UPDATE bloquea la compañía durante la transacción.
    # Dos solicitudes simultáneas de reasignación para la misma
    # compañía no pueden modificar su responsable en paralelo.
    consulta_compania_bloqueada = text("""
        SELECT
            id,
            codigo,
            nombre,
            activo
        FROM companias
        WHERE id = :compania_id
        FOR UPDATE
    """)

    # Identifica exclusivamente relaciones pertenecientes a
    # usuarios con rol ADMIN_SOPORTE. Las relaciones de líderes
    # organizacionales quedan fuera de esta consulta.
    consulta_admins_actuales = text("""
        SELECT DISTINCT
            u.id,
            u.id_externo,
            u.nombre
        FROM usuario_companias_plataforma uc
        JOIN usuarios_plataforma u
            ON u.id = uc.usuario_id
        JOIN usuario_roles_plataforma ur
            ON ur.usuario_id = u.id
        JOIN roles_plataforma r
            ON r.id = ur.rol_id
           AND r.activo = TRUE
        WHERE uc.compania_id = :compania_id
          AND r.nombre = 'ADMIN_SOPORTE'
        ORDER BY u.id
    """)

    # Elimina únicamente relaciones administrativas de
    # ADMIN_SOPORTE para la compañía. No toca identidades
    # LIDER_FACTURACION, LIDER_LOGISTICA ni
    # LIDER_GESTION_HUMANA.
    consulta_retirar_admins = text("""
        DELETE FROM usuario_companias_plataforma uc
        WHERE uc.compania_id = :compania_id
          AND EXISTS (
              SELECT 1
              FROM usuario_roles_plataforma ur
              JOIN roles_plataforma r
                ON r.id = ur.rol_id
               AND r.activo = TRUE
              WHERE ur.usuario_id = uc.usuario_id
                AND r.nombre = 'ADMIN_SOPORTE'
          )
    """)

    consulta_asignacion = text("""
        INSERT INTO usuario_companias_plataforma (
            usuario_id,
            compania_id,
            fecha_asignacion
        )
        VALUES (
            :usuario_id,
            :compania_id,
            NOW()
        )
        RETURNING
            id,
            usuario_id,
            compania_id,
            fecha_asignacion
    """)

    try:
        # ----------------------------------------------------
        # TRANSACCIÓN ATÓMICA
        # ----------------------------------------------------
        # Si cualquier paso falla, engine.begin() hace rollback
        # y evita dejar la compañía sin responsable por una
        # reasignación incompleta.
        # ----------------------------------------------------
        with engine.begin() as conexion:
            usuario = conexion.execute(
                consulta_usuario,
                {"usuario_id": datos.usuario_id}
            ).mappings().first()

            if usuario is None:
                raise HTTPException(
                    status_code=404,
                    detail="Usuario no encontrado"
                )

            if not usuario["activo"]:
                raise HTTPException(
                    status_code=400,
                    detail="El usuario se encuentra inactivo"
                )

            roles_usuario = [
                rol
                for rol in (usuario["roles"] or [])
                if rol is not None
            ]

            if roles_usuario != ["ADMIN_SOPORTE"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "La compañía solo puede asignarse "
                        "a un usuario ADMIN_SOPORTE"
                    )
                )

            compania = conexion.execute(
                consulta_compania_bloqueada,
                {"compania_id": datos.compania_id}
            ).mappings().first()

            if compania is None:
                raise HTTPException(
                    status_code=404,
                    detail="Compañía no encontrada"
                )

            if not compania["activo"]:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede asignar una compañía inactiva"
                )

            admins_anteriores = conexion.execute(
                consulta_admins_actuales,
                {"compania_id": datos.compania_id}
            ).mappings().all()

            # Si la compañía ya tiene exclusivamente al mismo
            # ADMIN_SOPORTE, la operación es idempotente: no
            # eliminamos ni recreamos la relación.
            if (
                len(admins_anteriores) == 1
                and admins_anteriores[0]["id"] == datos.usuario_id
            ):
                asignacion_existente = conexion.execute(
                    text("""
                        SELECT
                            id,
                            usuario_id,
                            compania_id,
                            fecha_asignacion
                        FROM usuario_companias_plataforma
                        WHERE usuario_id = :usuario_id
                          AND compania_id = :compania_id
                    """),
                    {
                        "usuario_id": datos.usuario_id,
                        "compania_id": datos.compania_id
                    }
                ).mappings().first()

                return {
                    "mensaje": "La compañía ya está asignada a este ADMIN_SOPORTE",
                    "reasignada": False,
                    "asignacion": dict(asignacion_existente),
                    "usuario": {
                        "id": usuario["id"],
                        "id_externo": usuario["id_externo"],
                        "nombre": usuario["nombre"],
                        "rol": "ADMIN_SOPORTE"
                    },
                    "compania": {
                        "id": compania["id"],
                        "codigo": compania["codigo"],
                        "nombre": compania["nombre"]
                    }
                }

            # Retira todos los ADMIN_SOPORTE anteriores. Esto
            # también sanea datos históricos donde una compañía
            # quedó asociada accidentalmente a más de uno.
            conexion.execute(
                consulta_retirar_admins,
                {"compania_id": datos.compania_id}
            )

            asignacion = conexion.execute(
                consulta_asignacion,
                {
                    "usuario_id": datos.usuario_id,
                    "compania_id": datos.compania_id
                }
            ).mappings().one()

            ids_soporte_afectados = list({
                datos.usuario_id,
                *[
                    admin["id"]
                    for admin in admins_anteriores
                    if admin["id"] != datos.usuario_id
                ]
            })

            if ids_soporte_afectados:
                conexion.execute(
                    text("""
                        UPDATE sesiones
                        SET
                            revocada = TRUE,
                            fecha_revocacion = NOW()
                        WHERE usuario_id = ANY(:usuario_ids)
                          AND revocada = FALSE
                          AND fecha_expiracion > NOW()
                    """),
                    {"usuario_ids": ids_soporte_afectados}
                )

            # ------------------------------------------------
            # SINCRONIZACIÓN ASÍNCRONA / WORKER
            # ------------------------------------------------
            # Los jobs se crean usando la MISMA conexión y la
            # MISMA transacción que modifica las asignaciones.
            #
            # Si la transacción falla, también se revierten los
            # jobs, evitando que el Worker procese un cambio que
            # no quedó confirmado en IAM Secure.
            # ------------------------------------------------

            # Al reasignar una compañía, cada ADMIN_SOPORTE
            # anterior pierde ese alcance y debe ser revocado
            # en el sistema externo.
            for admin in admins_anteriores:
                if admin["id"] == datos.usuario_id:
                    continue

                encolar_sync_job(
                    conexion,
                    operacion="REVOCAR",
                    usuario_id=admin["id"],
                    compania_id=datos.compania_id,
                    solicitado_por_usuario_id=usuario_actual["id"],
                )

            # El nuevo ADMIN_SOPORTE recibe el alcance sobre la
            # compañía. También aplica cuando la compañía no
            # tenía un administrador asignado previamente.
            encolar_sync_job(
                conexion,
                operacion="PROVISIONAR",
                usuario_id=datos.usuario_id,
                compania_id=datos.compania_id,
                solicitado_por_usuario_id=usuario_actual["id"],
            )

        # ----------------------------------------------------
        # AUDITORÍA
        # ----------------------------------------------------
        # Solo se registra cuando hubo una modificación real.
        # La rama idempotente anterior retorna sin generar un
        # evento de cambio porque no altera el estado.
        # ----------------------------------------------------

        registrar_evento(
            (
                COMPANIA_REASIGNADA
                if admins_anteriores
                else COMPANIA_ASIGNADA
            ),
            actor_usuario_id=usuario_actual["id"],
            objetivo_usuario_id=datos.usuario_id,
            compania_id=datos.compania_id,
            resultado="EXITO",
            detalle={
                "admin_soporte_nuevo_id": datos.usuario_id,
                "admins_soporte_retirados_ids": [
                    admin["id"]
                    for admin in admins_anteriores
                    if admin["id"] != datos.usuario_id
                ],
            },
        )

        administradores_retirados = [
            {
                "id": admin["id"],
                "id_externo": admin["id_externo"],
                "nombre": admin["nombre"]
            }
            for admin in admins_anteriores
            if admin["id"] != datos.usuario_id
        ]

        return {
            "mensaje": (
                "Compañía reasignada correctamente"
                if admins_anteriores
                else "Compañía asignada correctamente"
            ),
            "reasignada": bool(admins_anteriores),
            "asignacion": dict(asignacion),
            "administradores_retirados": administradores_retirados,
            "usuario": {
                "id": usuario["id"],
                "id_externo": usuario["id_externo"],
                "nombre": usuario["nombre"],
                "rol": "ADMIN_SOPORTE"
            },
            "compania": {
                "id": compania["id"],
                "codigo": compania["codigo"],
                "nombre": compania["nombre"]
            }
        }

    except IntegrityError:
        # No exponemos detalles internos de PostgreSQL.
        raise HTTPException(
            status_code=409,
            detail="No fue posible completar la asignación de la compañía"
        )


# ============================================================
# LISTAR ASIGNACIONES ADMIN_SOPORTE ↔ COMPAÑÍA
# ============================================================
# Solo ADMIN_TI puede consultar el mapa de asignaciones.
# Este endpoint expone únicamente datos administrativos
# necesarios para gestionar el alcance de ADMIN_SOPORTE.
# No devuelve identidades internas de las compañías.
# ============================================================

@router.get("/asignaciones")
def listar_asignaciones(
    usuario_actual=Depends(
        requiere_roles("ADMIN_TI")
    )
):
    consulta = text("""
        SELECT
            uc.id AS asignacion_id,
            uc.usuario_id,
            u.id_externo AS usuario_id_externo,
            u.nombre AS usuario_nombre,
            u.activo AS usuario_activo,
            uc.compania_id,
            c.codigo AS compania_codigo,
            c.nombre AS compania_nombre,
            c.activo AS compania_activa,
            uc.fecha_asignacion
        FROM usuario_companias_plataforma uc
        JOIN usuarios_plataforma u
            ON u.id = uc.usuario_id
        JOIN usuario_roles_plataforma ur
            ON ur.usuario_id = u.id
        JOIN roles_plataforma r
            ON r.id = ur.rol_id
           AND r.activo = TRUE
        JOIN companias c
            ON c.id = uc.compania_id
        WHERE r.nombre = 'ADMIN_SOPORTE'
        ORDER BY
            u.nombre,
            c.nombre
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(consulta)

        asignaciones = [
            dict(asignacion)
            for asignacion in resultado.mappings().all()
        ]

    return {
        "total": len(asignaciones),
        "asignaciones": asignaciones
    }


# ============================================================
# DESASIGNAR COMPAÑÍA DE ADMIN_SOPORTE
# ============================================================
# Únicamente ADMIN_TI puede retirar una compañía del alcance
# de un ADMIN_SOPORTE.
#
# La operación elimina solo la relación de autorización.
# No elimina el usuario, la compañía ni las identidades de
# negocio pertenecientes a la compañía.
#
# Se permite desasignar una compañía aunque esté inactiva,
# porque ADMIN_TI debe poder retirar accesos residuales.
# ============================================================

@router.delete(
    "/asignaciones/{usuario_id}/{compania_id}"
)
def desasignar_compania(
    usuario_id: int,
    compania_id: int,
    usuario_actual=Depends(requiere_roles("ADMIN_TI"))
):
    with engine.begin() as conexion:
        usuario = conexion.execute(
            text("""
                SELECT
                    u.id, u.id_externo, u.nombre,
                    ARRAY_AGG(r.nombre ORDER BY r.nombre)
                        FILTER (WHERE r.nombre IS NOT NULL) AS roles
                FROM usuarios_plataforma u
                LEFT JOIN usuario_roles_plataforma ur
                    ON ur.usuario_id = u.id
                LEFT JOIN roles_plataforma r
                    ON r.id = ur.rol_id
                   AND r.activo = TRUE
                WHERE u.id = :usuario_id
                GROUP BY u.id, u.id_externo, u.nombre
            """),
            {"usuario_id": usuario_id}
        ).mappings().first()

        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        roles = [r for r in (usuario["roles"] or []) if r is not None]
        if roles != ["ADMIN_SOPORTE"]:
            raise HTTPException(
                status_code=400,
                detail="Solo pueden modificarse asignaciones de usuarios ADMIN_SOPORTE"
            )

        compania = conexion.execute(
            text("""
                SELECT id, codigo, nombre, activo
                FROM companias
                WHERE id = :compania_id
                FOR UPDATE
            """),
            {"compania_id": compania_id}
        ).mappings().first()

        if compania is None:
            raise HTTPException(status_code=404, detail="Compañía no encontrada")

        eliminada = conexion.execute(
            text("""
                DELETE FROM usuario_companias_plataforma
                WHERE usuario_id = :usuario_id
                  AND compania_id = :compania_id
                RETURNING id
            """),
            {"usuario_id": usuario_id, "compania_id": compania_id}
        ).first()

        if eliminada is None:
            raise HTTPException(
                status_code=404,
                detail="La compañía no está asignada al usuario ADMIN_SOPORTE"
            )

        revocacion = conexion.execute(
            text("""
                UPDATE sesiones
                SET revocada = TRUE, fecha_revocacion = NOW()
                WHERE usuario_id = :usuario_id
                  AND revocada = FALSE
                  AND fecha_expiracion > NOW()
            """),
            {"usuario_id": usuario_id}
        )

        # La retirada del alcance se publica al Sync Worker en
        # la misma transacción que elimina la asignación.
        encolar_sync_job(
            conexion,
            operacion="REVOCAR",
            usuario_id=usuario_id,
            compania_id=compania_id,
            solicitado_por_usuario_id=usuario_actual["id"],
        )

    # --------------------------------------------------------
    # AUDITORÍA
    # --------------------------------------------------------
    # El evento se registra después del COMMIT exitoso.
    # --------------------------------------------------------

    registrar_evento(
        COMPANIA_DESASIGNADA,
        actor_usuario_id=usuario_actual["id"],
        objetivo_usuario_id=usuario_id,
        compania_id=compania_id,
        resultado="EXITO",
        detalle={
            "sesiones_revocadas": revocacion.rowcount,
            "operacion_sync": "REVOCAR",
        },
    )

    return {
        "mensaje": "Compañía desasignada correctamente",
        "usuario": {
            "id": usuario["id"],
            "id_externo": usuario["id_externo"],
            "nombre": usuario["nombre"],
            "rol": "ADMIN_SOPORTE"
        },
        "compania": {
            "id": compania["id"],
            "codigo": compania["codigo"],
            "nombre": compania["nombre"]
        },
        "sesiones_revocadas": revocacion.rowcount
    }


# ============================================================
# CAMBIAR ESTADO DE COMPAÑÍA
# ============================================================
# Solo ADMIN_TI puede habilitar o deshabilitar compañías.
# ============================================================

@router.patch("/{compania_id}/estado")
def cambiar_estado_compania(
    compania_id: int,
    datos: CompaniaEstado,
    usuario_actual=Depends(
        requiere_roles("ADMIN_TI")
    )
):
    consulta = text("""
        UPDATE companias
        SET
            activo = :activo,
            fecha_modificacion = NOW()
        WHERE id = :compania_id
        RETURNING
            id,
            codigo,
            nombre,
            descripcion,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    sesiones_revocadas = 0

    with engine.begin() as conexion:
        compania = conexion.execute(
            consulta,
            {
                "compania_id": compania_id,
                "activo": datos.activo
            }
        ).mappings().first()

        if compania is not None and datos.activo is False:
            resultado_revocacion = conexion.execute(
                text("""
                    UPDATE sesiones
                    SET revocada = TRUE, fecha_revocacion = NOW()
                    WHERE usuario_id IN (
                        SELECT usuario_id
                        FROM usuario_companias_plataforma
                        WHERE compania_id = :compania_id
                    )
                      AND revocada = FALSE
                      AND fecha_expiracion > NOW()
                """),
                {"compania_id": compania_id}
            )

            sesiones_revocadas = resultado_revocacion.rowcount

    if compania is None:
        raise HTTPException(
            status_code=404,
            detail="Compañía no encontrada"
        )

    # --------------------------------------------------------
    # AUDITORÍA
    # --------------------------------------------------------
    # Al deshabilitar una compañía se registra también la
    # cantidad de sesiones revocadas por el cambio de alcance.
    # --------------------------------------------------------

    registrar_evento(
        COMPANIA_ESTADO_MODIFICADO,
        actor_usuario_id=usuario_actual["id"],
        compania_id=compania_id,
        resultado="EXITO",
        detalle={
            "activo": datos.activo,
            "sesiones_revocadas": sesiones_revocadas,
        },
    )

    return dict(compania)


# ============================================================
# CONTEXTO DE COMPAÑÍA
# ============================================================

@router.get("/{compania_id}/contexto")
def obtener_contexto_compania(
    compania_id: int,
    usuario_actual=Depends(
        requiere_compania
    )
):
    consulta = text("""
        SELECT
            id,
            codigo,
            nombre,
            descripcion,
            activo,
            fecha_creacion,
            fecha_modificacion
        FROM companias
        WHERE id = :compania_id
    """)

    with engine.connect() as conexion:
        compania = conexion.execute(
            consulta,
            {
                "compania_id": compania_id
            }
        ).mappings().first()

    if compania is None:
        raise HTTPException(
            status_code=404,
            detail="Compañía no encontrada"
        )

    return {
        "usuario": {
            "id": usuario_actual["id"],
            "nombre": usuario_actual["nombre"],
            "email": usuario_actual["email"],
            "roles": usuario_actual["roles"]
        },
        "compania": dict(compania)
    }


# ============================================================
# USUARIOS DE UNA COMPAÑÍA
# ============================================================
# Principio de mínimo privilegio:
#
# - ADMIN_TI NO consulta identidades internas de compañías.
# - ADMIN_SOPORTE solo puede consultar compañías que tenga
#   asignadas, validado previamente por requiere_compania.
# - La consulta devuelve únicamente identidades organizacionales
#   administrables, nunca ADMIN_TI ni ADMIN_SOPORTE.
# ============================================================

@router.get("/{compania_id}/usuarios")
def obtener_usuarios_compania(
    compania_id: int,
    usuario_actual=Depends(
        requiere_compania
    )
):
    roles_usuario = usuario_actual.get("roles", [])

    if "ADMIN_SOPORTE" not in roles_usuario:
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para consultar identidades de la compañía"
        )

    consulta = text("""
        SELECT DISTINCT
            u.id,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo,
            r.nombre AS rol,
            u.fecha_creacion,
            u.fecha_modificacion
        FROM usuarios_plataforma u
        JOIN usuario_companias_plataforma uc
            ON uc.usuario_id = u.id
        JOIN usuario_roles_plataforma ur
            ON ur.usuario_id = u.id
        JOIN roles_plataforma r
            ON r.id = ur.rol_id
           AND r.activo = TRUE
        WHERE uc.compania_id = :compania_id
          AND r.nombre IN (
              'LIDER_FACTURACION',
              'LIDER_LOGISTICA',
              'LIDER_GESTION_HUMANA'
          )
        ORDER BY u.nombre
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "compania_id": compania_id
            }
        )

        usuarios = [
            dict(usuario)
            for usuario in resultado.mappings().all()
        ]

    return {
        "compania_id": compania_id,
        "total": len(usuarios),
        "usuarios": usuarios
    }

# ============================================================
