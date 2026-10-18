# ========================================================

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from seguridad import requiere_roles
from autenticacion import (
    generar_password_temporal,
    TEMP_PASSWORD_EXPIRE_HOURS,
)
from correo import enviar_password_temporal
from database import engine
from auditoria import (
    registrar_evento,
    MFA_RESTABLECIDO_ADMIN,
    USUARIO_CREADO,
    USUARIO_ESTADO_MODIFICADO,
    USUARIO_MODIFICADO,
    USUARIO_ROL_MODIFICADO,
)
from sync_jobs import encolar_sync_job
from permisos_iniciales import asignar_vistas_iniciales


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios de plataforma"]
)


password_hasher = PasswordHash.recommended()


# =========================================================
# MODELOS PYDANTIC
# =========================================================

# =========================================================
# MODELO BASE PARA CORREOS ELECTRÓNICOS
# =========================================================
# El correo electrónico funciona como identificador de
# acceso del usuario.
#
# SEGURIDAD / INTEGRIDAD:
# - EmailStr valida que tenga formato de correo.
# - strip() elimina espacios accidentales.
# - lower() normaliza mayúsculas/minúsculas.
#
# Ejemplo:
#   "  Usuario@Empresa.COM  "
#              ↓
#   "usuario@empresa.com"
#
# La validación se realiza en backend, por lo que no depende
# de controles implementados posteriormente en React.
# =========================================================

class ModeloConEmail(BaseModel):

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def normalizar_email(cls, valor):
        if isinstance(valor, str):
            return valor.strip().lower()

        return valor


class UsuarioModificar(ModeloConEmail):
    # -----------------------------------------------------
    # DATOS BÁSICOS EDITABLES
    # -----------------------------------------------------
    # ADMIN_TI puede corregir estos campos únicamente sobre
    # usuarios ADMIN_SOPORTE.
    #
    # ADMIN_SOPORTE puede corregirlos únicamente sobre líderes
    # pertenecientes a su alcance multitenant.
    #
    # El rol, el estado y las compañías se administran mediante
    # endpoints independientes con autorización específica.
    # -----------------------------------------------------

    id_externo: str = Field(
        min_length=1,
        max_length=50
    )

    nombre: str = Field(
        min_length=1,
        max_length=100
    )

    email: EmailStr

    @field_validator("id_externo", mode="before")
    @classmethod
    def normalizar_id_externo(cls, valor):
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @field_validator("nombre", mode="before")
    @classmethod
    def normalizar_nombre(cls, valor):
        if isinstance(valor, str):
            return " ".join(valor.strip().split())
        return valor


class UsuarioEstado(BaseModel):
    activo: bool

# =========================================================
# MODELO PARA CAMBIO DE ROL DE USUARIO
# =========================================================
# Este modelo limita los roles que ADMIN_SOPORTE puede
# asignar a los usuarios líderes.
#
# Solo se permiten los tres roles funcionales definidos
# para las compañías del alcance académico.
#
# Esto evita que este endpoint pueda utilizarse para
# asignar roles administrativos como ADMIN_TI o
# ADMIN_SOPORTE.
# =========================================================

class UsuarioRolCambiar(BaseModel):
    rol: Literal[
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA"
    ]


class IdentidadCrear(ModeloConEmail):

    @field_validator("id_externo", mode="before")
    @classmethod
    def normalizar_id_externo(cls, valor):
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @field_validator("nombre", mode="before")
    @classmethod
    def normalizar_nombre(cls, valor):
        if isinstance(valor, str):
            return " ".join(valor.strip().split())
        return valor

    # -----------------------------------------------------
    # IDENTIFICADOR ACADÉMICO / EXTERNO
    # -----------------------------------------------------
    # Corresponde al identificador definido para cada
    # usuario en el alcance académico.
    #
    # Ejemplos: 1051, 2051, 5110, etc.
    #
    # No reemplaza el ID interno autogenerado por PostgreSQL.
    # -----------------------------------------------------

    id_externo: str = Field(
        min_length=1,
        max_length=50
    )

    # -----------------------------------------------------
    # DATOS BÁSICOS DEL USUARIO
    # -----------------------------------------------------

    nombre: str = Field(
        min_length=1,
        max_length=100
    )

    email: EmailStr


    # -----------------------------------------------------
    # COMPAÑÍA
    # -----------------------------------------------------
    # El campo es opcional a nivel del modelo porque el mismo
    # endpoint atiende dos flujos administrativos distintos:
    #
    # ADMIN_TI -> ADMIN_SOPORTE
    #   La cuenta se crea inicialmente SIN compañía. El alcance
    #   se delega posteriormente mediante /companias/asignaciones.
    #
    # ADMIN_SOPORTE -> LÍDER
    #   La compañía es obligatoria y debe pertenecer al alcance
    #   activo del ADMIN_SOPORTE autenticado.
    #
    # La obligatoriedad condicional se valida en el backend y
    # nunca se confía únicamente en la interfaz React.
    # -----------------------------------------------------

    compania_id: int | None = None

    # -----------------------------------------------------
    # ROLES PERMITIDOS EN CREACIÓN ADMINISTRATIVA
    # -----------------------------------------------------
    # ADMIN_TI no aparece porque es la cuenta coordinadora
    # inicial y no debe crearse mediante este endpoint.
    # -----------------------------------------------------

    rol: Literal[
        "ADMIN_SOPORTE",
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA"
    ]


# =========================================================
# LISTAR USUARIOS ADMINISTRABLES
# =========================================================
# Este endpoint implementa la jerarquía administrativa
# definida para el nuevo alcance del Identity Service.
#
# ADMIN_TI:
#   -> visualiza únicamente usuarios ADMIN_SOPORTE.
#
# ADMIN_SOPORTE:
#   -> visualiza únicamente líderes pertenecientes a las
#      compañías activas que tenga asignadas.
#
# Los usuarios líderes no tienen acceso a este listado.
#
# La autorización se valida nuevamente contra PostgreSQL
# para mantener el principio de mínimo privilegio.
# =========================================================

