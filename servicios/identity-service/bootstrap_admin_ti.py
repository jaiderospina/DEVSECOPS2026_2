"""
Bootstrap seguro del ADMIN_TI inicial.

Este script existe porque la primera cuenta ADMIN_TI no puede
crearse mediante los endpoints administrativos normales: todavía
no existe un administrador autenticado que pueda autorizarla.

IMPORTANTE:
- La contraseña temporal NO está escrita en este archivo.
- Se recibe mediante la variable de entorno
  BOOTSTRAP_ADMIN_TI_PASSWORD.
- En PostgreSQL solamente se almacena el hash Argon2.
- La cuenta queda obligada a cambiar la contraseña en el primer acceso.
- El script es idempotente: no crea nuevamente la cuenta si ya existe.
- No se imprimen contraseñas, hashes, JWT, JTI ni otros secretos.
"""

import os
import sys

from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import engine


# =========================================================
# CONFIGURACIÓN ACADÉMICA DEL ADMIN_TI INICIAL
# =========================================================
# Estos datos no son secretos y corresponden a la identidad
# académica definida para el Coordinador TI.
#
# La contraseña NO se define aquí.
# =========================================================

ADMIN_TI_ID_EXTERNO = "1051"
ADMIN_TI_NOMBRE = "Camilo Andres Mendoza Garcia"
ADMIN_TI_EMAIL = "CamiloCoordiTI@areati.demo"
ADMIN_TI_ROL = "ADMIN_TI"


# =========================================================
# CONFIGURACIÓN DEL HASH DE CONTRASEÑA
# =========================================================
# PasswordHash.recommended() utiliza la configuración segura
# recomendada por pwdlib.
#
# La contraseña en texto claro nunca se almacena en la base
# de datos. Solamente se persiste el hash resultante.
# =========================================================

password_hasher = PasswordHash.recommended()


# =========================================================
# VALIDACIÓN DE CONTRASEÑA TEMPORAL
# =========================================================
# La política del proyecto establece:
#
# - mínimo 12 caracteres;
# - al menos una letra;
# - al menos un carácter especial.
#
# El mínimo de 12 caracteres está unificado con la política
# utilizada para las contraseñas definitivas del sistema.
# =========================================================

def validar_password_temporal(password: str) -> None:
    """
    Valida la contraseña temporal utilizada exclusivamente
    durante el bootstrap del ADMIN_TI.

    La función nunca imprime ni registra la contraseña.
    """

    if len(password) < 12:
        raise ValueError(
            "La contraseña temporal debe tener "
            "mínimo 12 caracteres"
        )

    if not any(
        caracter.isalpha()
        for caracter in password
    ):
        raise ValueError(
            "La contraseña temporal debe contener "
            "al menos una letra"
        )

    if not any(
        not caracter.isalnum()
        for caracter in password
    ):
        raise ValueError(
            "La contraseña temporal debe contener "
            "al menos un carácter especial"
        )


# =========================================================
# BOOTSTRAP DEL ADMIN_TI
# =========================================================

