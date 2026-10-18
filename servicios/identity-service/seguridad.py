import os
from datetime import datetime, timezone, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from database import engine
from auditoria import registrar_evento, SESION_EXPIRADA_INACTIVIDAD

load_dotenv()

# ============================================================
# CONFIGURACIÓN JWT
# ============================================================
# El secreto se obtiene exclusivamente desde variables de
# entorno. Nunca debe quedar hardcodeado en el repositorio.
# ============================================================

bearer_scheme = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

if not JWT_SECRET:
    raise RuntimeError("La variable JWT_SECRET no está configurada")


# ============================================================
# EXPIRACIÓN DE SESIÓN POR INACTIVIDAD
# ============================================================
# Política predeterminada: 5 minutos.
# Este control NO modifica la contraseña ni activa un cambio
# obligatorio de contraseña. Solamente revoca la sesión.
# ============================================================

try:
    SESSION_INACTIVITY_MINUTES = int(
        os.getenv("SESSION_INACTIVITY_MINUTES", "5")
    )
except ValueError:
    raise RuntimeError(
        "SESSION_INACTIVITY_MINUTES debe ser un número entero"
    )

if SESSION_INACTIVITY_MINUTES <= 0:
    raise RuntimeError(
        "SESSION_INACTIVITY_MINUTES debe ser mayor que cero"
    )


# ============================================================
# USUARIO AUTENTICADO
# ============================================================
# Esta dependencia constituye la validación central de cada
# petición autenticada.
#
# El JWT sirve para identificar la sesión, pero NO constituye
# por sí solo la fuente de verdad. En cada petición se consulta
# PostgreSQL para validar:
#
# - estado del usuario;
# - estado de la credencial;
# - bloqueo por intentos fallidos;
# - sesión persistida y revocación;
# - expiración absoluta;
# - inactividad;
# - roles vigentes;
# - obligación de cambiar contraseña;
# - expiración de la contraseña definitiva.
#
# IMPORTANTE:
# password_hash nunca se consulta en esta dependencia.
# ============================================================