@router.get("")
def obtener_usuarios(
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # 1. OBTENER ROLES DEL USUARIO AUTENTICADO
    # -----------------------------------------------------

    roles_actual = set(
        usuario_actual.get("roles", [])
    )

    with engine.connect() as conexion:

        # -------------------------------------------------
        # 2. ADMIN_TI
        # -------------------------------------------------
        # El Coordinador TI puede administrar únicamente
        # usuarios que tengan el rol ADMIN_SOPORTE.
        #
        # También recuperamos las compañías asignadas al
        # soporte mediante agregación. Esto permitirá que
        # posteriormente un soporte tenga 1, 2 o 3 compañías
        # sin duplicar usuarios en la respuesta.
        # -------------------------------------------------

        if "ADMIN_TI" in roles_actual:

            consulta = text("""
                SELECT
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.email,
                    u.activo,
                    u.fecha_creacion,
                    u.fecha_modificacion,

                    COALESCE(
                        ARRAY_AGG(
                            DISTINCT c.nombre
                        ) FILTER (
                            WHERE c.id IS NOT NULL
                              AND c.activo = TRUE
                        ),
                        ARRAY[]::VARCHAR[]
                    ) AS companias

                FROM usuarios_plataforma u

                JOIN usuario_roles_plataforma ur
                    ON ur.usuario_id = u.id

                JOIN roles_plataforma r
                    ON r.id = ur.rol_id
                   AND r.activo = TRUE

                LEFT JOIN usuario_companias_plataforma uc
                    ON uc.usuario_id = u.id

                LEFT JOIN companias c
                    ON c.id = uc.compania_id

                WHERE r.nombre = 'ADMIN_SOPORTE'

                GROUP BY
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.email,
                    u.activo,
                    u.fecha_creacion,
                    u.fecha_modificacion

                ORDER BY u.id
            """)

            resultado = conexion.execute(
                consulta
            )

        # -------------------------------------------------
        # 3. ADMIN_SOPORTE
        # -------------------------------------------------
        # El soporte solamente puede visualizar líderes que
        # pertenezcan a una compañía activa que él mismo
        # tenga asignada.
        #
        # La consulta excluye roles administrativos y
        # cualquier rol legado.
        # -------------------------------------------------

        elif "ADMIN_SOPORTE" in roles_actual:

            consulta = text("""
                SELECT DISTINCT
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.email,
                    u.activo,

                    r.nombre AS rol,

                    c.id AS compania_id,
                    c.codigo AS compania_codigo,
                    c.nombre AS compania_nombre,

                    u.fecha_creacion,
                    u.fecha_modificacion

                FROM usuarios_plataforma u

                JOIN usuario_roles_plataforma ur
                    ON ur.usuario_id = u.id

                JOIN roles_plataforma r
                    ON r.id = ur.rol_id
                   AND r.activo = TRUE

                JOIN usuario_companias_plataforma
                    uc_objetivo
                    ON uc_objetivo.usuario_id = u.id

                JOIN companias c
                    ON c.id = uc_objetivo.compania_id
                   AND c.activo = TRUE

                JOIN usuario_companias_plataforma
                    uc_soporte
                    ON uc_soporte.compania_id = c.id

                WHERE uc_soporte.usuario_id =
                      :usuario_actual_id

                  AND r.nombre IN (
                      'LIDER_FACTURACION',
                      'LIDER_LOGISTICA',
                      'LIDER_GESTION_HUMANA'
                  )

                ORDER BY u.id
            """)

            resultado = conexion.execute(
                consulta,
                {
                    "usuario_actual_id":
                        usuario_actual["id"]
                }
            )

        # -------------------------------------------------
        # 4. DEFENSA ADICIONAL
        # -------------------------------------------------
        # requiere_roles() ya bloquea otros roles.
        # Esta validación mantiene explícita la política
        # también dentro de la lógica del endpoint.
        # -------------------------------------------------

        else:
            raise HTTPException(
                status_code=403,
                detail=(
                    "El usuario autenticado no tiene "
                    "permisos para listar usuarios"
                )
            )

        usuarios = [
            dict(usuario)
            for usuario in resultado.mappings().all()
        ]

    # -----------------------------------------------------
    # 5. RESPUESTA
    # -----------------------------------------------------
    # No se exponen credenciales, hashes, contraseñas,
    # tokens ni identificadores de sesión.
    # -----------------------------------------------------

    return {
        "total": len(usuarios),
        "usuarios": usuarios
    }

# =========================================================
# CREAR IDENTIDAD COMPLETA
# =========================================================
# La creación de una identidad se realiza de forma atómica.
#
# En una única transacción se crean:
#
# 1. Usuario de plataforma.
# 2. Credencial con hash Argon2.
# 3. Rol de plataforma.
# 4. Asignación a compañía únicamente cuando se crea un líder.
#
# Un ADMIN_SOPORTE creado por ADMIN_TI nace sin alcance de
# compañía. ADMIN_TI delega posteriormente dicho alcance mediante
# los endpoints específicos de /companias/asignaciones.
#
# MODELO DE AUTORIZACIÓN:
#
# ADMIN_TI
#   -> puede crear únicamente ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> puede crear únicamente:
#      - LIDER_FACTURACION
#      - LIDER_LOGISTICA
#      - LIDER_GESTION_HUMANA
#
#   -> solamente dentro de compañías activas que tenga
#      expresamente asignadas.
#
# SEGURIDAD:
# - contraseña temporal generada criptográficamente en backend;
# - almacenamiento únicamente mediante Argon2;
# - requiere_cambio_password = TRUE;
# - contraseña temporal con tiempo máximo de vigencia
#   configurable mediante TEMP_PASSWORD_EXPIRE_HOURS;
# - nunca se devuelve contraseña ni password_hash.
# =========================================================

@router.post(
    "/identidad",
    status_code=201
)
def crear_identidad(
    datos: IdentidadCrear,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    return _crear_identidad(datos, usuario_actual)


def _crear_identidad(datos: IdentidadCrear, usuario_actual, contexto_carga=None):
    # -----------------------------------------------------
    # 1. OBTENER ROLES DEL ADMINISTRADOR AUTENTICADO
    # -----------------------------------------------------

    roles_actual = set(
        usuario_actual.get("roles", [])
    )

    roles_lider = {
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA"
    }

    # -----------------------------------------------------
    # 2. VALIDAR JERARQUÍA DE CREACIÓN
    # -----------------------------------------------------
    # ADMIN_TI solamente puede crear ADMIN_SOPORTE.
    #
    # ADMIN_SOPORTE solamente puede crear líderes.
    # -----------------------------------------------------

    if "ADMIN_TI" in roles_actual:

        if datos.rol != "ADMIN_SOPORTE":
            raise HTTPException(
                status_code=403,
                detail=(
                    "ADMIN_TI solo puede crear "
                    "usuarios ADMIN_SOPORTE"
                )
            )

        # Separación explícita entre creación de cuenta y
        # delegación de alcance. La compañía se administra
        # posteriormente mediante /companias/asignaciones.
        if datos.compania_id is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "ADMIN_SOPORTE debe crearse sin compañía. "
                    "Asigne el alcance posteriormente desde "
                    "la administración de compañías."
                )
            )

    elif "ADMIN_SOPORTE" in roles_actual:

        if datos.rol not in roles_lider:
            raise HTTPException(
                status_code=403,
                detail=(
                    "ADMIN_SOPORTE solo puede crear "
                    "usuarios líderes"
                )
            )

        # Los líderes sí pertenecen obligatoriamente a una
        # compañía del alcance del ADMIN_SOPORTE.
        if datos.compania_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La compañía es obligatoria "
                    "para crear usuarios líderes"
                )
            )

    else:
        raise HTTPException(
            status_code=403,
            detail=(
                "El usuario autenticado no tiene permisos "
                "para crear identidades"
            )
        )

    # -----------------------------------------------------
    # 3. GENERAR CONTRASEÑA TEMPORAL EN EL BACKEND
    # -----------------------------------------------------
    # SEGURIDAD:
    #
    # El administrador que crea la identidad NO define
    # ni conoce previamente la contraseña temporal.
    #
    # La contraseña se genera mediante el generador
    # criptográficamente seguro centralizado en
    # autenticacion.py.
    #
    # Esto permite mantener el mismo mecanismo utilizado
    # por:
    # - recuperación de contraseña;
    # - reset administrativo;
    # - creación inicial de nuevas identidades.
    #
    # La contraseña temporal existe en texto plano
    # únicamente durante esta operación para poder ser
    # enviada al correo registrado del nuevo usuario.
    # -----------------------------------------------------

    password_temporal = generar_password_temporal()

    # -----------------------------------------------------
    # 4. GENERAR HASH ARGON2
    # -----------------------------------------------------
    # PostgreSQL nunca almacena la contraseña temporal
    # en texto plano.
    #
    # PasswordHash.recommended() utiliza Argon2 en la
    # configuración actual del Identity Service.
    # -----------------------------------------------------

    password_hash = password_hasher.hash(
        password_temporal
    )

    try:
        with engine.begin() as conexion:
            if contexto_carga is not None:
                existente = contexto_carga.iniciar(conexion)
                if existente is not None:
                    return {"usuario": {"id": existente}, "repetida": True}

            # -------------------------------------------------
            # 4. VALIDAR COMPAÑÍA CUANDO CORRESPONDA
            # -------------------------------------------------
            # ADMIN_TI -> ADMIN_SOPORTE:
            #   no se asigna compañía durante la creación.
            #
            # ADMIN_SOPORTE -> LÍDER:
            #   la compañía es obligatoria, debe estar activa y
            #   formar parte del alcance vigente del administrador.
            # -------------------------------------------------

            compania = None

            if "ADMIN_SOPORTE" in roles_actual:

                consulta_compania = text("""
                    SELECT
                        c.id,
                        c.codigo,
                        c.nombre
                    FROM companias c

                    JOIN usuario_companias_plataforma uc
                        ON uc.compania_id = c.id

                    WHERE c.id = :compania_id
                      AND uc.usuario_id = :admin_id
                      AND c.activo = TRUE
                """)

                compania = conexion.execute(
                    consulta_compania,
                    {
                        "compania_id":
                            datos.compania_id,

                        "admin_id":
                            usuario_actual["id"]
                    }
                ).mappings().first()

                if compania is None:
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "La compañía no existe, está inactiva "
                            "o no está asignada al administrador"
                        )
                    )

            # -------------------------------------------------
            # 5. OBTENER EL ROL SOLICITADO
            # -------------------------------------------------
            # Aunque Pydantic limita los valores posibles,
            # verificamos también que el rol exista y esté
            # activo en PostgreSQL.
            # -------------------------------------------------

            consulta_rol = text("""
                SELECT
                    id,
                    nombre
                FROM roles_plataforma
                WHERE nombre = :rol
                  AND activo = TRUE
            """)

            rol = conexion.execute(
                consulta_rol,
                {
                    "rol": datos.rol
                }
            ).mappings().first()

            if rol is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "El rol de plataforma "
                        "no existe o está inactivo"
                    )
                )

            # -------------------------------------------------
            # 6. CREAR USUARIO
            # -------------------------------------------------
            # id_externo corresponde al identificador
            # académico definido para cada usuario.
            #
            # PostgreSQL mantiene adicionalmente su propio
            # ID interno autoincremental.
            # -------------------------------------------------

            consulta_usuario = text("""
                INSERT INTO usuarios_plataforma (
                    id_externo,
                    nombre,
                    email,
                    activo,
                    fecha_creacion,
                    fecha_modificacion
                )
                VALUES (
                    :id_externo,
                    :nombre,
                    :email,
                    TRUE,
                    NOW(),
                    NOW()
                )
                RETURNING
                    id,
                    id_externo,
                    nombre,
                    email,
                    activo,
                    fecha_creacion,
                    fecha_modificacion
            """)

            usuario = conexion.execute(
                consulta_usuario,
                {
                    "id_externo":
                        datos.id_externo,

                    "nombre":
                        datos.nombre,

                    "email":
                        str(datos.email)
                }
            ).mappings().one()

            usuario_id = usuario["id"]

            # -------------------------------------------------
            # 7. CREAR CREDENCIAL TEMPORAL
            # -------------------------------------------------
            # La contraseña generada por el backend es temporal.
            #
            # SEGURIDAD:
            # - PostgreSQL almacena únicamente el hash Argon2.
            # - requiere_cambio_password = TRUE obliga al usuario
            #   a establecer una contraseña definitiva.
            # - password_temporal_expira_en limita el tiempo
            #   durante el cual puede utilizarse la contraseña
            #   temporal.
            #
            # La duración no se encuentra hardcodeada aquí.
            # Se obtiene de TEMP_PASSWORD_EXPIRE_HOURS, cuya
            # configuración se centraliza en autenticacion.py
            # y actualmente tiene un valor académico por defecto
            # de 24 horas.
            #
            # PostgreSQL calcula la fecha a partir de NOW() para
            # mantener una referencia temporal consistente con
            # el resto de los datos persistidos.
            # -------------------------------------------------

            consulta_credencial = text("""
                INSERT INTO credenciales (
                    usuario_id,
                    password_hash,
                    activo,
                    requiere_cambio_password,
                    password_temporal_expira_en,
                    fecha_creacion,
                    fecha_modificacion
                )
                VALUES (
                    :usuario_id,
                    :password_hash,
                    TRUE,
                    TRUE,
                    NOW() + (
                        :temp_password_expire_hours
                        * INTERVAL '1 hour'
                    ),
                    NOW(),
                    NOW()
                )
                RETURNING
                    id,
                    activo,
                    requiere_cambio_password,
                    password_temporal_expira_en,
                    fecha_creacion
            """)

            credencial = conexion.execute(
                consulta_credencial,
                {
                    "usuario_id":
                        usuario_id,

                    "password_hash":
                        password_hash,

                    "temp_password_expire_hours":
                        TEMP_PASSWORD_EXPIRE_HOURS
                }
            ).mappings().one()

            # -------------------------------------------------
            # 8. ASIGNAR ROL
            # -------------------------------------------------

            consulta_asignar_rol = text("""
                INSERT INTO usuario_roles_plataforma (
                    usuario_id,
                    rol_id,
                    fecha_asignacion
                )
                VALUES (
                    :usuario_id,
                    :rol_id,
                    NOW()
                )
                RETURNING
                    id,
                    fecha_asignacion
            """)

            asignacion_rol = conexion.execute(
                consulta_asignar_rol,
                {
                    "usuario_id":
                        usuario_id,

                    "rol_id":
                        rol["id"]
                }
            ).mappings().one()

            # -------------------------------------------------
            # 9. ASIGNAR COMPAÑÍA CUANDO CORRESPONDA
            # -------------------------------------------------
            # Los líderes deben quedar asociados a la compañía
            # validada dentro de esta misma transacción.
            #
            # ADMIN_SOPORTE se crea sin compañía. ADMIN_TI podrá
            # asignar o reasignar su alcance posteriormente con
            # /companias/asignaciones.
            # -------------------------------------------------

            asignacion_compania = None

            if compania is not None:
                consulta_asignar_compania = text("""
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
                        fecha_asignacion
                """)

                asignacion_compania = conexion.execute(
                    consulta_asignar_compania,
                    {
                        "usuario_id":
                            usuario_id,

                        "compania_id":
                            compania["id"]
                    }
                ).mappings().one()


            # -------------------------------------------------
            # 10. ENCOLAR PROVISIONAMIENTO ASÍNCRONO
            # -------------------------------------------------
            # El trabajo se registra dentro de la MISMA
            # transacción que crea la identidad.
            #
            # Si cualquier operación posterior falla, incluido
            # el envío de correo, PostgreSQL hace ROLLBACK tanto
            # de la identidad como del sync_job.
            #
            # El Worker solo podrá ver el trabajo después del
            # COMMIT. No se incluyen contraseñas, hashes, JWT,
            # JTI ni secretos MFA en la cola.
            # -------------------------------------------------

            # Las tres vistas del área nacen habilitadas en la misma transacción.
            # Solo se ejecuta al crear una identidad; no modifica líderes existentes.
            vistas_iniciales = asignar_vistas_iniciales(
                conexion, usuario_id,
                compania["id"] if compania is not None else None,
                rol["nombre"], usuario_actual["id"],
            )

            encolar_sync_job(
                conexion,
                operacion="PROVISIONAR",
                usuario_id=usuario_id,
                compania_id=(
                    compania["id"]
                    if compania is not None
                    else None
                ),
                solicitado_por_usuario_id=usuario_actual["id"],
            )

            # ------------------------------------------------------------
            # 11. ENVIAR CONTRASEÑA TEMPORAL POR CORREO
            # -------------------------------------------------
            # La contraseña temporal solamente se comunica al
            # propietario de la cuenta mediante el correo que
            # acaba de ser registrado.
            #
            # SEGURIDAD:
            # - no se devuelve mediante la API;
            # - no se almacena en texto plano;
            # - PostgreSQL conserva únicamente el hash Argon2;
            # - el usuario deberá cambiarla en su primer acceso.
            #
            # El envío se realiza antes de finalizar el bloque
            # transaccional. Si el envío genera una excepción,
            # engine.begin() realizará ROLLBACK de los cambios
            # pendientes en PostgreSQL.
            # -------------------------------------------------

            if contexto_carga is not None:
                contexto_carga.completar(conexion, usuario_id, rol["nombre"], vistas_iniciales)

            enviar_password_temporal(
                destinatario=str(datos.email),
                nombre_usuario=datos.nombre,
                password_temporal=password_temporal
            )


        # -----------------------------------------------------
        # 12. REGISTRAR EVENTO DE AUDITORÍA
        # -----------------------------------------------------
        # Se registra únicamente después del COMMIT exitoso.
        # No se incluyen contraseña temporal, hash, JWT, JTI,
        # correo ni secretos MFA en el detalle del evento.
        # -----------------------------------------------------

        if contexto_carga is None:
            registrar_evento(
                USUARIO_CREADO,
                actor_usuario_id=usuario_actual["id"],
                objetivo_usuario_id=usuario_id,
                compania_id=(
                    compania["id"]
                    if compania is not None
                    else None
                ),
                resultado="EXITO",
                detalle={
                    "rol": rol["nombre"],
                    "activo": usuario["activo"],
                    "requiere_cambio_password": (
                        credencial["requiere_cambio_password"]
                    ),
                    "operacion_sync": "PROVISIONAR",
                    "vistas_iniciales_habilitadas": vistas_iniciales,
                },
            )


        # -----------------------------------------------------
        # 13. RESPUESTA SEGURA
        # -----------------------------------------------------
        # La transacción ya hizo COMMIT.
        #
        # No devolvemos:
        # - contraseña temporal;
        # - password_hash;
        # - JWT;
        # - JTI.
        # -----------------------------------------------------

        return {
            "mensaje": (
                "ADMIN_SOPORTE creado correctamente. "
                "Asigne su alcance de compañías desde la "
                "administración de plataforma."
                if rol["nombre"] == "ADMIN_SOPORTE"
                else "Identidad creada correctamente"
            ),

            "usuario": {
                "id":
                    usuario["id"],

                "id_externo":
                    usuario["id_externo"],

                "nombre":
                    usuario["nombre"],

                "email":
                    usuario["email"],

                "activo":
                    usuario["activo"]
            },

            "compania": (
                {
                    "id":
                        compania["id"],

                    "codigo":
                        compania["codigo"],

                    "nombre":
                        compania["nombre"]
                }
                if compania is not None
                else None
            ),

            "rol":
                rol["nombre"],

            "credencial": {
                "id":
                    credencial["id"],

                "activo":
                    credencial["activo"],

                "requiere_cambio_password":
                    credencial["requiere_cambio_password"]
            },

            "asignaciones": {
                "rol_asignacion_id":
                    asignacion_rol["id"],

                "compania_asignacion_id":
                    (
                        asignacion_compania["id"]
                        if asignacion_compania is not None
                        else None
                    )
            }
        }

    except HTTPException:
        raise

    except IntegrityError as error:
        # -----------------------------------------------------
        # CONFLICTOS DE UNICIDAD
        # -----------------------------------------------------
        # Tanto email como id_externo deben identificar
        # unívocamente a la identidad.
        # -----------------------------------------------------

        mensaje_error = str(
            getattr(
                error,
                "orig",
                error
            )
        ).lower()

        if "id_externo" in mensaje_error:
            raise HTTPException(
                status_code=409,
                detail=(
                    "El identificador externo "
                    "ya está registrado"
                )
            )

        if "email" in mensaje_error:
            raise HTTPException(
                status_code=409,
                detail=(
                    "El correo electrónico "
                    "ya está registrado"
                )
            )

        raise HTTPException(
            status_code=409,
            detail=(
                "No fue posible crear la identidad "
                "por un conflicto de datos"
            )
        )

