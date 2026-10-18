"""
Bootstrap seguro de los usuarios académicos iniciales.

Objetivo:
- Crear las 13 identidades iniciales del Identity Service.
- Asignar el rol técnico correspondiente.
- Asignar compañía cuando aplique.
- Generar una contraseña temporal aleatoria por usuario.
- Almacenar únicamente hashes Argon2.
- Obligar al cambio de contraseña en el primer acceso.
- Aplicar expiración configurable a la contraseña temporal.
- Entregar la contraseña temporal únicamente por correo.

SEGURIDAD:
- Ninguna contraseña se almacena en este archivo.
- No se utilizan variables BOOTSTRAP_PASSWORD_*.
- PostgreSQL recibe únicamente hashes Argon2.
- No se imprimen contraseñas, hashes, JWT ni otros secretos.
- El proceso es idempotente: no duplica usuarios existentes.
- Los correos se envían después del COMMIT de PostgreSQL.
"""

import sys

from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import engine
from autenticacion import (
    generar_password_temporal,
    TEMP_PASSWORD_EXPIRE_HOURS,
)
from correo import enviar_password_temporal


# =========================================================
# CATÁLOGO ACADÉMICO DE USUARIOS INICIALES
# =========================================================
# Estos datos identifican las cuentas académicas y NO son
# secretos. Las contraseñas no forman parte del catálogo.
#
# compania = None significa que el usuario no pertenece a
# una compañía cliente. Es el caso del Coordinador TI.
# =========================================================

USUARIOS_INICIALES = [
    {"id_externo": "1051", "nombre": "Camilo Andres Mendoza Garcia", "email": "sanmile2703@gmail.com", "rol": "ADMIN_TI", "compania": None},
    {"id_externo": "2051", "nombre": "Juan Jose Perez Galvis", "email": "jeank04520@yahoo.es", "rol": "ADMIN_SOPORTE", "compania": "ANDINA"},
    {"id_externo": "3051", "nombre": "Pedro Pablo Gomez Herrera", "email": "joseprueba8318@yahoo.com", "rol": "ADMIN_SOPORTE", "compania": "PACIFICO"},
    {"id_externo": "4051", "nombre": "Maximiliano Jose Rumbo Ustaris", "email": "jean.c.almenarez@libertynet.com", "rol": "ADMIN_SOPORTE", "compania": "CARIBE"},
    {"id_externo": "5110", "nombre": "Camila Andrea Buitrago Ruiz", "email": "camiloandresmendozagarcia68@gmail.com", "rol": "LIDER_FACTURACION", "compania": "ANDINA"},
    {"id_externo": "5120", "nombre": "Jorge Andres Paez Lopez", "email": "yeisonfblopez@gmail.com", "rol": "LIDER_LOGISTICA", "compania": "ANDINA"},
    {"id_externo": "5130", "nombre": "Carolina Mendez Prada", "email": "rioscarvajal270388@gmail.com", "rol": "LIDER_GESTION_HUMANA", "compania": "ANDINA"},
    {"id_externo": "1110", "nombre": "Pedro Jose Gutierrez Mina", "email": "juanjoseperezgalvis1@gmail.com", "rol": "LIDER_FACTURACION", "compania": "PACIFICO"},
    {"id_externo": "1120", "nombre": "Jose Alberto Mosquera Lopez", "email": "ingrid.vesga-g@uniminuto.edu.co", "rol": "LIDER_LOGISTICA", "compania": "PACIFICO"},
    {"id_externo": "1130", "nombre": "Fernando Jose Buitrago Alvarez", "email": "bleidysliceniaalmenarezrios@gmail.com", "rol": "LIDER_GESTION_HUMANA", "compania": "PACIFICO"},
    {"id_externo": "2210", "nombre": "Joan Andres Vargas Rodriguez", "email": "jalmenarezr@uniminuto.edu.co", "rol": "LIDER_FACTURACION", "compania": "CARIBE"},
    {"id_externo": "2220", "nombre": "Dayana Isabel Vargas Rodriguez", "email": "oscar.acosta-m@uniminuto.edu.co", "rol": "LIDER_LOGISTICA", "compania": "CARIBE"},
    {"id_externo": "2230", "nombre": "Ingrid Yamile Contreras Polo", "email": "jean.almenarez@acttelematica.com.co", "rol": "LIDER_GESTION_HUMANA", "compania": "CARIBE"},
]


# =========================================================
# HASH DE CONTRASEÑAS
# =========================================================
# pwdlib utiliza la configuración recomendada. PostgreSQL
# almacena únicamente el hash, nunca la contraseña temporal.
# =========================================================

password_hasher = PasswordHash.recommended()


# =========================================================
# VALIDACIÓN PREVIA DEL CATÁLOGO
# =========================================================