def crear_admin_ti_inicial() -> None:
    """
    Crea la primera identidad ADMIN_TI de forma controlada.

    La operación completa se ejecuta dentro de una transacción
    para evitar estados parciales en caso de error.
    """

    # -----------------------------------------------------
    # 1. OBTENER CONTRASEÑA DESDE EL ENTORNO
    # -----------------------------------------------------
    # Nunca utilizamos una contraseña escrita directamente
    # en el código fuente.
    #
    # Tampoco existe un valor por defecto para esta variable:
    # si no está configurada, el bootstrap debe detenerse.
    # -----------------------------------------------------

    password_temporal = os.getenv(
        "BOOTSTRAP_ADMIN_TI_PASSWORD"
    )

    if not password_temporal:
        raise RuntimeError(
            "No se encontró la variable de entorno "
            "BOOTSTRAP_ADMIN_TI_PASSWORD"
        )

    # -----------------------------------------------------
    # Validamos la contraseña antes de generar el hash.
    # -----------------------------------------------------

    validar_password_temporal(
        password_temporal
    )

    # -----------------------------------------------------
    # 2. GENERAR HASH ARGON2
    # -----------------------------------------------------
    # A partir de este punto, el valor destinado a la BD es
    # exclusivamente el hash.
    #
    # La contraseña temporal no se imprime ni se incluye en
    # mensajes de respuesta.
    # -----------------------------------------------------

    password_hash = password_hasher.hash(
        password_temporal
    )

    # -----------------------------------------------------
    # 3. TRANSACCIÓN ATÓMICA
    # -----------------------------------------------------
    # Usuario, credencial y rol deben crearse como una única
    # operación lógica.
    #
    # engine.begin() realiza COMMIT si todo termina
    # correctamente y ROLLBACK si ocurre una excepción.
    # -----------------------------------------------------

    with engine.begin() as conexion:

        # -------------------------------------------------
        # 4. COMPROBAR SI YA EXISTE EL ADMIN_TI
        # -------------------------------------------------
        # Esta validación hace que el bootstrap sea
        # idempotente.
        #
        # Se verifica tanto el ID académico como el correo
        # para evitar crear identidades duplicadas.
        # -------------------------------------------------

        usuario_existente = conexion.execute(
            text("""
                SELECT
                    id,
                    id_externo,
                    nombre,
                    email
                FROM usuarios_plataforma
                WHERE id_externo = :id_externo
                   OR LOWER(email) = LOWER(:email)
                LIMIT 1
            """),
            {
                "id_externo":
                    ADMIN_TI_ID_EXTERNO,

                "email":
                    ADMIN_TI_EMAIL
            }
        ).mappings().first()

        if usuario_existente is not None:
            print(
                "Bootstrap no ejecutado: "
                "el ADMIN_TI inicial ya existe."
            )
            return

        # -------------------------------------------------
        # 5. COMPROBAR EL ROL ADMIN_TI
        # -------------------------------------------------
        # El rol debe existir previamente y encontrarse
        # activo.
        # -------------------------------------------------

        rol = conexion.execute(
            text("""
                SELECT
                    id,
                    nombre
                FROM roles_plataforma
                WHERE nombre = :rol
                  AND activo = TRUE
                LIMIT 1
            """),
            {
                "rol":
                    ADMIN_TI_ROL
            }
        ).mappings().first()

        if rol is None:
            raise RuntimeError(
                "El rol ADMIN_TI no existe "
                "o se encuentra inactivo"
            )

        # -------------------------------------------------
        # 6. CREAR IDENTIDAD
        # -------------------------------------------------
        # Se utilizan parámetros SQL; los valores no se
        # concatenan directamente dentro de la consulta.
        # -------------------------------------------------

        usuario = conexion.execute(
            text("""
                INSERT INTO usuarios_plataforma (
                    id_externo,
                    nombre,
                    email,
                    activo
                )
                VALUES (
                    :id_externo,
                    :nombre,
                    :email,
                    TRUE
                )
                RETURNING
                    id,
                    id_externo,
                    nombre,
                    email
            """),
            {
                "id_externo":
                    ADMIN_TI_ID_EXTERNO,

                "nombre":
                    ADMIN_TI_NOMBRE,

                "email":
                    ADMIN_TI_EMAIL
            }
        ).mappings().one()

        # -------------------------------------------------
        # 7. CREAR CREDENCIAL
        # -------------------------------------------------
        # Únicamente almacenamos password_hash.
        #
        # requiere_cambio_password = TRUE obliga al
        # ADMIN_TI a reemplazar la contraseña temporal
        # antes de utilizar las funciones administrativas.
        # -------------------------------------------------

        conexion.execute(
            text("""
                INSERT INTO credenciales (
                    usuario_id,
                    password_hash,
                    activo,
                    requiere_cambio_password
                )
                VALUES (
                    :usuario_id,
                    :password_hash,
                    TRUE,
                    TRUE
                )
            """),
            {
                "usuario_id":
                    usuario["id"],

                "password_hash":
                    password_hash
            }
        )

        # -------------------------------------------------
        # 8. ASIGNAR ROL ADMIN_TI
        # -------------------------------------------------

        conexion.execute(
            text("""
                INSERT INTO usuario_roles_plataforma (
                    usuario_id,
                    rol_id
                )
                VALUES (
                    :usuario_id,
                    :rol_id
                )
            """),
            {
                "usuario_id":
                    usuario["id"],

                "rol_id":
                    rol["id"]
            }
        )

    # -----------------------------------------------------
    # 9. RESPUESTA SEGURA
    # -----------------------------------------------------
    # Solo se muestran datos operativos no secretos.
    #
    # Nunca se imprimen:
    # - contraseña temporal;
    # - hash Argon2;
    # - JWT;
    # - JTI;
    # - secretos de aplicación;
    # - credenciales de base de datos.
    # -----------------------------------------------------

    print(
        "ADMIN_TI inicial creado correctamente."
    )

    print(
        f"ID interno PostgreSQL: {usuario['id']}"
    )

    print(
        f"ID académico: {usuario['id_externo']}"
    )

    print(
        f"Nombre: {usuario['nombre']}"
    )

    print(
        f"Correo: {usuario['email']}"
    )

    print(
        "Cambio de contraseña requerido: SI"
    )


# =========================================================
# PUNTO DE ENTRADA
# =========================================================

if __name__ == "__main__":
    try:
        crear_admin_ti_inicial()

    # -----------------------------------------------------
    # ERROR DE VALIDACIÓN CONTROLADO
    # -----------------------------------------------------
    # Estos mensajes son definidos por nuestra propia
    # validación y no contienen la contraseña recibida.
    # -----------------------------------------------------

    except ValueError as error:
        print(
            f"Error de validación: {error}",
            file=sys.stderr
        )
        sys.exit(1)

    # -----------------------------------------------------
    # ERROR DE INTEGRIDAD
    # -----------------------------------------------------
    # No mostramos la excepción original de PostgreSQL para
    # evitar exponer SQL, parámetros o información interna.
    # -----------------------------------------------------

    except IntegrityError:
        print(
            "No fue posible crear ADMIN_TI debido "
            "a una restricción de integridad.",
            file=sys.stderr
        )
        sys.exit(1)

    # -----------------------------------------------------
    # ERROR INESPERADO
    # -----------------------------------------------------
    # No interpolamos el objeto Exception.
    #
    # Dependiendo del origen, una excepción podría incluir
    # detalles internos del motor de BD, infraestructura,
    # parámetros u otra información que no debe exponerse.
    # -----------------------------------------------------

    except Exception:
        print(
            "Error interno durante el bootstrap "
            "de ADMIN_TI.",
            file=sys.stderr
        )
        sys.exit(1)