# =========================================================
# OBTENER USUARIO ADMINISTRABLE POR ID
# =========================================================
# Implementa la misma jerarquía utilizada por GET /usuarios.
#
# ADMIN_TI:
#   -> puede consultar únicamente ADMIN_SOPORTE.
#
# ADMIN_SOPORTE:
#   -> puede consultar únicamente líderes pertenecientes
#      a una compañía activa que tenga asignada.
#
# Los líderes no tienen acceso a este endpoint administrativo.
#
# No se exponen contraseñas, hashes, JWT, JTI ni credenciales.
# =========================================================

@router.get("/{usuario_id}")
def obtener_usuario(
    usuario_id: int,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # 1. EVITAR CONSULTA ADMINISTRATIVA SOBRE SÍ MISMO
    # -----------------------------------------------------
    # La información propia se obtiene mediante /auth/me.
    # Este endpoint se utiliza para administrar subordinados.
    # -----------------------------------------------------

    if usuario_id == usuario_actual["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Para consultar su propia identidad "
                "utilice /auth/me"
            )
        )

    roles_actual = set(
        usuario_actual.get("roles", [])
    )

    with engine.connect() as conexion:

        # -------------------------------------------------
        # 2. VERIFICAR EXISTENCIA DEL USUARIO
        # -------------------------------------------------

        consulta_existencia = text("""
            SELECT id
            FROM usuarios_plataforma
            WHERE id = :usuario_id
        """)

        usuario_existe = conexion.execute(
            consulta_existencia,
            {
                "usuario_id": usuario_id
            }
        ).first()

        if usuario_existe is None:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )

        # -------------------------------------------------
        # 3. ADMIN_TI -> ADMIN_SOPORTE
        # -------------------------------------------------
        # El Coordinador TI solamente puede consultar
        # identidades con el rol ADMIN_SOPORTE.
        #
        # Las compañías se agregan en un arreglo para
        # soportar 1, 2 o 3 compañías por usuario soporte.
        # -------------------------------------------------

        if "ADMIN_TI" in roles_actual:

            consulta = text("""
                SELECT
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.email,
                    u.activo,

                    r.nombre AS rol,

                    COALESCE(
                        ARRAY_AGG(
                            DISTINCT c.nombre
                        ) FILTER (
                            WHERE c.id IS NOT NULL
                              AND c.activo = TRUE
                        ),
                        ARRAY[]::VARCHAR[]
                    ) AS companias,

                    u.fecha_creacion,
                    u.fecha_modificacion

                FROM usuarios_plataforma u

                JOIN usuario_roles_plataforma ur
                    ON ur.usuario_id = u.id

                JOIN roles_plataforma r
                    ON r.id = ur.rol_id
                   AND r.activo = TRUE

                LEFT JOIN usuario_companias_plataforma uc
                    ON uc.usuario_id = u.id

                LEFT JOIN companias c
                    ON c.id = uc.compania_id

                WHERE u.id = :usuario_id
                  AND r.nombre = 'ADMIN_SOPORTE'

                GROUP BY
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.email,
                    u.activo,
                    r.nombre,
                    u.fecha_creacion,
                    u.fecha_modificacion
            """)

            usuario = conexion.execute(
                consulta,
                {
                    "usuario_id": usuario_id
                }
            ).mappings().first()

            if usuario is None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "ADMIN_TI solo puede consultar "
                        "usuarios ADMIN_SOPORTE"
                    )
                )

        # -------------------------------------------------
        # 4. ADMIN_SOPORTE -> LÍDERES
        # -------------------------------------------------
        # El soporte solamente puede consultar líderes
        # pertenecientes a sus compañías activas asignadas.
        # -------------------------------------------------

        elif "ADMIN_SOPORTE" in roles_actual:

            consulta = text("""
                SELECT DISTINCT
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.email,
                    u.activo,

                    r.nombre AS rol,

                    c.id AS compania_id,
                    c.codigo AS compania_codigo,
                    c.nombre AS compania_nombre,

                    u.fecha_creacion,
                    u.fecha_modificacion

                FROM usuarios_plataforma u

                JOIN usuario_roles_plataforma ur
                    ON ur.usuario_id = u.id

                JOIN roles_plataforma r
                    ON r.id = ur.rol_id
                   AND r.activo = TRUE

                JOIN usuario_companias_plataforma
                    uc_objetivo
                    ON uc_objetivo.usuario_id = u.id

                JOIN companias c
                    ON c.id = uc_objetivo.compania_id
                   AND c.activo = TRUE

                JOIN usuario_companias_plataforma
                    uc_soporte
                    ON uc_soporte.compania_id = c.id

                WHERE u.id = :usuario_id

                  AND uc_soporte.usuario_id =
                      :usuario_actual_id

                  AND r.nombre IN (
                      'LIDER_FACTURACION',
                      'LIDER_LOGISTICA',
                      'LIDER_GESTION_HUMANA'
                  )

                LIMIT 1
            """)

            usuario = conexion.execute(
                consulta,
                {
                    "usuario_id":
                        usuario_id,

                    "usuario_actual_id":
                        usuario_actual["id"]
                }
            ).mappings().first()

            if usuario is None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "No tiene permisos para consultar "
                        "este usuario o no pertenece a una "
                        "compañía asignada"
                    )
                )

        # -------------------------------------------------
        # 5. DEFENSA ADICIONAL
        # -------------------------------------------------

        else:
            raise HTTPException(
                status_code=403,
                detail=(
                    "El usuario autenticado no tiene "
                    "permisos para consultar usuarios"
                )
            )

    # -----------------------------------------------------
    # 6. RESPUESTA SEGURA
    # -----------------------------------------------------

    return dict(usuario)