def validar_catalogo() -> None:
    """
    Valida la integridad estructural del catálogo académico.

    No modifica los datos definidos por el proyecto y no procesa
    contraseñas ni otros secretos.
    """

    roles_permitidos = {
        "ADMIN_TI",
        "ADMIN_SOPORTE",
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA",
    }

    companias_permitidas = {
        None,
        "ANDINA",
        "PACIFICO",
        "CARIBE",
    }

    if len(USUARIOS_INICIALES) != 13:
        raise RuntimeError(
            "El catálogo académico debe contener 13 identidades"
        )

    ids = []
    emails = []

    for usuario in USUARIOS_INICIALES:
        campos_requeridos = {
            "id_externo",
            "nombre",
            "email",
            "rol",
            "compania",
        }

        if set(usuario) != campos_requeridos:
            raise RuntimeError(
                "El catálogo contiene una identidad con estructura inválida"
            )

        id_externo = str(usuario["id_externo"]).strip()
        nombre = str(usuario["nombre"]).strip()
        email = str(usuario["email"]).strip().lower()
        rol = usuario["rol"]
        compania = usuario["compania"]

        if not id_externo or not nombre or not email:
            raise RuntimeError(
                "El catálogo contiene campos obligatorios vacíos"
            )

        if rol not in roles_permitidos:
            raise RuntimeError(
                "El catálogo contiene un rol no permitido"
            )

        if compania not in companias_permitidas:
            raise RuntimeError(
                "El catálogo contiene una compañía no permitida"
            )

        # ADMIN_TI es global y no debe quedar asociado a una compañía.
        if rol == "ADMIN_TI" and compania is not None:
            raise RuntimeError(
                "ADMIN_TI no debe tener compañía asignada"
            )

        # Los demás roles del catálogo académico sí requieren compañía.
        if rol != "ADMIN_TI" and compania is None:
            raise RuntimeError(
                "La identidad requiere una compañía asignada"
            )

        ids.append(id_externo)
        emails.append(email)

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            "Existen id_externo duplicados en el catálogo"
        )

    if len(emails) != len(set(emails)):
        raise RuntimeError(
            "Existen correos duplicados en el catálogo"
        )


# =========================================================
# BOOTSTRAP PRINCIPAL
# =========================================================

