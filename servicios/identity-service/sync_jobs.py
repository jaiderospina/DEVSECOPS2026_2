# ============================================================
# IAM SECURE - PRODUCTOR DE TRABAJOS DE SINCRONIZACIÓN
# ============================================================
# Este módulo permite que el Identity Service publique trabajos
# para el Sync Worker.
#
# DISEÑO:
# - El Identity Service produce trabajos.
# - PostgreSQL actúa como cola persistente.
# - El Sync Worker consume los trabajos asíncronamente.
#
# SEGURIDAD:
# - No almacena contraseñas.
# - No almacena hashes.
# - No almacena JWT ni JTI.
# - No almacena secretos MFA/TOTP.
# - No almacena credenciales SMTP.
#
# El trabajo debe insertarse utilizando la MISMA conexión /
# transacción que realiza la operación principal. De esta forma:
#
#   COMMIT identidad  -> COMMIT sync_job
#   ROLLBACK identidad -> ROLLBACK sync_job
#
# Esto evita inconsistencias entre IAM Secure y el Worker.
# ============================================================

from typing import Literal

from sqlalchemy import text
from sqlalchemy.engine import Connection


OperacionSync = Literal[
    "PROVISIONAR",
    "MODIFICAR",
    "DESHABILITAR",
    "REVOCAR",
]


# ============================================================
# ENCOLAR TRABAJO DE SINCRONIZACIÓN
# ============================================================

def encolar_sync_job(
    conexion: Connection,
    *,
    operacion: OperacionSync,
    usuario_id: int | None,
    compania_id: int | None = None,
    solicitado_por_usuario_id: int | None = None,
    max_intentos: int = 3,
) -> int:
    """
    Registra un trabajo pendiente para el Sync Worker.

    La función NO abre una transacción independiente.
    Utiliza la conexión recibida para que el trabajo forme
    parte de la misma transacción de la operación IAM.

    Retorna únicamente el ID interno del trabajo.
    """

    # --------------------------------------------------------
    # VALIDACIONES DEFENSIVAS
    # --------------------------------------------------------

    operaciones_permitidas = {
        "PROVISIONAR",
        "MODIFICAR",
        "DESHABILITAR",
        "REVOCAR",
    }

    if operacion not in operaciones_permitidas:
        raise ValueError(
            "Operación de sincronización no permitida"
        )

    if usuario_id is not None:
        if not isinstance(usuario_id, int) or usuario_id <= 0:
            raise ValueError(
                "usuario_id debe ser un entero positivo"
            )

    if compania_id is not None:
        if not isinstance(compania_id, int) or compania_id <= 0:
            raise ValueError(
                "compania_id debe ser un entero positivo"
            )

    if solicitado_por_usuario_id is not None:
        if (
            not isinstance(solicitado_por_usuario_id, int)
            or solicitado_por_usuario_id <= 0
        ):
            raise ValueError(
                "solicitado_por_usuario_id debe ser "
                "un entero positivo"
            )

    if not isinstance(max_intentos, int) or max_intentos <= 0:
        raise ValueError(
            "max_intentos debe ser un entero positivo"
        )

    # --------------------------------------------------------
    # CREAR TRABAJO
    # --------------------------------------------------------
    # disponible_desde queda en NOW(), por lo que el Worker
    # podrá reclamar el trabajo inmediatamente después del
    # COMMIT de la transacción actual.
    #
    # No se incluye información sensible en resultado/error.
    # --------------------------------------------------------

    resultado = conexion.execute(
        text("""
            INSERT INTO sync_jobs (
                operacion,
                estado,
                usuario_id,
                compania_id,
                solicitado_por_usuario_id,
                intentos,
                max_intentos,
                disponible_desde,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (
                :operacion,
                'PENDIENTE',
                :usuario_id,
                :compania_id,
                :solicitado_por_usuario_id,
                0,
                :max_intentos,
                NOW(),
                NOW(),
                NOW()
            )
            RETURNING id
        """),
        {
            "operacion":
                operacion,

            "usuario_id":
                usuario_id,

            "compania_id":
                compania_id,

            "solicitado_por_usuario_id":
                solicitado_por_usuario_id,

            "max_intentos":
                max_intentos,
        },
    ).scalar_one()

    return int(resultado)