# =========================================================
# MODIFICAR USUARIO ADMINISTRABLE
# =========================================================
# Permite modificar únicamente los datos básicos:
#
# - nombre
# - correo electrónico
#
# El cambio de rol y el cambio de estado se mantienen en
# operaciones independientes para aplicar autorización
# específica y mantener responsabilidades separadas.
#
# JERARQUÍA:
#
# ADMIN_TI
#   -> puede modificar únicamente ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> puede modificar únicamente líderes pertenecientes
#      a una compañía activa que tenga asignada.
#
# Un administrador no utiliza este endpoint para modificar
# su propia identidad.
# =========================================================

@router.put("/{usuario_id}")
def modificar_usuario(
    usuario_id: int,
    datos: UsuarioModificar,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # 1. EVITAR AUTOGESTIÓN MEDIANTE ENDPOINT ADMINISTRATIVO
    # -----------------------------------------------------

    if usuario_id == usuario_actual["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "No puede modificar su propia identidad "
                "mediante este endpoint administrativo"
            )
        )

    roles_actual = set(
        usuario_actual.get("roles", [])
    )

    try:
        with engine.begin() as conexion:

            # -------------------------------------------------
            # 2. VERIFICAR EXISTENCIA Y ROLES DEL OBJETIVO
            # -------------------------------------------------
            # Los roles se consultan directamente en PostgreSQL
            # para que la decisión de autorización utilice el
            # estado actual de la base de datos.
            # -------------------------------------------------

            consulta_objetivo = text("""
                SELECT
                    u.id,
                    ARRAY_AGG(
                        DISTINCT r.nombre
                    ) FILTER (
                        WHERE r.nombre IS NOT NULL
                          AND r.activo = TRUE
                    ) AS roles

                FROM usuarios_plataforma u

                LEFT JOIN usuario_roles_plataforma ur
                    ON ur.usuario_id = u.id

                LEFT JOIN roles_plataforma r
                    ON r.id = ur.rol_id

                WHERE u.id = :usuario_id

                GROUP BY u.id
            """)

            objetivo = conexion.execute(
                consulta_objetivo,
                {
                    "usuario_id": usuario_id
                }
            ).mappings().first()

            if objetivo is None:
                raise HTTPException(
                    status_code=404,
                    detail="Usuario no encontrado"
                )

            roles_objetivo = set(
                objetivo["roles"] or []
            )

            # Contexto opcional de compañía para el trabajo
            # asíncrono. ADMIN_TI administra ADMIN_SOPORTE de
            # forma global, por lo que puede permanecer en None.
            compania_id_sync = None

            # -------------------------------------------------
            # 3. AUTORIZACIÓN PARA ADMIN_TI
            # -------------------------------------------------
            # ADMIN_TI puede modificar solamente una identidad
            # cuyo conjunto de roles sea exactamente:
            #
            # {"ADMIN_SOPORTE"}
            #
            # Esto evita administrar accidentalmente usuarios
            # antiguos, líderes u otras cuentas privilegiadas.
            # -------------------------------------------------

            if "ADMIN_TI" in roles_actual:

                if roles_objetivo != {
                    "ADMIN_SOPORTE"
                }:
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "ADMIN_TI solo puede modificar "
                            "usuarios ADMIN_SOPORTE"
                        )
                    )

            # -------------------------------------------------
            # 4. AUTORIZACIÓN PARA ADMIN_SOPORTE
            # -------------------------------------------------

            elif "ADMIN_SOPORTE" in roles_actual:

                roles_lider_permitidos = {
                    "LIDER_FACTURACION",
                    "LIDER_LOGISTICA",
                    "LIDER_GESTION_HUMANA"
                }

                # El objetivo debe tener al menos un rol y
                # todos sus roles deben pertenecer al conjunto
                # permitido de líderes.
                if (
                    not roles_objetivo
                    or not roles_objetivo.issubset(
                        roles_lider_permitidos
                    )
                ):
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "ADMIN_SOPORTE solo puede modificar "
                            "usuarios líderes"
                        )
                    )

                # ---------------------------------------------
                # AISLAMIENTO MULTITENANT
                # ---------------------------------------------
                # Debe existir al menos una compañía activa
                # compartida entre ADMIN_SOPORTE y el usuario
                # objetivo.
                # ---------------------------------------------

                consulta_compania_compartida = text("""
                    SELECT
                        c.id AS compania_id

                    FROM usuario_companias_plataforma
                        soporte_compania

                    JOIN companias c
                        ON c.id =
                           soporte_compania.compania_id
                       AND c.activo = TRUE

                    JOIN usuario_companias_plataforma
                        objetivo_compania
                        ON objetivo_compania.compania_id =
                           soporte_compania.compania_id

                    WHERE soporte_compania.usuario_id =
                          :admin_id

                      AND objetivo_compania.usuario_id =
                          :usuario_id

                    LIMIT 1
                """)

                compania_compartida = conexion.execute(
                    consulta_compania_compartida,
                    {
                        "admin_id":
                            usuario_actual["id"],

                        "usuario_id":
                            usuario_id
                    }
                ).mappings().first()

                if compania_compartida is None:
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "No tiene acceso a una compañía "
                            "del usuario solicitado"
                        )
                    )

                compania_id_sync = compania_compartida[
                    "compania_id"
                ]

            else:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "El usuario autenticado no tiene "
                        "permisos para modificar usuarios"
                    )
                )

            # -------------------------------------------------
            # 5. MODIFICAR DATOS BÁSICOS
            # -------------------------------------------------

            consulta_actualizar = text("""
                UPDATE usuarios_plataforma
                SET
                    id_externo = :id_externo,
                    nombre = :nombre,
                    email = :email,
                    fecha_modificacion = NOW()

                WHERE id = :usuario_id

                RETURNING
                    id,
                    id_externo,
                    nombre,
                    email,
                    activo,
                    fecha_creacion,
                    fecha_modificacion
            """)

            usuario_actualizado = conexion.execute(
                consulta_actualizar,
                {
                    "usuario_id":
                        usuario_id,

                    "id_externo":
                        datos.id_externo,

                    "nombre":
                        datos.nombre,

                    "email":
                        str(datos.email)
                }
            ).mappings().one()

            # -------------------------------------------------
            # 5.1. REVOCAR SESIONES TRAS CAMBIAR IDENTIDAD
            # -------------------------------------------------
            # Nombre/correo forman parte del contexto de acceso.
            # Forzamos una nueva autenticación para que ninguna
            # sesión continúe utilizando datos anteriores.
            # -------------------------------------------------

            resultado_revocacion = conexion.execute(
                text("""
                    UPDATE sesiones
                    SET
                        revocada = TRUE,
                        fecha_revocacion = NOW()
                    WHERE usuario_id = :usuario_id
                      AND revocada = FALSE
                      AND fecha_expiracion > NOW()
                """),
                {
                    "usuario_id": usuario_id
                }
            )

            sesiones_revocadas = resultado_revocacion.rowcount

            # -------------------------------------------------
            # 6. ENCOLAR SINCRONIZACIÓN DE MODIFICACIÓN
            # -------------------------------------------------
            # El job comparte la transacción del UPDATE.
            # Si el INSERT del job falla, también se revierte
            # la modificación del usuario y la revocación de
            # sesiones.
            # -------------------------------------------------

            encolar_sync_job(
                conexion,
                operacion="MODIFICAR",
                usuario_id=usuario_id,
                compania_id=compania_id_sync,
                solicitado_por_usuario_id=usuario_actual["id"],
            )

        # -----------------------------------------------------
        # 7. REGISTRAR EVENTO DE AUDITORÍA
        # -----------------------------------------------------
        # El evento se genera después del COMMIT para no marcar
        # como exitoso un cambio que PostgreSQL pudiera revertir.
        # Solo se registran nombres de campos, no sus valores.
        # -----------------------------------------------------

        registrar_evento(
            USUARIO_MODIFICADO,
            actor_usuario_id=usuario_actual["id"],
            objetivo_usuario_id=usuario_id,
            compania_id=compania_id_sync,
            resultado="EXITO",
            detalle={
                "campos_modificados": [
                    "id_externo",
                    "nombre",
                    "email",
                ],
                "sesiones_revocadas": sesiones_revocadas,
                "operacion_sync": "MODIFICAR",
            },
        )

        # -----------------------------------------------------
        # 8. RESPUESTA SEGURA
        # -----------------------------------------------------

        return dict(
            usuario_actualizado
        )

    except HTTPException:
        raise

    except IntegrityError:
        # La base de datos mantiene las restricciones de unicidad.
        # No exponemos nombres de índices ni detalles internos.
        raise HTTPException(
            status_code=409,
            detail=(
                "El identificador externo o el correo electrónico "
                "ya está registrado"
            )
        )