def crear_usuarios_iniciales() -> None:
    validar_catalogo()

    creados = 0
    existentes = 0

    # -----------------------------------------------------
    # ENTREGA DE CREDENCIALES TEMPORALES
    # -----------------------------------------------------
    # Solo se conservan temporalmente en memoria las claves
    # de usuarios creados durante esta ejecución.
    #
    # El correo se envía DESPUÉS del COMMIT para evitar
    # entregar una contraseña cuya transacción pudiera ser
    # revertida posteriormente.
    # -----------------------------------------------------
    entregas_pendientes = []

    # -----------------------------------------------------
    # FASE 1 - PROVISIONAMIENTO ATÓMICO EN POSTGRESQL
    # -----------------------------------------------------

    with engine.begin() as conexion:

        for datos in USUARIOS_INICIALES:

            # -------------------------------------------------
            # 1. COMPROBAR EXISTENCIA
            # -------------------------------------------------

            existente = conexion.execute(
                text("""
                    SELECT id, id_externo, nombre, email
                    FROM usuarios_plataforma
                    WHERE id_externo = :id_externo
                       OR LOWER(email) = LOWER(:email)
                    LIMIT 1
                """),
                {
                    "id_externo": datos["id_externo"],
                    "email": datos["email"].strip().lower(),
                },
            ).mappings().first()

            if existente is not None:
                existentes += 1
                continue

            # -------------------------------------------------
            # 2. VALIDAR ROL
            # -------------------------------------------------

            rol = conexion.execute(
                text("""
                    SELECT id, nombre
                    FROM roles_plataforma
                    WHERE nombre = :rol
                      AND activo = TRUE
                    LIMIT 1
                """),
                {"rol": datos["rol"]},
            ).mappings().first()

            if rol is None:
                raise RuntimeError(
                    f"El rol {datos['rol']} no existe "
                    "o se encuentra inactivo"
                )

            # -------------------------------------------------
            # 3. VALIDAR COMPAÑÍA CUANDO APLIQUE
            # -------------------------------------------------

            compania = None

            if datos["compania"] is not None:
                compania = conexion.execute(
                    text("""
                        SELECT id, codigo, nombre
                        FROM companias
                        WHERE codigo = :codigo
                          AND activo = TRUE
                        LIMIT 1
                    """),
                    {"codigo": datos["compania"]},
                ).mappings().first()

                if compania is None:
                    raise RuntimeError(
                        f"La compañía {datos['compania']} "
                        "no existe o se encuentra inactiva"
                    )

            # -------------------------------------------------
            # 4. GENERAR CONTRASEÑA TEMPORAL Y HASH ARGON2
            # -------------------------------------------------
            # Reutilizamos el generador del Identity Service.
            # La contraseña temporal nunca se almacena en texto
            # claro en PostgreSQL.
            # -------------------------------------------------

            password_temporal = generar_password_temporal()
            password_hash = password_hasher.hash(
                password_temporal
            )

            # -------------------------------------------------
            # 5. CREAR IDENTIDAD
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
                    RETURNING id
                """),
                {
                    "id_externo": datos["id_externo"],
                    "nombre": datos["nombre"],
                    "email": datos["email"].strip().lower(),
                },
            ).mappings().one()

            # -------------------------------------------------
            # 6. CREAR CREDENCIAL TEMPORAL
            # -------------------------------------------------
            # - requiere_cambio_password obliga al cambio.
            # - password_temporal_expira_en limita su vigencia.
            # - La duración proviene de la configuración común
            #   TEMP_PASSWORD_EXPIRE_HOURS.
            # -------------------------------------------------

            conexion.execute(
                text("""
                    INSERT INTO credenciales (
                        usuario_id,
                        password_hash,
                        activo,
                        requiere_cambio_password,
                        password_temporal_expira_en
                    )
                    VALUES (
                        :usuario_id,
                        :password_hash,
                        TRUE,
                        TRUE,
                        NOW() + (
                            :temp_password_expire_hours
                            * INTERVAL '1 hour'
                        )
                    )
                """),
                {
                    "usuario_id": usuario["id"],
                    "password_hash": password_hash,
                    "temp_password_expire_hours":
                        TEMP_PASSWORD_EXPIRE_HOURS,
                },
            )

            # -------------------------------------------------
            # 7. ASIGNAR ROL
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
                    "usuario_id": usuario["id"],
                    "rol_id": rol["id"],
                },
            )

            # -------------------------------------------------
            # 8. ASIGNAR COMPAÑÍA
            # -------------------------------------------------
            # ADMIN_TI no necesita compañía.
            # Los demás usuarios reciben la compañía definida
            # en el catálogo académico.
            # -------------------------------------------------

            if compania is not None:
                conexion.execute(
                    text("""
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
                    """),
                    {
                        "usuario_id": usuario["id"],
                        "compania_id": compania["id"],
                    },
                )

            # -------------------------------------------------
            # 9. PREPARAR ENTREGA DE CREDENCIAL
            # -------------------------------------------------
            # El correo NO se envía dentro de la transacción.
            # -------------------------------------------------

            entregas_pendientes.append(
                {
                    "nombre": datos["nombre"],
                    "email": datos["email"].strip().lower(),
                    "password_temporal": password_temporal,
                }
            )

            creados += 1

    # -----------------------------------------------------
    # FASE 2 - ENVÍO DE CORREOS DESPUÉS DEL COMMIT
    # -----------------------------------------------------
    # Un fallo SMTP ya no puede provocar que PostgreSQL
    # revierta usuarios cuyas contraseñas fueron enviadas.
    #
    # Si una entrega falla, el usuario puede obtener una
    # contraseña nueva mediante el flujo seguro de
    # recuperación ya implementado.
    # -----------------------------------------------------

    correos_enviados = 0
    correos_fallidos = 0

    for entrega in entregas_pendientes:
        try:
            enviar_password_temporal(
                destinatario=entrega["email"],
                nombre_usuario=entrega["nombre"],
                password_temporal=entrega["password_temporal"],
            )
            correos_enviados += 1

        except Exception:
            # No mostramos correo ni contraseña en el error.
            correos_fallidos += 1

        finally:
            # No constituye borrado criptográfico de memoria,
            # pero evita conservar esta referencia explícita.
            entrega["password_temporal"] = None

    entregas_pendientes.clear()

    # -----------------------------------------------------
    # RESPUESTA SEGURA
    # -----------------------------------------------------

    print("Bootstrap de usuarios iniciales completado.")
    print(f"Usuarios creados: {creados}")
    print(f"Usuarios ya existentes: {existentes}")
    print(f"Correos enviados: {correos_enviados}")
    print(f"Correos con entrega pendiente: {correos_fallidos}")
    print("Contraseñas, hashes y tokens no fueron mostrados.")

    if correos_fallidos > 0:
        print(
            "ADVERTENCIA: alguna credencial temporal no pudo "
            "entregarse. Utilice el flujo seguro de recuperación "
            "de contraseña para generar una nueva.",
            file=sys.stderr,
        )


# =========================================================
# PUNTO DE ENTRADA
# =========================================================

if __name__ == "__main__":
    try:
        crear_usuarios_iniciales()

    except IntegrityError:
        print(
            "No fue posible completar el bootstrap debido "
            "a una restricción de integridad.",
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception:
        # SEGURIDAD:
        # No imprimimos el texto de la excepción original porque una
        # librería o servicio externo podría incluir datos sensibles.
        print(
            "No fue posible completar el bootstrap. "
            "Revise la configuración y los logs sanitizados del servicio.",
            file=sys.stderr,
        )
        sys.exit(1)