def obtener_usuario_desde_token(
    credenciales: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credenciales.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
        )

    usuario_id = payload.get("sub")
    jti = payload.get("jti")

    if usuario_id is None or jti is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
        )

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
        )

    # ========================================================
    # USUARIO + CREDENCIAL
    # ========================================================
    # Se incluyen únicamente campos necesarios para tomar
    # decisiones de seguridad. No se recupera password_hash.
    # ========================================================

    consulta_usuario = text("""
        SELECT
            u.id,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo,
            c.activo AS credencial_activa,
            c.requiere_cambio_password,
            c.bloqueado,
            c.password_temporal_expira_en,
            c.password_expira_en
        FROM usuarios_plataforma u
        JOIN credenciales c
            ON c.usuario_id = u.id
        WHERE u.id = :usuario_id
    """)

    with engine.connect() as conexion:
        usuario = conexion.execute(
            consulta_usuario,
            {"usuario_id": usuario_id},
        ).mappings().first()

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado",
        )

    if not usuario["activo"]:
        raise HTTPException(
            status_code=403,
            detail="Usuario inactivo",
        )

    if not usuario["credencial_activa"]:
        raise HTTPException(
            status_code=403,
            detail="Credencial inactiva",
        )

    # ========================================================
    # BLOQUEO POR INTENTOS FALLIDOS
    # ========================================================
    # Si la cuenta fue bloqueada, ningún JWT emitido antes del
    # bloqueo puede seguir utilizándose.
    # ========================================================

    if usuario["bloqueado"]:
        raise HTTPException(
            status_code=401,
            detail="Sesión no válida",
        )

    # ========================================================
    # SESIÓN PERSISTIDA
    # ========================================================

    consulta_sesion = text("""
        SELECT
            id,
            usuario_id,
            fecha_inicio,
            ultima_actividad,
            fecha_expiracion,
            revocada,
            fecha_revocacion
        FROM sesiones
        WHERE jti = :jti
          AND usuario_id = :usuario_id
    """)

    with engine.connect() as conexion:
        sesion = conexion.execute(
            consulta_sesion,
            {
                "jti": jti,
                "usuario_id": usuario_id,
            },
        ).mappings().first()

    if sesion is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión no encontrada",
        )

    if sesion["revocada"]:
        raise HTTPException(
            status_code=401,
            detail="Sesión revocada",
        )

    ahora = datetime.now(timezone.utc)

    # ========================================================
    # EXPIRACIÓN ABSOLUTA
    # ========================================================

    if sesion["fecha_expiracion"] <= ahora:
        raise HTTPException(
            status_code=401,
            detail="Sesión expirada",
        )

    # ========================================================
    # EXPIRACIÓN POR INACTIVIDAD
    # ========================================================
    # La sesión se revoca al superar el límite. Este proceso
    # NO cambia password_hash, password_expira_en ni
    # requiere_cambio_password.
    # ========================================================

    ultima_actividad = (
        sesion["ultima_actividad"]
        if sesion["ultima_actividad"] is not None
        else sesion["fecha_inicio"]
    )

    limite_inactividad = timedelta(
        minutes=SESSION_INACTIVITY_MINUTES
    )

    if ahora - ultima_actividad >= limite_inactividad:
        revocar_sesion = text("""
            UPDATE sesiones
            SET
                revocada = TRUE,
                fecha_revocacion = NOW()
            WHERE id = :sesion_id
              AND revocada = FALSE
        """)

        with engine.begin() as conexion:
            resultado_revocacion = conexion.execute(
                revocar_sesion,
                {"sesion_id": sesion["id"]},
            )

        if resultado_revocacion.rowcount > 0:
            registrar_evento(
                SESION_EXPIRADA_INACTIVIDAD,
                actor_usuario_id=sesion["usuario_id"],
                resultado="EXITO",
                detalle={
                    "motivo": "INACTIVIDAD",
                    "limite_minutos": SESSION_INACTIVITY_MINUTES,
                },
            )

        raise HTTPException(
            status_code=401,
            detail="Sesión expirada por inactividad",
        )

    # ========================================================
    # EXPIRACIÓN DE CONTRASEÑA DEFINITIVA DURANTE LA SESIÓN
    # ========================================================
    # No basta con comprobar la vigencia únicamente durante
    # /auth/login. Una sesión podría permanecer activa justo
    # cuando la contraseña alcanza su fecha de vencimiento.
    #
    # Si la contraseña definitiva ya venció:
    # - se marca requiere_cambio_password = TRUE;
    # - NO se destruye la sesión actual;
    # - la sesión queda limitada a endpoints que no utilicen
    #   requiere_password_definitivo, por ejemplo /auth/password
    #   y /auth/logout.
    #
    # Así el usuario puede establecer una nueva contraseña sin
    # necesidad de crear una excepción insegura en el frontend.
    # ========================================================

    requiere_cambio_password = bool(
        usuario["requiere_cambio_password"]
    )

    password_definitiva_expirada = (
        not requiere_cambio_password
        and usuario["password_expira_en"] is not None
        and usuario["password_expira_en"] <= ahora
    )

    if password_definitiva_expirada:
        marcar_cambio_obligatorio = text("""
            UPDATE credenciales
            SET
                requiere_cambio_password = TRUE,
                fecha_modificacion = NOW()
            WHERE usuario_id = :usuario_id
              AND activo = TRUE
              AND requiere_cambio_password = FALSE
              AND password_expira_en IS NOT NULL
              AND password_expira_en <= NOW()
        """)

        with engine.begin() as conexion:
            conexion.execute(
                marcar_cambio_obligatorio,
                {"usuario_id": usuario_id},
            )

        requiere_cambio_password = True

    # ========================================================
    # CONTRASEÑA TEMPORAL EXPIRADA DURANTE SESIÓN LIMITADA
    # ========================================================
    # Normalmente una contraseña temporal vencida no puede
    # iniciar sesión. Esta comprobación adicional cubre el caso
    # en el que una sesión limitada fue creada antes de que se
    # cumplieran las 24 horas y permaneció abierta después.
    #
    # Al vencer la temporal se revoca la sesión. No se permite
    # prolongar indirectamente la validez de la temporal.
    # ========================================================

    temporal_expirada = (
        requiere_cambio_password
        and usuario["password_temporal_expira_en"] is not None
        and usuario["password_temporal_expira_en"] <= ahora
    )

    if temporal_expirada:
        revocar_temporal = text("""
            UPDATE sesiones
            SET
                revocada = TRUE,
                fecha_revocacion = NOW()
            WHERE id = :sesion_id
              AND revocada = FALSE
        """)

        with engine.begin() as conexion:
            conexion.execute(
                revocar_temporal,
                {"sesion_id": sesion["id"]},
            )

        raise HTTPException(
            status_code=401,
            detail=(
                "La contraseña temporal expiró. "
                "Solicite un nuevo restablecimiento de acceso."
            ),
        )

    # ========================================================
    # ACTUALIZAR ÚLTIMA ACTIVIDAD
    # ========================================================

    actualizar_actividad = text("""
        UPDATE sesiones
        SET ultima_actividad = NOW()
        WHERE id = :sesion_id
          AND revocada = FALSE
    """)

    with engine.begin() as conexion:
        conexion.execute(
            actualizar_actividad,
            {"sesion_id": sesion["id"]},
        )

    # ========================================================
    # ROLES VIGENTES
    # ========================================================

    consulta_roles = text("""
        SELECT r.nombre
        FROM roles_plataforma r
        JOIN usuario_roles_plataforma ur
            ON ur.rol_id = r.id
        WHERE ur.usuario_id = :usuario_id
          AND r.activo = TRUE
        ORDER BY r.nombre
    """)

    with engine.connect() as conexion:
        resultado_roles = conexion.execute(
            consulta_roles,
            {"usuario_id": usuario_id},
        )

        roles = [
            fila[0]
            for fila in resultado_roles.fetchall()
        ]

    if not roles:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un rol activo asignado",
        )

    # ========================================================
    # CONTEXTO INTERNO AUTENTICADO
    # ========================================================
    # session_id se necesita internamente para logout y otras
    # operaciones de sesión. JTI deliberadamente NO se devuelve
    # en este diccionario porque los endpoints no necesitan
    # recibirlo después de localizar la sesión.
    # ========================================================

    return {
        "id": usuario["id"],
        "id_externo": usuario["id_externo"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "activo": usuario["activo"],
        "roles": roles,
        "requiere_cambio_password": requiere_cambio_password,
        "password_expira_en": usuario["password_expira_en"],
        "session_id": sesion["id"],
    }


# ============================================================
# CAMBIO OBLIGATORIO DE CONTRASEÑA
# ============================================================
# Separa autenticación de habilitación funcional.
#
# Un usuario puede poseer una sesión válida y, al mismo tiempo,
# estar obligado a cambiar su contraseña. En ese estado puede
# acceder a /auth/password y /auth/logout, pero no a endpoints
# protegidos mediante esta dependencia.
# ============================================================

def requiere_password_definitivo(
    usuario=Depends(obtener_usuario_desde_token)
):
    if usuario.get("requiere_cambio_password", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "Debe cambiar su contraseña "
                "antes de continuar"
            ),
        )

    return usuario