# =========================================================
# ACTIVAR / DESACTIVAR USUARIO ADMINISTRABLE
# =========================================================
# Permite habilitar o deshabilitar identidades respetando
# la jerarquía administrativa del Identity Service.
#
# ADMIN_TI:
#   -> puede activar/desactivar únicamente ADMIN_SOPORTE.
#
# ADMIN_SOPORTE:
#   -> puede activar/desactivar únicamente líderes de las
#      compañías activas que tenga asignadas.
#
# SEGURIDAD:
# - No se permite modificar el estado de la propia cuenta.
# - Al desactivar una identidad se revocan sus sesiones
#   activas para invalidar inmediatamente sus tokens.
# - La autorización y la modificación se realizan dentro
#   de una única transacción.
# =========================================================

@router.patch("/{usuario_id}/estado")
def cambiar_estado_usuario(
    usuario_id: int,
    datos: UsuarioEstado,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # 1. IMPEDIR AUTOGESTIÓN DEL ESTADO
    # -----------------------------------------------------
    # Ni ADMIN_TI ni ADMIN_SOPORTE deben poder activar o
    # desactivar su propia identidad mediante este endpoint.
    # -----------------------------------------------------

    if usuario_id == usuario_actual["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "No puede modificar el estado "
                "de su propia identidad"
            )
        )

    roles_actual = set(
        usuario_actual.get("roles", [])
    )

    with engine.begin() as conexion:

        # -------------------------------------------------
        # 2. OBTENER USUARIO OBJETIVO Y SUS ROLES ACTIVOS
        # -------------------------------------------------
        # La autorización se basa en el estado actual de
        # PostgreSQL y no únicamente en datos suministrados
        # por el cliente.
        # -------------------------------------------------

        consulta_objetivo = text("""
            SELECT
                u.id,
                u.id_externo,
                u.nombre,
                u.email,
                u.activo,

                ARRAY_AGG(
                    DISTINCT r.nombre
                ) FILTER (
                    WHERE r.nombre IS NOT NULL
                      AND r.activo = TRUE
                ) AS roles

            FROM usuarios_plataforma u

            LEFT JOIN usuario_roles_plataforma ur
                ON ur.usuario_id = u.id

            LEFT JOIN roles_plataforma r
                ON r.id = ur.rol_id

            WHERE u.id = :usuario_id

            GROUP BY
                u.id,
                u.id_externo,
                u.nombre,
                u.email,
                u.activo
        """)

        objetivo = conexion.execute(
            consulta_objetivo,
            {
                "usuario_id": usuario_id
            }
        ).mappings().first()

        if objetivo is None:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )

        roles_objetivo = set(
            objetivo["roles"] or []
        )

        # Contexto opcional de compañía para el Sync Worker.
        # Un ADMIN_SOPORTE administrado por ADMIN_TI puede
        # tener varias compañías o ninguna, por lo que en ese
        # flujo se mantiene None.
        compania_id_sync = None

        # -------------------------------------------------
        # 3. AUTORIZACIÓN DE ADMIN_TI
        # -------------------------------------------------
        # El Coordinador TI administra únicamente cuentas
        # cuyo rol sea exactamente ADMIN_SOPORTE.
        # -------------------------------------------------

        if "ADMIN_TI" in roles_actual:

            if roles_objetivo != {
                "ADMIN_SOPORTE"
            }:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "ADMIN_TI solo puede cambiar "
                        "el estado de usuarios "
                        "ADMIN_SOPORTE"
                    )
                )

        # -------------------------------------------------
        # 4. AUTORIZACIÓN DE ADMIN_SOPORTE
        # -------------------------------------------------

        elif "ADMIN_SOPORTE" in roles_actual:

            roles_lider_permitidos = {
                "LIDER_FACTURACION",
                "LIDER_LOGISTICA",
                "LIDER_GESTION_HUMANA"
            }

            # El objetivo debe ser exclusivamente un usuario
            # perteneciente al conjunto de roles líder.
            if (
                not roles_objetivo
                or not roles_objetivo.issubset(
                    roles_lider_permitidos
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "ADMIN_SOPORTE solo puede cambiar "
                        "el estado de usuarios líderes"
                    )
                )

            # ---------------------------------------------
            # AISLAMIENTO MULTITENANT
            # ---------------------------------------------
            # Debe existir al menos una compañía activa
            # compartida entre el soporte autenticado y
            # el usuario objetivo.
            # ---------------------------------------------

            consulta_compania_compartida = text("""
                SELECT
                    c.id AS compania_id

                FROM usuario_companias_plataforma
                    soporte_compania

                JOIN companias c
                    ON c.id =
                       soporte_compania.compania_id
                   AND c.activo = TRUE

                JOIN usuario_companias_plataforma
                    objetivo_compania
                    ON objetivo_compania.compania_id =
                       soporte_compania.compania_id

                WHERE soporte_compania.usuario_id =
                      :admin_id

                  AND objetivo_compania.usuario_id =
                      :usuario_id

                LIMIT 1
            """)

            compania_compartida = conexion.execute(
                consulta_compania_compartida,
                {
                    "admin_id":
                        usuario_actual["id"],

                    "usuario_id":
                        usuario_id
                }
            ).mappings().first()

            if compania_compartida is None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "No tiene acceso a una compañía "
                        "del usuario solicitado"
                    )
                )

            compania_id_sync = compania_compartida[
                "compania_id"
            ]

        # -------------------------------------------------
        # 5. DEFENSA ADICIONAL
        # -------------------------------------------------

        else:
            raise HTTPException(
                status_code=403,
                detail=(
                    "El usuario autenticado no tiene "
                    "permisos para cambiar el estado "
                    "de usuarios"
                )
            )

        # -------------------------------------------------
        # 6. ACTIVAR / DESACTIVAR IDENTIDAD
        # -------------------------------------------------

        consulta_actualizar = text("""
            UPDATE usuarios_plataforma
            SET
                activo = :activo,
                fecha_modificacion = NOW()

            WHERE id = :usuario_id

            RETURNING
                id,
                id_externo,
                nombre,
                email,
                activo,
                fecha_creacion,
                fecha_modificacion
        """)

        usuario = conexion.execute(
            consulta_actualizar,
            {
                "usuario_id":
                    usuario_id,

                "activo":
                    datos.activo
            }
        ).mappings().one()

        # -------------------------------------------------
        # 7. REVOCAR SESIONES AL DESACTIVAR
        # -------------------------------------------------
        # Aunque seguridad.py también verifica que la
        # identidad esté activa en cada solicitud, marcar
        # las sesiones como revocadas mantiene coherencia
        # entre el estado de la identidad y las sesiones.
        #
        # Todo ocurre en la misma transacción: si alguna
        # operación falla, PostgreSQL revierte el conjunto.
        # -------------------------------------------------

        sesiones_revocadas = 0

        if datos.activo is False:

            consulta_revocar_sesiones = text("""
                UPDATE sesiones
                SET
                    revocada = TRUE,
                    fecha_revocacion = NOW()

                WHERE usuario_id = :usuario_id
                  AND revocada = FALSE
                  AND fecha_expiracion > NOW()
            """)

            resultado_revocacion = conexion.execute(
                consulta_revocar_sesiones,
                {
                    "usuario_id":
                        usuario_id
                }
            )

            sesiones_revocadas = (
                resultado_revocacion.rowcount
            )

        # -------------------------------------------------
        # 8. ENCOLAR CAMBIO DE ESTADO
        # -------------------------------------------------
        # Activar una identidad solicita PROVISIONAR.
        # Desactivarla solicita DESHABILITAR.
        #
        # El job se registra en la misma transacción del
        # cambio de estado y de la revocación de sesiones.
        # -------------------------------------------------

        encolar_sync_job(
            conexion,
            operacion=(
                "PROVISIONAR"
                if datos.activo
                else "DESHABILITAR"
            ),
            usuario_id=usuario_id,
            compania_id=compania_id_sync,
            solicitado_por_usuario_id=usuario_actual["id"],
        )

    # -----------------------------------------------------
    # 9. REGISTRAR EVENTO DE AUDITORÍA
    # -----------------------------------------------------
    # Se registra después del COMMIT exitoso y únicamente con
    # metadatos administrativos necesarios.
    # -----------------------------------------------------

    registrar_evento(
        USUARIO_ESTADO_MODIFICADO,
        actor_usuario_id=usuario_actual["id"],
        objetivo_usuario_id=usuario_id,
        compania_id=compania_id_sync,
        resultado="EXITO",
        detalle={
            "activo": datos.activo,
            "sesiones_revocadas": sesiones_revocadas,
            "operacion_sync": (
                "PROVISIONAR"
                if datos.activo
                else "DESHABILITAR"
            ),
        },
    )

    # -----------------------------------------------------
    # 10. RESPUESTA SEGURA
    # -----------------------------------------------------
    # Solo informamos cuántas sesiones fueron revocadas.
    # No exponemos JWT, JTI, hashes ni credenciales.
    # -----------------------------------------------------

    respuesta = dict(usuario)

    respuesta["sesiones_revocadas"] = (
        sesiones_revocadas
    )

    return respuesta

# =========================================================
# CAMBIAR ROL DE USUARIO LÍDER
# =========================================================
# Este endpoint implementa el requisito académico que
# permite a ADMIN_SOPORTE cambiar el rol funcional de los
# usuarios pertenecientes a sus compañías asignadas.
#
# ROLES DESTINO PERMITIDOS:
#
# - LIDER_FACTURACION
# - LIDER_LOGISTICA
# - LIDER_GESTION_HUMANA
#
# SEGURIDAD:
#
# 1. Solo ADMIN_SOPORTE puede ejecutar esta operación.
# 2. El usuario objetivo debe ser actualmente un líder.
# 3. Debe existir una compañía activa compartida entre
#    ADMIN_SOPORTE y el usuario objetivo.
# 4. El nuevo rol debe existir y estar activo.
# 5. Se mantiene un único rol líder por usuario.
# 6. Las sesiones activas del usuario se revocan después
#    del cambio para aplicar inmediatamente la autorización.
# =========================================================

@router.patch("/{usuario_id}/rol")
def cambiar_rol_usuario(
    usuario_id: int,
    datos: UsuarioRolCambiar,
    usuario_actual=Depends(
        requiere_roles("ADMIN_SOPORTE")
    )
):
    # -----------------------------------------------------
    # 1. IMPEDIR AUTOGESTIÓN ADMINISTRATIVA
    # -----------------------------------------------------

    if usuario_id == usuario_actual["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "No puede modificar su propio rol mediante "
                "este endpoint administrativo"
            )
        )

    roles_lider_permitidos = {
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA"
    }

    with engine.begin() as conexion:

        # -------------------------------------------------
        # 2. OBTENER USUARIO OBJETIVO Y ROLES ACTUALES
        # -------------------------------------------------

        consulta_objetivo = text("""
            SELECT
                u.id,
                u.id_externo,
                u.nombre,
                u.email,
                u.activo,

                ARRAY_AGG(
                    DISTINCT r.nombre
                ) FILTER (
                    WHERE r.nombre IS NOT NULL
                      AND r.activo = TRUE
                ) AS roles

            FROM usuarios_plataforma u

            LEFT JOIN usuario_roles_plataforma ur
                ON ur.usuario_id = u.id

            LEFT JOIN roles_plataforma r
                ON r.id = ur.rol_id

            WHERE u.id = :usuario_id

            GROUP BY
                u.id,
                u.id_externo,
                u.nombre,
                u.email,
                u.activo
        """)

        objetivo = conexion.execute(
            consulta_objetivo,
            {
                "usuario_id": usuario_id
            }
        ).mappings().first()

        if objetivo is None:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )

        roles_objetivo = set(
            objetivo["roles"] or []
        )

        # -------------------------------------------------
        # 3. VALIDAR QUE EL OBJETIVO SEA UN LÍDER
        # -------------------------------------------------
        # No basta con impedir ADMIN_TI o ADMIN_SOPORTE.
        # Exigimos que todos los roles actuales del objetivo
        # pertenezcan al conjunto permitido de líderes.
        #
        # Esto también impide modificar usuarios antiguos
        # ADMIN, ANALYST o VIEWER.
        # -------------------------------------------------

        if (
            not roles_objetivo
            or not roles_objetivo.issubset(
                roles_lider_permitidos
            )
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "ADMIN_SOPORTE solo puede cambiar "
                    "roles de usuarios líderes"
                )
            )

        # -------------------------------------------------
        # 4. VERIFICAR AISLAMIENTO MULTITENANT
        # -------------------------------------------------
        # El usuario objetivo debe compartir al menos una
        # compañía activa con ADMIN_SOPORTE.
        # -------------------------------------------------

        consulta_compania = text("""
            SELECT
                c.id,
                c.codigo,
                c.nombre

            FROM usuario_companias_plataforma
                soporte_compania

            JOIN companias c
                ON c.id =
                   soporte_compania.compania_id
               AND c.activo = TRUE

            JOIN usuario_companias_plataforma
                objetivo_compania
                ON objetivo_compania.compania_id =
                   soporte_compania.compania_id

            WHERE soporte_compania.usuario_id =
                  :admin_id

              AND objetivo_compania.usuario_id =
                  :usuario_id

            ORDER BY c.id

            LIMIT 1
        """)

        compania = conexion.execute(
            consulta_compania,
            {
                "admin_id":
                    usuario_actual["id"],

                "usuario_id":
                    usuario_id
            }
        ).mappings().first()

        if compania is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "No tiene acceso a una compañía "
                    "del usuario solicitado"
                )
            )

        # -------------------------------------------------
        # 5. OBTENER Y VALIDAR EL NUEVO ROL
        # -------------------------------------------------
        # Literal ya restringe los valores recibidos desde
        # la API. Aun así, consultamos PostgreSQL para
        # verificar que el rol exista y esté activo.
        # -------------------------------------------------

        consulta_nuevo_rol = text("""
            SELECT
                id,
                nombre
            FROM roles_plataforma
            WHERE nombre = :rol
              AND activo = TRUE
        """)

        nuevo_rol = conexion.execute(
            consulta_nuevo_rol,
            {
                "rol": datos.rol
            }
        ).mappings().first()

        if nuevo_rol is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "El rol solicitado no existe "
                    "o se encuentra inactivo"
                )
            )

        # -------------------------------------------------
        # 6. DETECTAR SI EL USUARIO YA TIENE ESE ROL
        # -------------------------------------------------

        if (
            roles_objetivo == {
                datos.rol
            }
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "El usuario ya tiene asignado "
                    "el rol solicitado"
                )
            )

        # -------------------------------------------------
        # 7. ELIMINAR ROLES LÍDER ACTUALES
        # -------------------------------------------------
        # Primero eliminamos únicamente los roles que
        # pertenecen al conjunto funcional de líderes.
        #
        # No utilizamos un DELETE general de todos los roles.
        # Esto reduce el alcance de la modificación.
        # -------------------------------------------------

        consulta_eliminar_roles = text("""
            DELETE FROM usuario_roles_plataforma

            WHERE usuario_id = :usuario_id

              AND rol_id IN (
                  SELECT id
                  FROM roles_plataforma
                  WHERE nombre IN (
                      'LIDER_FACTURACION',
                      'LIDER_LOGISTICA',
                      'LIDER_GESTION_HUMANA'
                  )
              )
        """)

        conexion.execute(
            consulta_eliminar_roles,
            {
                "usuario_id":
                    usuario_id
            }
        )

        # -------------------------------------------------
        # 8. ASIGNAR EL NUEVO ROL
        # -------------------------------------------------

        consulta_asignar_rol = text("""
            INSERT INTO usuario_roles_plataforma (
                usuario_id,
                rol_id,
                fecha_asignacion
            )
            VALUES (
                :usuario_id,
                :rol_id,
                NOW()
            )
            RETURNING id
        """)

        asignacion = conexion.execute(
            consulta_asignar_rol,
            {
                "usuario_id":
                    usuario_id,

                "rol_id":
                    nuevo_rol["id"]
            }
        ).mappings().one()

        # -------------------------------------------------
        # 9. REVOCAR SESIONES ACTIVAS
        # -------------------------------------------------
        # El usuario debe autenticarse nuevamente para que
        # cualquier nueva sesión opere bajo el rol actualizado.
        # -------------------------------------------------

        consulta_revocar = text("""
            UPDATE sesiones
            SET
                revocada = TRUE,
                fecha_revocacion = NOW()

            WHERE usuario_id = :usuario_id
              AND revocada = FALSE
              AND fecha_expiracion > NOW()
        """)

        resultado_revocacion = conexion.execute(
            consulta_revocar,
            {
                "usuario_id":
                    usuario_id
            }
        )

        sesiones_revocadas = (
            resultado_revocacion.rowcount
        )

        # -------------------------------------------------
        # 10. ENCOLAR SINCRONIZACIÓN DEL CAMBIO DE ROL
        # -------------------------------------------------
        # El cambio de rol modifica la representación de la
        # identidad en sistemas integrados, por lo que se
        # publica como MODIFICAR.
        # -------------------------------------------------

        encolar_sync_job(
            conexion,
            operacion="MODIFICAR",
            usuario_id=usuario_id,
            compania_id=compania["id"],
            solicitado_por_usuario_id=usuario_actual["id"],
        )

    # -----------------------------------------------------
    # 11. REGISTRAR EVENTO DE AUDITORÍA
    # -----------------------------------------------------
    # El evento se emite después de completar correctamente
    # la transacción para no registrar como exitoso un cambio
    # que PostgreSQL pudiera revertir.
    #
    # SEGURIDAD:
    # - no se registran JWT, JTI, contraseñas ni hashes;
    # - solo se incluyen datos administrativos necesarios;
    # - auditoria.py aplica sanitización adicional.
    # -----------------------------------------------------

    registrar_evento(
        USUARIO_ROL_MODIFICADO,
        actor_usuario_id=usuario_actual["id"],
        objetivo_usuario_id=usuario_id,
        compania_id=compania["id"],
        resultado="EXITO",
        detalle={
            "rol_anterior": sorted(roles_objetivo),
            "rol_nuevo": nuevo_rol["nombre"],
            "sesiones_revocadas": sesiones_revocadas,
        },
    )

    # -----------------------------------------------------
    # 12. RESPUESTA SEGURA
    # -----------------------------------------------------
    # No se devuelven JWT, JTI, credenciales ni hashes.
    # -----------------------------------------------------

    return {
        "mensaje":
            "Rol actualizado correctamente",

        "usuario": {
            "id":
                objetivo["id"],

            "id_externo":
                objetivo["id_externo"],

            "nombre":
                objetivo["nombre"],

            "email":
                objetivo["email"],

            "activo":
                objetivo["activo"]
        },

        "compania": {
            "id":
                compania["id"],

            "codigo":
                compania["codigo"],

            "nombre":
                compania["nombre"]
        },

        "rol_anterior":
            sorted(
                roles_objetivo
            ),

        "rol_nuevo":
            nuevo_rol["nombre"],

        "rol_asignacion_id":
            asignacion["id"],

        "sesiones_revocadas":
            sesiones_revocadas
    }