# ============================================================
# AUTORIZACIÓN BASADA EN ROLES
# ============================================================
# La autorización siempre se aplica en backend. Ocultar botones
# o vistas en React nunca sustituye este control.
# ============================================================

def requiere_roles(*roles_permitidos):
    def validador(
        usuario=Depends(requiere_password_definitivo)
    ):
        roles_usuario = usuario.get("roles", [])

        if not any(
            rol in roles_usuario
            for rol in roles_permitidos
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "No tiene permisos para "
                    "realizar esta operación"
                ),
            )

        return usuario

    return validador


# ============================================================
# ACCESO ADMINISTRATIVO A UNA COMPAÑÍA
# ============================================================
# ADMIN_TI:
#   alcance administrativo global sobre compañías activas.
#
# ADMIN_SOPORTE:
#   únicamente compañías activas asignadas explícitamente.
#
# Otros roles:
#   no obtienen privilegios administrativos por el simple
#   hecho de estar asociados con una compañía.
# ============================================================

def requiere_compania(
    compania_id: int,
    usuario=Depends(requiere_password_definitivo)
):
    roles_usuario = usuario.get("roles", [])

    if "ADMIN_TI" in roles_usuario:
        consulta_compania = text("""
            SELECT id
            FROM companias
            WHERE id = :compania_id
              AND activo = TRUE
        """)

        with engine.connect() as conexion:
            compania = conexion.execute(
                consulta_compania,
                {"compania_id": compania_id},
            ).first()

        if compania is None:
            raise HTTPException(
                status_code=404,
                detail="Compañía no encontrada o inactiva",
            )

        return usuario

    if "ADMIN_SOPORTE" not in roles_usuario:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tiene permisos administrativos "
                "sobre compañías"
            ),
        )

    consulta = text("""
        SELECT uc.id
        FROM usuario_companias_plataforma uc
        JOIN companias c
            ON c.id = uc.compania_id
        WHERE uc.usuario_id = :usuario_id
          AND uc.compania_id = :compania_id
          AND c.activo = TRUE
    """)

    with engine.connect() as conexion:
        asignacion = conexion.execute(
            consulta,
            {
                "usuario_id": usuario["id"],
                "compania_id": compania_id,
            },
        ).first()

    if asignacion is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tiene acceso administrativo "
                "a la compañía solicitada"
            ),
        )

    return usuario