# =========================================================
# RESTABLECER MFA DE USUARIO LÍDER
# =========================================================
# Operación administrativa de recuperación de segundo factor.
#
# AUTORIZACIÓN:
# - Exclusiva para ADMIN_SOPORTE.
# - El usuario objetivo debe ser un líder.
# - Debe compartir una compañía ACTIVA con el ADMIN_SOPORTE.
# - No permite autogestión.
#
# SEGURIDAD:
# - El administrador NO recibe el secreto TOTP ni un código QR.
# - Se elimina la vinculación TOTP existente para que el propio
#   usuario realice un nuevo enrolamiento en su siguiente login.
# - Se invalidan todos los desafíos MFA pendientes del usuario.
# - Se revocan todas sus sesiones activas.
# - Contraseña y estado de bloqueo NO se modifican.
# - Toda la mutación ocurre en una única transacción.
# =========================================================

@router.post("/{usuario_id}/mfa/restablecer")
def restablecer_mfa_usuario(
    usuario_id: int,
    usuario_actual=Depends(
        requiere_roles("ADMIN_SOPORTE")
    )
):
    # -----------------------------------------------------
    # 1. IMPEDIR AUTOGESTIÓN
    # -----------------------------------------------------
    if usuario_id == usuario_actual["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "No puede restablecer su propio MFA mediante "
                "este endpoint administrativo"
            )
        )

    roles_lider_permitidos = {
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA",
    }

    with engine.begin() as conexion:
        # -------------------------------------------------
        # 2. OBTENER Y BLOQUEAR EL USUARIO OBJETIVO
        # -------------------------------------------------
        # FOR UPDATE evita que dos restablecimientos
        # administrativos modifiquen simultáneamente el mismo
        # estado de identidad.
        # -------------------------------------------------
        objetivo = conexion.execute(
            text("""
                SELECT
                    u.id,
                    u.id_externo,
                    u.nombre,
                    u.activo
                FROM usuarios_plataforma u
                WHERE u.id = :usuario_id
                FOR UPDATE
            """),
            {
                "usuario_id": usuario_id
            }
        ).mappings().first()

        if objetivo is None:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )

        # -------------------------------------------------
        # 3. VALIDAR QUE EL OBJETIVO SEA UN LÍDER
        # -------------------------------------------------
        roles_objetivo = {
            fila["nombre"]
            for fila in conexion.execute(
                text("""
                    SELECT DISTINCT r.nombre
                    FROM usuario_roles_plataforma ur
                    JOIN roles_plataforma r
                      ON r.id = ur.rol_id
                     AND r.activo = TRUE
                    WHERE ur.usuario_id = :usuario_id
                """),
                {
                    "usuario_id": usuario_id
                }
            ).mappings().all()
        }

        if (
            not roles_objetivo
            or not roles_objetivo.issubset(
                roles_lider_permitidos
            )
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "ADMIN_SOPORTE solo puede restablecer "
                    "MFA de usuarios líderes"
                )
            )

        # -------------------------------------------------
        # 4. VALIDAR AISLAMIENTO MULTITENANT
        # -------------------------------------------------
        # Debe existir una compañía activa compartida entre
        # el soporte autenticado y el líder objetivo.
        # -------------------------------------------------
        compania = conexion.execute(
            text("""
                SELECT
                    c.id,
                    c.codigo,
                    c.nombre
                FROM usuario_companias_plataforma soporte_compania

                JOIN companias c
                  ON c.id = soporte_compania.compania_id
                 AND c.activo = TRUE

                JOIN usuario_companias_plataforma objetivo_compania
                  ON objetivo_compania.compania_id =
                     soporte_compania.compania_id

                WHERE soporte_compania.usuario_id = :admin_id
                  AND objetivo_compania.usuario_id = :usuario_id

                ORDER BY c.id
                LIMIT 1
            """),
            {
                "admin_id": usuario_actual["id"],
                "usuario_id": usuario_id,
            }
        ).mappings().first()

        if compania is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "No tiene permisos para restablecer MFA "
                    "de este usuario"
                )
            )

        if not objetivo["activo"]:
            raise HTTPException(
                status_code=400,
                detail="El usuario se encuentra inactivo"
            )

        # -------------------------------------------------
        # 5. COMPROBAR QUE EXISTA UNA VINCULACIÓN MFA
        # -------------------------------------------------
        # No devolvemos ni desciframos secreto_cifrado.
        # Solamente verificamos existencia/estado.
        # -------------------------------------------------
        mfa_actual = conexion.execute(
            text("""
                SELECT
                    id,
                    activo
                FROM mfa_totp
                WHERE usuario_id = :usuario_id
                FOR UPDATE
            """),
            {
                "usuario_id": usuario_id
            }
        ).mappings().first()

        if mfa_actual is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "El usuario no tiene una vinculación MFA "
                    "para restablecer"
                )
            )

        # -------------------------------------------------
        # 6. INVALIDAR DESAFÍOS MFA PENDIENTES
        # -------------------------------------------------
        # Esto impide que un desafío emitido antes del
        # restablecimiento pueda utilizarse después.
        # -------------------------------------------------
        resultado_desafios = conexion.execute(
            text("""
                UPDATE mfa_desafios
                SET
                    usado = TRUE,
                    usado_en = COALESCE(usado_en, NOW())
                WHERE usuario_id = :usuario_id
                  AND usado = FALSE
            """),
            {
                "usuario_id": usuario_id
            }
        )

        desafios_invalidados = resultado_desafios.rowcount

        # -------------------------------------------------
        # 7. REVOCAR SESIONES ACTIVAS
        # -------------------------------------------------
        # Un restablecimiento de MFA es un cambio sensible.
        # Cualquier sesión existente debe autenticarse de nuevo.
        # -------------------------------------------------
        resultado_sesiones = conexion.execute(
            text("""
                UPDATE sesiones
                SET
                    revocada = TRUE,
                    fecha_revocacion = NOW()
                WHERE usuario_id = :usuario_id
                  AND revocada = FALSE
                  AND fecha_expiracion > NOW()
            """),
            {
                "usuario_id": usuario_id
            }
        )

        sesiones_revocadas = resultado_sesiones.rowcount

        # -------------------------------------------------
        # 8. ELIMINAR LA VINCULACIÓN TOTP
        # -------------------------------------------------
        # La eliminación del registro cifrado provoca que el
        # login obligatorio detecte al usuario como no enrolado.
        # El NUEVO secreto y el QR serán generados únicamente
        # para el propio usuario durante el siguiente login.
        # -------------------------------------------------
        resultado_mfa = conexion.execute(
            text("""
                DELETE FROM mfa_totp
                WHERE usuario_id = :usuario_id
            """),
            {
                "usuario_id": usuario_id
            }
        )

        if resultado_mfa.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "No fue posible restablecer la vinculación MFA"
                )
            )

        # T06: persistir auditoría sanitizada antes del COMMIT.
        registrar_evento(
            MFA_RESTABLECIDO_ADMIN,
            actor_usuario_id=usuario_actual["id"],
            objetivo_usuario_id=usuario_id,
            compania_id=compania["id"],
            resultado="EXITO",
            conexion=conexion,
            detalle={
                "sesiones_revocadas": sesiones_revocadas,
                "desafios_mfa_invalidados": desafios_invalidados,
            },
        )

    # -----------------------------------------------------
    # 10. RESPUESTA SEGURA
    # -----------------------------------------------------
    # El administrador solo recibe el resultado administrativo.
    # Nunca se devuelve secreto, URI otpauth, QR o código TOTP.
    # -----------------------------------------------------
    return {
        "mensaje": (
            "MFA restablecido correctamente. "
            "El usuario deberá vincular Authenticator "
            "en su próximo inicio de sesión."
        ),
        "usuario_id": objetivo["id"],
        "sesiones_revocadas": sesiones_revocadas,
        "desafios_mfa_invalidados": desafios_invalidados,
    }
