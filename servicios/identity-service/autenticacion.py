# =========================================================
# INICIO CODIGO autenticacion.py
# =========================================================

import os
import secrets
import string
import re
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from correo import enviar_password_temporal

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import text


from database import engine
from seguridad import (
    obtener_usuario_desde_token,
    requiere_roles,
)
from auditoria import (
    registrar_evento,
    LOGIN_EXITOSO,
    LOGIN_FALLIDO,
    CUENTA_BLOQUEADA,
    CUENTA_DESBLOQUEADA,
    PASSWORD_RECUPERADA,
    SESIONES_EXPIRADAS_ELIMINADAS,
    MFA_ENROLAMIENTO_INICIADO,
    MFA_ACTIVADO,
    MFA_LOGIN_EXITOSO,
    MFA_LOGIN_FALLIDO,
)

from mfa import (
    generar_secreto_totp,
    cifrar_secreto_totp,
    descifrar_secreto_totp,
    generar_qr_aprovisionamiento_png,
    validar_codigo_totp,
    consumir_contador_totp,
)

# =========================================================
# CONFIGURACIÓN
# =========================================================

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

password_hasher = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET")

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

JWT_EXPIRE_MINUTES = int(
    os.getenv(
        "JWT_EXPIRE_MINUTES",
        "30"
    )
)

# =========================================================
# SEGURIDAD - EXPIRACIÓN DE CONTRASEÑA TEMPORAL
# =========================================================
# Define durante cuántas horas puede utilizarse una
# contraseña temporal generada por recuperación o por
# restablecimiento administrativo.
#
# El valor se obtiene desde una variable de entorno para
# evitar dejar la política fija dentro de la lógica.
#
# Valor académico predeterminado: 24 horas.
# =========================================================

try:
    TEMP_PASSWORD_EXPIRE_HOURS = int(
        os.getenv(
            "TEMP_PASSWORD_EXPIRE_HOURS",
            "24"
        )
    )
except ValueError:
    raise RuntimeError(
        "TEMP_PASSWORD_EXPIRE_HOURS debe ser un número entero"
    )

if TEMP_PASSWORD_EXPIRE_HOURS <= 0:
    raise RuntimeError(
        "TEMP_PASSWORD_EXPIRE_HOURS debe ser mayor que cero"
    )


# =========================================================
# SEGURIDAD - EXPIRACIÓN DE CONTRASEÑA DEFINITIVA
# =========================================================
# Define durante cuántos días puede utilizarse una contraseña
# definitiva antes de exigir al usuario un nuevo cambio.
#
# La política se obtiene desde una variable de entorno para
# evitar dejar el período de vigencia fijo dentro del código.
#
# Valor académico predeterminado: 60 días.
# =========================================================

try:
    PASSWORD_EXPIRE_DAYS = int(
        os.getenv(
            "PASSWORD_EXPIRE_DAYS",
            "60"
        )
    )
except ValueError:
    raise RuntimeError(
        "PASSWORD_EXPIRE_DAYS debe ser un número entero"
    )

if PASSWORD_EXPIRE_DAYS <= 0:
    raise RuntimeError(
        "PASSWORD_EXPIRE_DAYS debe ser mayor que cero"
    )

# =========================================================
# COOLDOWN DE RECUPERACIÓN DE CONTRASEÑA
# =========================================================
# Limita la frecuencia con la que una misma cuenta puede
# generar una nueva contraseña temporal mediante el endpoint
# público de recuperación.
#
# El valor se configura mediante variable de entorno para
# evitar tiempos hardcodeados dentro de la lógica del
# endpoint.
#
# Este control complementa la respuesta genérica utilizada
# contra enumeración de cuentas.
# =========================================================

try:
    PASSWORD_RECOVERY_COOLDOWN_MINUTES = int(
        os.getenv(
            "PASSWORD_RECOVERY_COOLDOWN_MINUTES",
            "15"
        )
    )
except ValueError:
    raise RuntimeError(
        "PASSWORD_RECOVERY_COOLDOWN_MINUTES "
        "debe ser un número entero"
    )

if PASSWORD_RECOVERY_COOLDOWN_MINUTES <= 0:
    raise RuntimeError(
        "PASSWORD_RECOVERY_COOLDOWN_MINUTES "
        "debe ser mayor que cero"
    )

# =========================================================
# SEGURIDAD - SECRETO JWT
# =========================================================
# El Identity Service no debe iniciar si el secreto requerido
# para firmar y validar los tokens JWT no está configurado.
# =========================================================

if not JWT_SECRET:
    raise RuntimeError(
        "La variable JWT_SECRET no está configurada"
    )


# =========================================================
# SEGURIDAD - DESAFÍO MFA DE LOGIN
# =========================================================
# El desafío de segundo factor es breve y de un solo uso.
# El valor enviado al cliente nunca se almacena en texto plano:
# PostgreSQL conserva únicamente su SHA-256.
# =========================================================

try:
    MFA_CHALLENGE_EXPIRE_MINUTES = int(
        os.getenv("MFA_CHALLENGE_EXPIRE_MINUTES", "5")
    )
except ValueError:
    raise RuntimeError(
        "MFA_CHALLENGE_EXPIRE_MINUTES debe ser un número entero"
    )

if MFA_CHALLENGE_EXPIRE_MINUTES <= 0:
    raise RuntimeError(
        "MFA_CHALLENGE_EXPIRE_MINUTES debe ser mayor que cero"
    )

# Máximo de intentos incorrectos permitidos para un desafío MFA.
# Al tercer fallo, el desafío se consume y debe iniciarse
# nuevamente el proceso completo de autenticación.
MFA_CHALLENGE_MAX_ATTEMPTS = 3


# =========================================================
# MODELOS PYDANTIC
# =========================================================

class CambioPassword(BaseModel):
    # La contraseña actual es opcional únicamente a nivel
    # del modelo de entrada.
    #
    # SEGURIDAD:
    # El backend decidirá si debe exigirse utilizando el
    # estado real requiere_cambio_password almacenado en
    # PostgreSQL.
    #
    # - Cambio voluntario:
    #     password_actual será obligatorio.
    #
    # - Cambio obligatorio después de autenticarse con una
    #   contraseña temporal:
    #     password_actual no será solicitado nuevamente.
    #
    # El frontend no decide qué modalidad aplica.
    password_actual: str | None = None

    # Contraseña definitiva elegida por el usuario.
    #
    # SEGURIDAD:
    # - mínimo 12 caracteres;
    # - las reglas adicionales se validan nuevamente
    #   mediante la política central del backend.
    #
    # Esta validación de Pydantic constituye una primera
    # barrera, pero la autoridad de seguridad continúa
    # siendo validar_password_seguro().
    # La política completa de la contraseña se valida en
    # validar_password_seguro(), permitiendo devolver al usuario
    # un único mensaje con todos los requisitos de seguridad.
    password_nuevo: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ActivarMFARequest(BaseModel):
    # Código temporal mostrado por la aplicación Authenticator.
    # No se persiste ni se registra en auditoría.
    codigo: str


class VerificarMFALoginRequest(BaseModel):
    # Identificador aleatorio de un solo uso generado después de
    # validar correctamente correo y contraseña.
    #
    # SEGURIDAD:
    # - no es un JWT de acceso;
    # - no concede autorización;
    # - en PostgreSQL solo se almacena su hash SHA-256.
    desafio: str
    codigo: str


class EnrolamientoMFAObligatorioRequest(BaseModel):
    # Desafío temporal emitido únicamente después de validar
    # correctamente el primer factor (correo + contraseña).
    desafio: str


class ActivarMFAObligatorioRequest(BaseModel):
    # El desafío demuestra que el primer factor ya fue validado.
    # El código TOTP confirma la posesión del Authenticator.
    desafio: str
    codigo: str


# =========================================================
# MFA / TOTP - ENROLAMIENTO Y ACTIVACIÓN
# =========================================================
# ETAPA 1:
# - El usuario debe poseer una sesión autenticada válida.
# - El secreto TOTP se genera exclusivamente en backend.
# - PostgreSQL recibe únicamente el secreto cifrado con Fernet.
# - La URI otpauth permanece en memoria y se entrega como QR PNG.
# - MFA solo queda activo después de validar el primer TOTP.
# - No se devuelven secretos TOTP como texto.
# =========================================================

@router.post("/mfa/enrolamiento")
def iniciar_enrolamiento_mfa(
    usuario=Depends(obtener_usuario_desde_token)
):
    usuario_id = usuario["id"]

    # El identificador visible dentro de Authenticator se obtiene
    # del contexto autenticado; no se acepta desde el frontend.
    identificador_usuario = usuario.get("email")

    if not identificador_usuario:
        raise HTTPException(
            status_code=409,
            detail="No fue posible identificar al usuario para MFA"
        )

    consulta_estado = text("""
        SELECT activo
        FROM mfa_totp
        WHERE usuario_id = :usuario_id
        LIMIT 1
    """)

    with engine.connect() as conexion:
        estado = conexion.execute(
            consulta_estado,
            {"usuario_id": usuario_id}
        ).mappings().first()

    # Un MFA ya activo no debe reemplazarse silenciosamente.
    # La rotación/desactivación tendrá un flujo separado.
    if estado is not None and estado["activo"]:
        raise HTTPException(
            status_code=409,
            detail="MFA ya se encuentra activo para este usuario"
        )

    secreto = generar_secreto_totp()
    secreto_cifrado = cifrar_secreto_totp(secreto)

    # Generamos el QR antes de confirmar la persistencia. Si la
    # generación falla, no queda un enrolamiento pendiente inútil.
    qr_png = generar_qr_aprovisionamiento_png(
        secreto=secreto,
        identificador_usuario=str(identificador_usuario),
    )

    guardar_enrolamiento = text("""
        INSERT INTO mfa_totp (
            usuario_id,
            secreto_cifrado,
            activo,
            ultimo_contador_validado,
            fecha_enrolamiento,
            fecha_creacion,
            fecha_modificacion
        )
        VALUES (
            :usuario_id,
            :secreto_cifrado,
            FALSE,
            NULL,
            NULL,
            NOW(),
            NOW()
        )
        ON CONFLICT (usuario_id)
        DO UPDATE SET
            secreto_cifrado = EXCLUDED.secreto_cifrado,
            activo = FALSE,
            ultimo_contador_validado = NULL,
            fecha_enrolamiento = NULL,
            fecha_modificacion = NOW()
        WHERE mfa_totp.activo = FALSE
        RETURNING usuario_id
    """)

    with engine.begin() as conexion:
        guardado = conexion.execute(
            guardar_enrolamiento,
            {
                "usuario_id": usuario_id,
                "secreto_cifrado": secreto_cifrado,
            }
        ).mappings().first()

    if guardado is None:
        raise HTTPException(
            status_code=409,
            detail="MFA ya se encuentra activo para este usuario"
        )

    registrar_evento(
        MFA_ENROLAMIENTO_INICIADO,
        actor_usuario_id=usuario_id,
        objetivo_usuario_id=usuario_id,
        resultado="EXITO",
        detalle={"motivo": "ENROLAMIENTO_TOTP"}
    )

    # La imagen contiene material de enrolamiento sensible.
    # Evitamos caché y no devolvemos URI/secreto en JSON.
    return Response(
        content=qr_png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.post("/mfa/activar")
def activar_mfa(
    datos: ActivarMFARequest,
    usuario=Depends(obtener_usuario_desde_token)
):
    usuario_id = usuario["id"]

    consulta = text("""
        SELECT secreto_cifrado, activo
        FROM mfa_totp
        WHERE usuario_id = :usuario_id
        LIMIT 1
    """)

    with engine.connect() as conexion:
        configuracion = conexion.execute(
            consulta,
            {"usuario_id": usuario_id}
        ).mappings().first()

    if configuracion is None:
        raise HTTPException(
            status_code=409,
            detail="No existe un enrolamiento MFA pendiente"
        )

    if configuracion["activo"]:
        raise HTTPException(
            status_code=409,
            detail="MFA ya se encuentra activo para este usuario"
        )

    secreto = descifrar_secreto_totp(
        configuracion["secreto_cifrado"]
    )

    validacion = validar_codigo_totp(
        secreto=secreto,
        codigo=datos.codigo,
    )

    if not validacion.valido or validacion.contador is None:
        raise HTTPException(
            status_code=401,
            detail="Código de autenticación no válido"
        )

    # La activación y el consumo del primer contador se realizan
    # atómicamente. Esto evita activar dos veces el mismo enrolamiento
    # y deja preparado el control anti-replay para el login posterior.
    activar = text("""
        UPDATE mfa_totp
        SET
            activo = TRUE,
            ultimo_contador_validado = :contador,
            fecha_enrolamiento = NOW(),
            fecha_modificacion = NOW()
        WHERE usuario_id = :usuario_id
          AND activo = FALSE
        RETURNING usuario_id, activo, fecha_enrolamiento
    """)

    with engine.begin() as conexion:
        resultado = conexion.execute(
            activar,
            {
                "usuario_id": usuario_id,
                "contador": validacion.contador,
            }
        ).mappings().first()

    if resultado is None:
        raise HTTPException(
            status_code=409,
            detail="El estado del enrolamiento MFA cambió"
        )

    registrar_evento(
        MFA_ACTIVADO,
        actor_usuario_id=usuario_id,
        objetivo_usuario_id=usuario_id,
        resultado="EXITO",
        detalle={"motivo": "CONFIRMACION_TOTP"}
    )

    return {
        "mensaje": "MFA activado correctamente",
        "mfa_activo": True,
    }


# =========================================================
# RECUPERACIÓN DE CONTRASEÑA
# =========================================================
# Este modelo recibe únicamente el correo electrónico.
#
# SEGURIDAD:
# - el usuario no proporciona una nueva contraseña;
# - la contraseña temporal será generada por el backend;
# - no se devuelve información que permita determinar si
#   el correo está registrado en la plataforma.
# =========================================================

class RecuperarPassword(BaseModel):
    email: EmailStr

# =========================================================
# POLÍTICA CENTRAL DE CONTRASEÑAS
# =========================================================
# Esta validación se realiza en el backend porque las
# validaciones del frontend no constituyen por sí solas
# un control de seguridad.
#
# La contraseña definitiva debe cumplir:
# - mínimo 12 caracteres;
# - al menos un número (0-9);
# - al menos una letra;
# - al menos un carácter especial.
#
# La contraseña recibida no se imprime ni se almacena
# directamente. Posteriormente se protege mediante Argon2.
# =========================================================

def validar_password_seguro(password: str):
    """
    Valida la política central de contraseñas definitivas.

    POLÍTICA DE SEGURIDAD:
    - mínimo 12 caracteres;
    - al menos un número (0-9);
    - al menos una letra;
    - al menos un carácter especial.

    SEGURIDAD:
    La política se valida siempre en el backend.
    El frontend puede presentar estos mismos requisitos
    para mejorar la experiencia del usuario, pero no
    constituye el control de seguridad autoritativo.

    La contraseña nunca se registra ni se almacena
    en texto plano.
    """

    # =====================================================
    # VALIDACIÓN CONSOLIDADA DE CONTRASEÑA
    # =====================================================
    # Evaluamos todos los requisitos antes de responder.
    #
    # Si uno o varios requisitos no se cumplen, devolvemos
    # un único mensaje con la política completa. Esto evita
    # presentar al usuario los requisitos uno por uno.
    # =====================================================

    longitud_valida = len(password) >= 12

    contiene_numero = (
        re.search(r"[0-9]", password) is not None
    )

    contiene_letra = (
        re.search(r"[A-Za-z]", password) is not None
    )

    contiene_especial = (
        re.search(r"[^A-Za-z0-9]", password) is not None
    )

    if not all([
        longitud_valida,
        contiene_numero,
        contiene_letra,
        contiene_especial,
    ]):
        raise HTTPException(
            status_code=400,
            detail=(
                "La contraseña no es segura. "
                "Asegúrate de cumplir con lo siguiente: "
                "Mínimo 12 caracteres. "
                "Al menos un número (0-9). "
                "Incluir al menos una letra (a, b, c...). "
                "Al menos un carácter especial "
                "(!, @, #, $, %, etc.)."
            )
        )

# ============================================================
# GENERACIÓN SEGURA DE CONTRASEÑAS TEMPORALES
# ============================================================
# Las contraseñas temporales se generan automáticamente
# utilizando aleatoriedad criptográficamente segura.
#
# Requisitos:
# - mínimo 12 caracteres;
# - contiene letras;
# - contiene caracteres especiales;
# - no utiliza información personal del usuario;
# - posteriormente solo se almacena su hash Argon2.
# ============================================================

def generar_password_temporal(longitud: int = 16) -> str:
    """
    Genera una contraseña temporal criptográficamente segura.

    La longitud predeterminada es de 16 caracteres, superando
    el mínimo académico establecido de 12 caracteres.
    """

    if longitud < 12:
        raise ValueError(
            "La contraseña temporal debe tener al menos 12 caracteres"
        )

    letras = string.ascii_letters
    especiales = "!@#$%&*_-"
    alfabeto = letras + string.digits + especiales

    # Garantiza como mínimo una letra y un carácter especial.
    caracteres = [
        secrets.choice(letras),
        secrets.choice(especiales),
    ]

    # Completa los caracteres restantes de forma aleatoria.
    caracteres.extend(
        secrets.choice(alfabeto)
        for _ in range(longitud - len(caracteres))
    )

    # Mezcla las posiciones para evitar patrones predecibles.
    secrets.SystemRandom().shuffle(caracteres)

    return "".join(caracteres)


# =========================================================
# AUTORIZACIÓN PARA ADMINISTRAR OTRO USUARIO
# =========================================================
# Esta función centraliza las reglas administrativas del
# nuevo modelo IAM.
#
# MODELO DE AUTORIZACIÓN:
#
# ADMIN_TI
#   -> administra usuarios ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> administra usuarios pertenecientes a una de las
#      compañías activas que tenga asignadas.
#
#   -> NO puede administrar ADMIN_TI.
#
#   -> NO puede administrar otro ADMIN_SOPORTE.
#
# LÍDERES
#   -> no administran otros usuarios.
#
# Centralizar esta regla evita implementar criterios
# diferentes en:
#
# - credenciales;
# - reset de contraseña;
# - activación/desactivación;
# - revocación administrativa de sesiones.
#
# IMPORTANTE:
# La autorización siempre se consulta en PostgreSQL.
# No se confía únicamente en información incluida
# previamente dentro del JWT.
# =========================================================

def validar_administracion_usuario(
    conexion,
    usuario_actual: dict,
    usuario_objetivo_id: int
):
    """
    Valida si el usuario autenticado puede administrar
    al usuario objetivo según el nuevo modelo IAM.

    Reglas principales:

    ADMIN_TI:
        Solo puede administrar usuarios cuyo único rol
        administrativo sea ADMIN_SOPORTE.

    ADMIN_SOPORTE:
        Solo puede administrar usuarios líderes de las
        compañías activas que tenga asignadas.

    Los líderes y cualquier rol legado no tienen permisos
    administrativos sobre otros usuarios.

    Esta función consulta PostgreSQL para utilizar el estado
    actual de roles y compañías como fuente autoritativa.
    """

    # -----------------------------------------------------
    # 1. IMPEDIR AUTOADMINISTRACIÓN
    # -----------------------------------------------------
    # Las operaciones administrativas sobre terceros no deben
    # utilizarse sobre la propia cuenta.
    #
    # El cambio de la contraseña propia dispone de su endpoint
    # específico: PUT /auth/password.
    # -----------------------------------------------------

    if usuario_actual["id"] == usuario_objetivo_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta operación administrativa "
                "no puede realizarse sobre la propia cuenta"
            )
        )

    # -----------------------------------------------------
    # 2. OBTENER USUARIO OBJETIVO Y SUS ROLES ACTIVOS
    # -----------------------------------------------------
    # No confiamos en información enviada por el frontend.
    # Los roles actuales del usuario objetivo se consultan
    # directamente desde PostgreSQL.
    # -----------------------------------------------------

    consulta_objetivo = text("""
        SELECT
            u.id,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo,
            COALESCE(
                ARRAY_AGG(
                    DISTINCT r.nombre
                ) FILTER (
                    WHERE r.id IS NOT NULL
                      AND r.activo = TRUE
                ),
                ARRAY[]::VARCHAR[]
            ) AS roles
        FROM usuarios_plataforma u

        LEFT JOIN usuario_roles_plataforma ur
            ON ur.usuario_id = u.id

        LEFT JOIN roles_plataforma r
            ON r.id = ur.rol_id
           AND r.activo = TRUE

        WHERE u.id = :usuario_objetivo_id

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
            "usuario_objetivo_id":
                usuario_objetivo_id
        }
    ).mappings().first()

    if objetivo is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    # Convertimos los roles a conjuntos para realizar
    # comparaciones estrictas y evitar duplicados.
    roles_actual = set(
        usuario_actual.get("roles", [])
    )

    roles_objetivo = set(
        objetivo["roles"] or []
    )

    # -----------------------------------------------------
    # 3. REGLA ADMIN_TI
    # -----------------------------------------------------
    # ADMIN_TI administra exclusivamente cuentas de
    # ADMIN_SOPORTE.
    #
    # Exigimos que el conjunto sea exactamente:
    #
    # {"ADMIN_SOPORTE"}
    #
    # Esto impide administrar accidentalmente una cuenta que
    # combine ADMIN_SOPORTE con un rol legado o incompatible.
    # -----------------------------------------------------

    if "ADMIN_TI" in roles_actual:

        if roles_objetivo != {"ADMIN_SOPORTE"}:
            raise HTTPException(
                status_code=403,
                detail=(
                    "ADMIN_TI solo puede administrar "
                    "usuarios ADMIN_SOPORTE"
                )
            )

        return objetivo

    # -----------------------------------------------------
    # 4. REGLA ADMIN_SOPORTE
    # -----------------------------------------------------
    # ADMIN_SOPORTE solamente puede administrar los tres
    # tipos de líderes definidos en el alcance académico.
    #
    # Los roles antiguos ADMIN, ANALYST y VIEWER quedan
    # explícitamente fuera de esta autorización.
    # -----------------------------------------------------

    if "ADMIN_SOPORTE" in roles_actual:

        roles_lider_permitidos = {
            "LIDER_FACTURACION",
            "LIDER_LOGISTICA",
            "LIDER_GESTION_HUMANA"
        }

        # El usuario objetivo debe tener al menos un rol y
        # TODOS sus roles deben pertenecer al conjunto de
        # líderes permitido.
        #
        # Así rechazamos:
        # - ADMIN_TI;
        # - ADMIN_SOPORTE;
        # - ADMIN;
        # - ANALYST;
        # - VIEWER;
        # - cualquier rol futuro no autorizado;
        # - combinaciones de líder + rol administrativo.
        if (
            not roles_objetivo
            or not roles_objetivo.issubset(
                roles_lider_permitidos
            )
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "ADMIN_SOPORTE solo puede administrar "
                    "usuarios líderes de sus compañías"
                )
            )

        # -------------------------------------------------
        # 5. VALIDAR COMPAÑÍA ASIGNADA
        # -------------------------------------------------
        # Debe existir al menos una compañía que:
        #
        # - esté activa;
        # - esté asignada al ADMIN_SOPORTE;
        # - esté asignada al usuario objetivo.
        #
        # Esta consulta funciona aunque el ADMIN_SOPORTE
        # tenga asignada 1, 2 o las 3 compañías.
        # -------------------------------------------------

        consulta_compania_autorizada = text("""
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

            WHERE soporte_compania.usuario_id =
                  :usuario_actual_id

              AND objetivo_compania.usuario_id =
                  :usuario_objetivo_id

            LIMIT 1
        """)

        compania_autorizada = conexion.execute(
            consulta_compania_autorizada,
            {
                "usuario_actual_id":
                    usuario_actual["id"],

                "usuario_objetivo_id":
                    usuario_objetivo_id
            }
        ).mappings().first()

        if compania_autorizada is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "El usuario objetivo no pertenece "
                    "a una compañía activa asignada "
                    "al ADMIN_SOPORTE"
                )
            )

        return objetivo

    # -----------------------------------------------------
    # 6. CUALQUIER OTRO ROL
    # -----------------------------------------------------
    # Los líderes y los roles heredados no poseen permisos
    # administrativos sobre otros usuarios.
    # -----------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail=(
            "El usuario autenticado no tiene permisos "
            "para administrar otros usuarios"
        )
    )



# =========================================================
# CAMBIO DE CONTRASEÑA
# Usuario autenticado
#
# Este endpoint permite que cualquier usuario autenticado
# cambie su propia contraseña.
#
# También se utiliza durante el primer inicio de sesión
# cuando requiere_cambio_password = TRUE.
# =========================================================

@router.put("/password")
def cambiar_password(
    datos: CambioPassword,
    usuario=Depends(
        obtener_usuario_desde_token
    )
):
    # -----------------------------------------------------
    # 1. OBTENER LA CREDENCIAL ACTIVA DEL USUARIO
    # -----------------------------------------------------
    # Recuperamos únicamente el hash necesario para verificar
    # la contraseña actual.
    #
    # La contraseña en texto plano nunca se almacena.
    # -----------------------------------------------------

    consulta = text("""
        SELECT
            password_hash,
            requiere_cambio_password
        FROM credenciales
        WHERE usuario_id = :usuario_id
          AND activo = TRUE
    """)

    with engine.connect() as conexion:
        credencial = conexion.execute(
            consulta,
            {
                "usuario_id": usuario["id"]
            }
        ).mappings().first()

    if credencial is None:
        raise HTTPException(
            status_code=404,
            detail="Credencial activa no encontrada"
        )

    # -----------------------------------------------------
    # 2. DETERMINAR EL TIPO DE CAMBIO DE CONTRASEÑA
    # -----------------------------------------------------
    # El backend utiliza exclusivamente el estado almacenado
    # en PostgreSQL para decidir el flujo aplicable.
    #
    # requiere_cambio_password = TRUE:
    #   El usuario ya se autenticó con la contraseña temporal
    #   y dispone únicamente de una sesión restringida.
    #   No se solicita nuevamente la contraseña temporal.
    #
    # requiere_cambio_password = FALSE:
    #   Es un cambio voluntario de contraseña y se exige
    #   verificar la contraseña actual.
    #
    # El frontend no puede elegir ni alterar esta modalidad.
    # -----------------------------------------------------

    cambio_obligatorio = bool(
        credencial["requiere_cambio_password"]
    )

    if not cambio_obligatorio:

        # -------------------------------------------------
        # CAMBIO VOLUNTARIO
        # -------------------------------------------------
        # Para un cambio iniciado desde "Mi perfil" sigue
        # siendo obligatorio demostrar conocimiento de la
        # contraseña actual.
        # -------------------------------------------------

        if not datos.password_actual:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La contraseña actual es obligatoria "
                    "para realizar un cambio voluntario"
                )
            )

        password_actual_valida = password_hasher.verify(
            datos.password_actual,
            credencial["password_hash"]
        )

        if not password_actual_valida:
            raise HTTPException(
                status_code=401,
                detail="La contraseña actual no es válida"
            )

        # No permitimos reutilizar inmediatamente la misma
        # contraseña durante un cambio voluntario.
        if datos.password_actual == datos.password_nuevo:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La nueva contraseña "
                    "debe ser diferente"
                )
            )

    else:

        # -------------------------------------------------
        # CAMBIO OBLIGATORIO
        # -------------------------------------------------
        # La contraseña temporal ya fue validada durante el
        # login que creó esta sesión restringida.
        #
        # Por ello no se solicita nuevamente al usuario.
        # Sin embargo, verificamos que la nueva contraseña
        # definitiva no sea igual a la contraseña temporal.
        # -------------------------------------------------

        if password_hasher.verify(
            datos.password_nuevo,
            credencial["password_hash"]
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "La nueva contraseña debe ser diferente "
                    "de la contraseña temporal"
                )
            )
    # -----------------------------------------------------
    # 4. VALIDAR LA NUEVA CONTRASEÑA
    # -----------------------------------------------------
    # Aplicamos la política central definida anteriormente:
    #
    # - mínimo 12 caracteres;
    # - al menos un número (0-9);
    # - al menos una letra;
    # - al menos un carácter especial.
    #
    # Esta validación ocurre en el backend y, por tanto,
    # no depende de las validaciones del frontend.
    # -----------------------------------------------------

    validar_password_seguro(
        datos.password_nuevo
    )

    # -----------------------------------------------------
    # 5. GENERAR EL NUEVO HASH ARGON2
    # -----------------------------------------------------
    # Solo el hash será almacenado en PostgreSQL.
    # -----------------------------------------------------

    nuevo_hash = password_hasher.hash(
        datos.password_nuevo
    )

    # -----------------------------------------------------
    # 6. CALCULAR EXPIRACIÓN DE LA CONTRASEÑA DEFINITIVA
    # -----------------------------------------------------
    # La contraseña elegida por el usuario deja de ser
    # temporal y recibe una vigencia propia. El período se
    # controla mediante PASSWORD_EXPIRE_DAYS (60 días por
    # defecto) y la fecha se calcula en UTC.
    # -----------------------------------------------------

    password_expira_en = (
        datetime.now(timezone.utc)
        + timedelta(days=PASSWORD_EXPIRE_DAYS)
    )

    # -----------------------------------------------------
    # 7. ACTUALIZAR CREDENCIAL
    # -----------------------------------------------------
    # El cambio se realiza de forma atómica:
    # - guarda únicamente el nuevo hash Argon2;
    # - elimina la expiración de la contraseña temporal;
    # - registra la expiración de la contraseña definitiva;
    # - elimina la obligación de cambio de contraseña.
    # -----------------------------------------------------

    consulta_actualizar = text("""
        UPDATE credenciales
        SET
            password_hash = :password_hash,
            requiere_cambio_password = FALSE,
            password_temporal_expira_en = NULL,
            password_expira_en = :password_expira_en,
            fecha_modificacion = NOW()
        WHERE usuario_id = :usuario_id
          AND activo = TRUE
        RETURNING
            id,
            usuario_id,
            activo,
            requiere_cambio_password,
            password_expira_en,
            fecha_modificacion
    """)

    with engine.begin() as conexion:
        resultado = conexion.execute(
            consulta_actualizar,
            {
                "usuario_id": usuario["id"],
                "password_hash": nuevo_hash,
                "password_expira_en": password_expira_en
            }
        ).mappings().first()

        if resultado is not None:
            # Un cambio de contraseña invalida cualquier desafío MFA
            # pendiente emitido antes del cambio de credencial.
            conexion.execute(
                text("""
                    UPDATE mfa_desafios
                    SET
                        usado = TRUE,
                        usado_en = NOW()
                    WHERE usuario_id = :usuario_id
                      AND usado = FALSE
                """),
                {"usuario_id": usuario["id"]}
            )

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Credencial activa no encontrada"
        )

    # -----------------------------------------------------
    # 8. RESPUESTA SEGURA
    # -----------------------------------------------------
    # Nunca devolvemos password_hash ni las contraseñas.
    # -----------------------------------------------------

    return {
        "mensaje":
            "Contraseña actualizada correctamente",

        "requiere_cambio_password":
            resultado["requiere_cambio_password"]
    }

# =========================================================
# RESET ADMINISTRATIVO DE CONTRASEÑA
# =========================================================
# Permite establecer una contraseña temporal para otro
# usuario de acuerdo con el modelo administrativo IAM.
#
# AUTORIZACIÓN:
#
# ADMIN_TI
#   -> puede administrar usuarios ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> puede administrar usuarios pertenecientes a las
#      compañías activas que tenga asignadas.
#
#   -> no puede administrar ADMIN_TI.
#   -> no puede administrar otros ADMIN_SOPORTE.
#
# LÍDERES
#   -> no pueden administrar otros usuarios.
#
# SEGURIDAD:
# - contraseña temporal de mínimo 12 caracteres;
# - debe contener letra y carácter especial;
# - almacenamiento únicamente mediante hash Argon2;
# - requiere_cambio_password = TRUE;
# - revocación de sesiones anteriores;
# - no se devuelve contraseña, hash, JWT ni JTI.
# =========================================================

@router.put(
    "/credenciales/{usuario_id}/reset-password"
)
def reset_password_admin(
    usuario_id: int,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):

    """
    Genera y envía una nueva contraseña temporal para un
    usuario administrado.

    SEGURIDAD:
    - la contraseña temporal es generada por el backend;
    - utiliza aleatoriedad criptográficamente segura;
    - no es suministrada por el administrador;
    - solo se almacena su hash Argon2;
    - obliga al cambio de contraseña en el siguiente acceso;
    - revoca las sesiones anteriores;
    - la contraseña temporal se envía al correo registrado;
    - nunca se devuelve en la respuesta de la API.
    """

    # -----------------------------------------------------
    # 1. VALIDAR AUTORIZACIÓN Y OBTENER USUARIO OBJETIVO
    # -----------------------------------------------------
    # La autorización se determina con información actual
    # obtenida directamente de PostgreSQL.
    #
    # También obtenemos nombre y correo del usuario objetivo.
    # No confiamos en esos datos enviados desde el frontend.
    # -----------------------------------------------------

    with engine.connect() as conexion:

        objetivo = validar_administracion_usuario(
            conexion=conexion,
            usuario_actual=usuario_actual,
            usuario_objetivo_id=usuario_id
        )

    # -----------------------------------------------------
    # 2. VALIDAR ESTADO DEL USUARIO OBJETIVO
    # -----------------------------------------------------
    # No generamos nuevas credenciales para una identidad
    # deshabilitada.
    # -----------------------------------------------------

    if not objetivo["activo"]:
        raise HTTPException(
            status_code=400,
            detail="El usuario se encuentra inactivo"
        )

    # -----------------------------------------------------
    # 3. GENERAR CONTRASEÑA TEMPORAL
    # -----------------------------------------------------
    # El valor existe únicamente de forma transitoria en
    # memoria durante esta operación.
    #
    # generar_password_temporal() utiliza secrets y genera
    # actualmente 16 caracteres.
    # -----------------------------------------------------

    password_temporal = generar_password_temporal()

    # -----------------------------------------------------
    # EXPIRACIÓN DE LA CONTRASEÑA TEMPORAL
    # -----------------------------------------------------
    # Se calcula en UTC y se almacena en PostgreSQL como
    # TIMESTAMPTZ. La vigencia se controla mediante una
    # variable de entorno configurable.
    # -----------------------------------------------------

    password_temporal_expira_en = (
        datetime.now(timezone.utc)
        + timedelta(hours=TEMP_PASSWORD_EXPIRE_HOURS)
    )

    # -----------------------------------------------------
    # 4. GENERAR HASH ARGON2
    # -----------------------------------------------------
    # PostgreSQL nunca recibe la contraseña en texto plano.
    # Solamente se almacena el hash Argon2.
    # -----------------------------------------------------

    nuevo_hash = password_hasher.hash(
        password_temporal
    )

    # -----------------------------------------------------
    # 5. CONSULTA PARA ACTUALIZAR CREDENCIAL
    # -----------------------------------------------------
    # requiere_cambio_password = TRUE obliga al usuario a
    # establecer posteriormente una contraseña definitiva.
    # -----------------------------------------------------

    consulta_actualizar_credencial = text("""
    UPDATE credenciales
    SET
        password_hash = :password_hash,
        requiere_cambio_password = TRUE,
        password_temporal_expira_en = :password_temporal_expira_en,
        password_expira_en = NULL,

        -- =================================================
        -- RESTABLECER ESTADO DE BLOQUEO
        -- =================================================
        -- Al generar una nueva contraseña temporal también
        -- se elimina cualquier bloqueo producido por
        -- intentos fallidos anteriores.
        --
        -- Esto permite que el usuario pueda autenticarse
        -- utilizando la nueva contraseña temporal recibida.
        -- =================================================
        intentos_fallidos = 0,
        bloqueado = FALSE,
        bloqueado_en = NULL,

        fecha_modificacion = NOW()
    WHERE usuario_id = :usuario_id
      AND activo = TRUE
    RETURNING
        id,
        usuario_id,
        activo,
        requiere_cambio_password,
        password_temporal_expira_en,
        fecha_modificacion
""")

    # -----------------------------------------------------
    # 6. REVOCAR SESIONES ACTIVAS
    # -----------------------------------------------------
    # Una contraseña restablecida invalida las sesiones
    # anteriores del usuario.
    # -----------------------------------------------------

    consulta_revocar_sesiones = text("""
        UPDATE sesiones
        SET
            revocada = TRUE,
            fecha_revocacion = NOW()
        WHERE usuario_id = :usuario_id
          AND revocada = FALSE
          AND fecha_expiracion > NOW()
        RETURNING id
    """)

    # Todo desafío MFA emitido antes del restablecimiento deja de ser
    # confiable porque pertenece al estado anterior de la credencial.
    consulta_invalidar_desafios_mfa = text("""
        UPDATE mfa_desafios
        SET
            usado = TRUE,
            usado_en = NOW()
        WHERE usuario_id = :usuario_id
          AND usado = FALSE
    """)

    # -----------------------------------------------------
    # 7. TRANSACCIÓN DE BASE DE DATOS + ENVÍO
    # -----------------------------------------------------
    # Primero modificamos la credencial dentro de una
    # transacción todavía no confirmada.
    #
    # Después intentamos enviar el correo.
    #
    # Si SMTP genera una excepción, esta sale del bloque
    # engine.begin() y SQLAlchemy realiza rollback.
    #
    # Así evitamos, en el caso normal de fallo SMTP, dejar al
    # usuario con una contraseña nueva que nunca recibió.
    # -----------------------------------------------------

    try:

        with engine.begin() as conexion:

            credencial = conexion.execute(
                consulta_actualizar_credencial,
                {
                    "usuario_id":
                        usuario_id,

                    "password_hash":
                        nuevo_hash,

                    "password_temporal_expira_en":
                        password_temporal_expira_en
                }
            ).mappings().first()

            if credencial is None:
                raise HTTPException(
                    status_code=404,
                    detail="Credencial activa no encontrada"
                )

            resultado_sesiones = conexion.execute(
                consulta_revocar_sesiones,
                {
                    "usuario_id":
                        usuario_id
                }
            )

            sesiones_revocadas = (
                resultado_sesiones.fetchall()
            )

            conexion.execute(
                consulta_invalidar_desafios_mfa,
                {"usuario_id": usuario_id}
            )

            # -------------------------------------------------
            # 8. ENVIAR CONTRASEÑA TEMPORAL
            # -------------------------------------------------
            # La contraseña solamente se utiliza aquí para
            # construir el mensaje de correo.
            #
            # No se imprime y no se incluye en la respuesta.
            # -------------------------------------------------

            enviar_password_temporal(
                destinatario=objetivo["email"],
                nombre_usuario=objetivo["nombre"],
                password_temporal=password_temporal
            )

    except HTTPException:
        # Conservamos los códigos HTTP controlados generados
        # por nuestra propia lógica.
        raise

    except Exception:
        # -------------------------------------------------
        # RESPUESTA SEGURA ANTE ERROR SMTP/INFRAESTRUCTURA
        # -------------------------------------------------
        # No exponemos:
        # - contraseña temporal;
        # - credenciales SMTP;
        # - detalles internos del servidor.
        # -------------------------------------------------

        raise HTTPException(
            status_code=503,
            detail=(
                "No fue posible completar el restablecimiento "
                "de la contraseña temporal"
            )
        )

    # -----------------------------------------------------
    # 9. RESPUESTA SEGURA
    # -----------------------------------------------------
    # Deliberadamente no devolvemos:
    # - contraseña temporal;
    # - password_hash;
    # - JWT;
    # - JTI;
    # - credenciales SMTP.
    # -----------------------------------------------------

    return {
        "mensaje":
            "Contraseña temporal generada y enviada correctamente",

        "usuario_id":
            usuario_id,

        "requiere_cambio_password":
            credencial["requiere_cambio_password"],

        "sesiones_revocadas":
            len(sesiones_revocadas)
    }


# =========================================================
# RECUPERACIÓN DE CONTRASEÑA POR CORREO
# =========================================================
# Endpoint público para iniciar una recuperación sin sesión.
#
# SEGURIDAD:
# - usa una respuesta genérica para reducir enumeración;
# - genera la contraseña temporal exclusivamente en backend;
# - almacena únicamente su hash Argon2;
# - aplica cooldown persistente por cuenta;
# - valida el cooldown de forma atómica durante el UPDATE;
# - revoca sesiones activas anteriores;
# - obliga a cambiar la contraseña temporal;
# - no devuelve contraseña, hash, JWT, JTI ni correo.
# =========================================================

@router.post("/recuperar-password")
def recuperar_password(
    datos: RecuperarPassword
):
    """
    Inicia el proceso de recuperación de contraseña.

    La respuesta pública no confirma si el correo pertenece
    o no a una cuenta registrada.
    """

    respuesta_generica = {
        "mensaje": (
            "Si el correo corresponde a una cuenta válida, "
            "se enviaron las instrucciones de recuperación."
        )
    }

    # -----------------------------------------------------
    # 1. BUSCAR USUARIO Y CREDENCIAL ACTIVA
    # -----------------------------------------------------
    consulta_usuario = text("""
        SELECT
            u.id AS usuario_id,
            u.nombre,
            u.email,
            u.activo AS usuario_activo,
            c.id AS credencial_id,
            c.activo AS credencial_activa,
            c.ultima_recuperacion_password_en
        FROM usuarios_plataforma u
        JOIN credenciales c
            ON c.usuario_id = u.id
        WHERE LOWER(u.email) = LOWER(:email)
          AND c.activo = TRUE
        LIMIT 1
    """)

    try:
        with engine.connect() as conexion:
            usuario = conexion.execute(
                consulta_usuario,
                {"email": str(datos.email)}
            ).mappings().first()
    except Exception:
        return respuesta_generica

    if (
        usuario is None
        or not usuario["usuario_activo"]
        or not usuario["credencial_activa"]
    ):
        return respuesta_generica

    usuario_id = usuario["usuario_id"]

    # -----------------------------------------------------
    # 2. COMPROBACIÓN PREVIA DEL COOLDOWN
    # -----------------------------------------------------
    # Evita generar un nuevo hash y enviar otro correo cuando
    # la recuperación anterior todavía está dentro del período
    # configurado. El UPDATE vuelve a validar la condición para
    # proteger también frente a solicitudes concurrentes.
    ultima_recuperacion = usuario[
        "ultima_recuperacion_password_en"
    ]

    if ultima_recuperacion is not None:
        limite_recuperacion = (
            datetime.now(timezone.utc)
            - timedelta(
                minutes=PASSWORD_RECOVERY_COOLDOWN_MINUTES
            )
        )

        if ultima_recuperacion > limite_recuperacion:
            return respuesta_generica

    # -----------------------------------------------------
    # 3. GENERAR CONTRASEÑA TEMPORAL Y EXPIRACIÓN
    # -----------------------------------------------------
    password_temporal = generar_password_temporal()

    password_temporal_expira_en = (
        datetime.now(timezone.utc)
        + timedelta(hours=TEMP_PASSWORD_EXPIRE_HOURS)
    )

    # PostgreSQL recibe únicamente el hash Argon2.
    nuevo_hash = password_hasher.hash(password_temporal)

    # -----------------------------------------------------
    # 4. ACTUALIZACIÓN ATÓMICA CON COOLDOWN
    # -----------------------------------------------------
    # Si dos solicitudes llegan simultáneamente, solo una
    # puede satisfacer la condición y completar el UPDATE.
    consulta_actualizar_credencial = text("""
        UPDATE credenciales
        SET
            password_hash = :password_hash,
            requiere_cambio_password = TRUE,
            password_temporal_expira_en =
                :password_temporal_expira_en,
            password_expira_en = NULL,
            intentos_fallidos = 0,
            bloqueado = FALSE,
            bloqueado_en = NULL,
            ultima_recuperacion_password_en = NOW(),
            fecha_modificacion = NOW()
        WHERE usuario_id = :usuario_id
          AND activo = TRUE
          AND (
              ultima_recuperacion_password_en IS NULL
              OR ultima_recuperacion_password_en <=
                  NOW() - (
                      :cooldown_minutes
                      * INTERVAL '1 minute'
                  )
          )
        RETURNING
            id,
            usuario_id,
            requiere_cambio_password,
            password_temporal_expira_en,
            ultima_recuperacion_password_en
    """)

    consulta_revocar_sesiones = text("""
        UPDATE sesiones
        SET
            revocada = TRUE,
            fecha_revocacion = NOW()
        WHERE usuario_id = :usuario_id
          AND revocada = FALSE
          AND fecha_expiracion > NOW()
        RETURNING id
    """)

    # Todo desafío MFA emitido antes del restablecimiento deja de ser
    # confiable porque pertenece al estado anterior de la credencial.
    consulta_invalidar_desafios_mfa = text("""
        UPDATE mfa_desafios
        SET
            usado = TRUE,
            usado_en = NOW()
        WHERE usuario_id = :usuario_id
          AND usado = FALSE
    """)

    # -----------------------------------------------------
    # 5. TRANSACCIÓN + ENVÍO DE CORREO
    # -----------------------------------------------------
    # Si SMTP falla, la excepción provoca rollback. No queda
    # activa una contraseña temporal que el usuario no recibió
    # y tampoco se consume el cooldown.
    try:
        with engine.begin() as conexion:
            credencial = conexion.execute(
                consulta_actualizar_credencial,
                {
                    "usuario_id": usuario_id,
                    "password_hash": nuevo_hash,
                    "password_temporal_expira_en":
                        password_temporal_expira_en,
                    "cooldown_minutes":
                        PASSWORD_RECOVERY_COOLDOWN_MINUTES,
                }
            ).mappings().first()

            # Otra solicitud concurrente pudo activar el cooldown.
            if credencial is None:
                return respuesta_generica

            resultado_sesiones = conexion.execute(
                consulta_revocar_sesiones,
                {"usuario_id": usuario_id}
            )

            sesiones_revocadas = resultado_sesiones.fetchall()

            conexion.execute(
                consulta_invalidar_desafios_mfa,
                {"usuario_id": usuario_id}
            )

            enviar_password_temporal(
                destinatario=usuario["email"],
                nombre_usuario=usuario["nombre"],
                password_temporal=password_temporal
            )

    except Exception:
        # No exponemos detalles de SMTP, PostgreSQL ni datos que
        # permitan inferir si la cuenta existe.
        return respuesta_generica

    # -----------------------------------------------------
    # 6. AUDITORÍA DESPUÉS DEL COMMIT
    # -----------------------------------------------------
    # No se registra correo, contraseña, hash, JWT ni JTI.
    registrar_evento(
        PASSWORD_RECUPERADA,
        objetivo_usuario_id=usuario_id,
        resultado="EXITO",
        detalle={
            "motivo": "RECUPERACION_PASSWORD",
            "sesiones_revocadas": len(sesiones_revocadas),
        }
    )

    return respuesta_generica


# =========================================================
# EMISIÓN CENTRALIZADA DE SESIÓN / JWT DEFINITIVO
# =========================================================
# Esta función se utiliza:
# - directamente después de contraseña cuando MFA no está activo;
# - únicamente después de validar TOTP cuando MFA está activo.
#
# Nunca debe llamarse antes de completar todos los factores exigidos.
# =========================================================

def _emitir_sesion_y_token(
    registro: dict,
    roles: list[str],
    requiere_cambio_password: bool,
):
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(minutes=JWT_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())

    consulta_sesion = text("""
        INSERT INTO sesiones (
            usuario_id,
            jti,
            fecha_inicio,
            fecha_expiracion,
            revocada
        )
        VALUES (
            :usuario_id,
            :jti,
            :fecha_inicio,
            :fecha_expiracion,
            FALSE
        )
        RETURNING
            id,
            usuario_id,
            fecha_inicio,
            fecha_expiracion,
            revocada
    """)

    with engine.begin() as conexion:
        sesion = conexion.execute(
            consulta_sesion,
            {
                "usuario_id": registro["usuario_id"],
                "jti": jti,
                "fecha_inicio": ahora,
                "fecha_expiracion": expira,
            }
        ).mappings().one()

    payload = {
        "sub": str(registro["usuario_id"]),
        "email": registro["email"],
        "roles": roles,
        "jti": jti,
        "iat": ahora,
        "exp": expira,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

    registrar_evento(
        LOGIN_EXITOSO,
        actor_usuario_id=registro["usuario_id"],
        resultado="EXITO",
        detalle={
            "session_id": sesion["id"],
            "requiere_cambio_password": requiere_cambio_password,
            "roles": roles,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRE_MINUTES * 60,
        "session_id": sesion["id"],
        "usuario": {
            "id": registro["usuario_id"],
            "id_externo": registro["id_externo"],
            "nombre": registro["nombre"],
            "email": registro["email"],
            "roles": roles,
            "requiere_cambio_password": requiere_cambio_password,
        }
    }


# =========================================================
# LOGIN
# =========================================================
# Este endpoint autentica al usuario mediante:
#
# 1. Correo electrónico.
# 2. Contraseña.
# 3. Estado activo del usuario.
# 4. Estado activo de la credencial.
#
# Después de autenticar:
# - consulta los roles actuales desde PostgreSQL;
# - crea una sesión persistente;
# - genera un JWT con JTI;
# - informa si el usuario debe cambiar su contraseña.
#
# IMPORTANTE:
# El JWT no almacena contraseñas ni hashes.
# =========================================================

@router.post("/login")
def login(
    datos: LoginRequest
):
    # -----------------------------------------------------
    # 1. BUSCAR USUARIO Y CREDENCIAL
    # -----------------------------------------------------
    # password_hash se utiliza exclusivamente dentro del
    # backend para verificar la contraseña recibida.
    #
    # requiere_cambio_password permite determinar si el
    # usuario está utilizando una contraseña temporal.
    # -----------------------------------------------------

    consulta = text("""
        SELECT
            u.id AS usuario_id,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo AS usuario_activo,
            c.password_hash,
            c.activo AS credencial_activa,
            c.requiere_cambio_password,
            c.intentos_fallidos,
            c.bloqueado,
            c.bloqueado_en,
            c.password_temporal_expira_en,
            c.password_expira_en
        FROM usuarios_plataforma u
        JOIN credenciales c
            ON c.usuario_id = u.id
        WHERE LOWER(u.email) = LOWER(:email)
    """)

    with engine.connect() as conexion:
        registro = conexion.execute(
            consulta,
            {
                "email": datos.email
            }
        ).mappings().first()

    # -----------------------------------------------------
    # 2. EVITAR REVELAR SI EL CORREO EXISTE
    # -----------------------------------------------------
    # Se utiliza el mismo mensaje genérico que para una
    # contraseña incorrecta.
    #
    # De esta forma la API no confirma directamente si una
    # dirección de correo está registrada.
    # -----------------------------------------------------

    if registro is None:
        # Auditoría segura:
        # no registramos el correo introducido porque podría ser un dato
        # arbitrario controlado por un atacante y tampoco inventamos un
        # usuario_id para una cuenta que no existe.
        registrar_evento(
            LOGIN_FALLIDO,
            resultado="FALLO",
            detalle={
                "motivo": "CREDENCIALES_INVALIDAS"
            }
        )

        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    # -----------------------------------------------------
    # 3. VERIFICAR ESTADO DEL USUARIO
    # -----------------------------------------------------

    if not registro["usuario_activo"]:
        registrar_evento(
            LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "ESTADO_NO_PERMITE_LOGIN"
            }
        )

        raise HTTPException(
            status_code=403,
            detail="Usuario inactivo"
        )

    # -----------------------------------------------------
    # 4. VERIFICAR ESTADO DE LA CREDENCIAL
    # -----------------------------------------------------

    if not registro["credencial_activa"]:
        registrar_evento(
            LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "ESTADO_NO_PERMITE_LOGIN"
            }
        )

        raise HTTPException(
            status_code=403,
            detail="Credencial inactiva"
        )

    # -----------------------------------------------------
    # 5. VERIFICAR BLOQUEO DE SEGURIDAD
    # -----------------------------------------------------
    # "bloqueado" representa un bloqueo provocado por
    # múltiples intentos fallidos de autenticación.
    #
    # No debe confundirse con:
    #
    # activo = FALSE
    #
    # que representa una desactivación administrativa.
    #
    # Una credencial bloqueada no puede generar una nueva
    # sesión ni un JWT, incluso si posteriormente se presenta
    # la contraseña correcta.
    # -----------------------------------------------------

    if registro["bloqueado"]:
        # La cuenta ya alcanzó el límite de intentos fallidos.
        # No se verifica la contraseña ni se genera una sesión.
        registrar_evento(
            LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "CUENTA_BLOQUEADA"
            }
        )

        raise HTTPException(
            status_code=423,
            detail=(
                "Usuario bloqueado por máximo de intentos. "
                "Contacte al administrador para restablecer el acceso."
            )
        )

    # -----------------------------------------------------
    # 6. VERIFICAR CONTRASEÑA CON ARGON2
    # -----------------------------------------------------
    # La contraseña recibida se compara únicamente contra
    # el hash Argon2 almacenado.
    #
    # La contraseña en texto plano nunca se almacena en la
    # base de datos.
    # -----------------------------------------------------

    password_valida = password_hasher.verify(
        datos.password,
        registro["password_hash"]
    )

    # -----------------------------------------------------
    # 7. REGISTRAR INTENTO FALLIDO
    # -----------------------------------------------------
    # Si la contraseña es incorrecta:
    #
    # intento 1 -> intentos_fallidos = 1
    # intento 2 -> intentos_fallidos = 2
    # intento 3 -> intentos_fallidos = 3
    #              bloqueado = TRUE
    #              bloqueado_en = NOW()
    #
    # La actualización se realiza dentro de engine.begin()
    # para garantizar que PostgreSQL confirme la transacción
    # antes de devolver el error HTTP.
    # -----------------------------------------------------

    if not password_valida:

        # =====================================================
        # INCREMENTO ATÓMICO DE INTENTOS FALLIDOS
        # =====================================================
        # El contador se incrementa directamente en PostgreSQL.
        #
        # No calculamos:
        #
        #     intentos_fallidos + 1
        #
        # previamente en Python, porque dos solicitudes
        # simultáneas podrían leer el mismo valor y provocar
        # una condición de carrera.
        #
        # PostgreSQL realiza el incremento sobre la propia fila
        # y RETURNING nos entrega el estado resultante.
        # =====================================================

        actualizar_intentos = text("""
            UPDATE credenciales
            SET
                intentos_fallidos = intentos_fallidos + 1,

                bloqueado =
                    (intentos_fallidos + 1 >= 3),

                bloqueado_en =
                    CASE
                        WHEN intentos_fallidos + 1 >= 3
                             AND bloqueado_en IS NULL
                        THEN NOW()
                        ELSE bloqueado_en
                    END,

                fecha_modificacion = NOW()

            WHERE usuario_id = :usuario_id

            RETURNING
                intentos_fallidos,
                bloqueado
        """)

        with engine.begin() as conexion:

            estado_seguridad = conexion.execute(
                actualizar_intentos,
                {
                    "usuario_id":
                        registro["usuario_id"]
                }
            ).mappings().first()

            # =================================================
            # REVOCACIÓN DE SESIONES AL BLOQUEAR LA CUENTA
            # =================================================
            # Si este intento alcanza el límite permitido,
            # todas las sesiones activas del usuario se revocan
            # dentro de la misma transacción.
            #
            # De esta forma, un JWT emitido previamente no puede
            # seguir utilizándose después del bloqueo.
            # =================================================

            if (
                estado_seguridad
                and estado_seguridad["bloqueado"]
            ):
                revocar_sesiones = text("""
                    UPDATE sesiones
                    SET
                        revocada = TRUE,
                        fecha_revocacion = NOW()
                    WHERE usuario_id = :usuario_id
                      AND revocada = FALSE
                      AND fecha_expiracion > NOW()
                """)

                conexion.execute(
                    revocar_sesiones,
                    {
                        "usuario_id":
                            registro["usuario_id"]
                    }
                )

                # Un desafío MFA emitido antes del bloqueo no debe
                # poder completarse ni recuperar validez tras un
                # desbloqueo posterior.
                conexion.execute(
                    text("""
                        UPDATE mfa_desafios
                        SET
                            usado = TRUE,
                            usado_en = NOW()
                        WHERE usuario_id = :usuario_id
                          AND usado = FALSE
                    """),
                    {"usuario_id": registro["usuario_id"]}
                )


        # La transacción anterior ya terminó correctamente.
        # Registramos auditoría después del COMMIT para que el evento
        # describa el estado que realmente quedó persistido.
        intentos_actuales = (
            estado_seguridad["intentos_fallidos"]
            if estado_seguridad is not None
            else None
        )

        registrar_evento(
            LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "CREDENCIALES_INVALIDAS",
                "intentos_fallidos": intentos_actuales
            }
        )

        # Como una cuenta previamente bloqueada se rechaza antes de llegar
        # a este bloque, este evento corresponde al intento que provoca
        # el bloqueo dentro del flujo normal.
        if (
            estado_seguridad is not None
            and estado_seguridad["bloqueado"]
        ):
            registrar_evento(
                CUENTA_BLOQUEADA,
                actor_usuario_id=registro["usuario_id"],
                objetivo_usuario_id=registro["usuario_id"],
                resultado="EXITO",
                detalle={
                    "motivo": "LIMITE_INTENTOS_FALLIDOS",
                    "intentos_fallidos": intentos_actuales
                }
            )

        if (
            estado_seguridad is not None
            and estado_seguridad["bloqueado"]
        ):
            raise HTTPException(
                status_code=423,
                detail=(
                    "Usuario bloqueado por máximo de intentos. "
                    "Contacte al administrador para restablecer el acceso."
                )
            )

        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    # -----------------------------------------------------
    # 8. VALIDAR EXPIRACIÓN DE CONTRASEÑA TEMPORAL
    # -----------------------------------------------------
    # Solo se aplica cuando la credencial exige cambio.
    # Las credenciales antiguas con fecha NULL se mantienen
    # compatibles hasta que sean restablecidas nuevamente.
    # Una contraseña correcta pero expirada no incrementa el
    # contador de intentos fallidos y no genera sesión/JWT.
    # -----------------------------------------------------

    if (
        registro["requiere_cambio_password"]
        and registro["password_temporal_expira_en"] is not None
        and registro["password_temporal_expira_en"]
            <= datetime.now(timezone.utc)
    ):
        registrar_evento(
            LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "CREDENCIALES_INVALIDAS"
            }
        )

        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    # -----------------------------------------------------
    # 9. VALIDAR EXPIRACIÓN DE CONTRASEÑA DEFINITIVA
    # -----------------------------------------------------
    # La expiración definitiva solo se evalúa cuando el
    # usuario NO está en un flujo de contraseña temporal.
    #
    # Si la contraseña definitiva venció, la autenticación
    # sigue siendo válida porque el usuario presentó la
    # contraseña correcta, pero PostgreSQL marca la cuenta
    # para cambio obligatorio. Se permite crear una sesión
    # limitada para que PUT /auth/password pueda completar
    # el cambio. seguridad.py mantiene bloqueado el acceso a
    # las funciones normales mientras el indicador sea TRUE.
    #
    # Las credenciales definitivas heredadas con NULL se
    # mantienen compatibles hasta ejecutar la migración de
    # fechas para los usuarios existentes.
    # -----------------------------------------------------

    requiere_cambio_password = bool(
        registro["requiere_cambio_password"]
    )

    password_definitiva_expirada = (
        not requiere_cambio_password
        and registro["password_expira_en"] is not None
        and registro["password_expira_en"]
            <= datetime.now(timezone.utc)
    )

    if password_definitiva_expirada:
        marcar_cambio_obligatorio = text("""
            UPDATE credenciales
            SET
                requiere_cambio_password = TRUE,
                fecha_modificacion = NOW()
            WHERE usuario_id = :usuario_id
              AND activo = TRUE
        """)

        with engine.begin() as conexion:
            conexion.execute(
                marcar_cambio_obligatorio,
                {
                    "usuario_id":
                        registro["usuario_id"]
                }
            )

        requiere_cambio_password = True

    # -----------------------------------------------------
    # 10. REINICIAR CONTADOR DESPUÉS DE LOGIN CORRECTO
    # -----------------------------------------------------
    # Si existían uno o dos intentos fallidos anteriores y
    # posteriormente se presenta la contraseña correcta,
    # reiniciamos el contador.
    #
    # Una cuenta que ya llegó al estado bloqueado nunca llega
    # a este punto porque fue rechazada anteriormente.
    # -----------------------------------------------------

    if registro["intentos_fallidos"] > 0:

        reiniciar_intentos = text("""
            UPDATE credenciales
            SET
                intentos_fallidos = 0,
                bloqueado_en = NULL,
                fecha_modificacion = NOW()
            WHERE usuario_id = :usuario_id
        """)

        with engine.begin() as conexion:
            conexion.execute(
                reiniciar_intentos,
                {
                    "usuario_id":
                        registro["usuario_id"]
                }
            )

    # -----------------------------------------------------
    # 11. OBTENER ROLES ACTUALES DESDE POSTGRESQL
    # -----------------------------------------------------

    # Aunque los roles posteriormente se incluyen en el JWT,
    # seguridad.py vuelve a consultar los roles actuales de
    # PostgreSQL para las decisiones de autorización.
    #
    # Esto evita depender exclusivamente de información que
    # quedó almacenada previamente dentro del token.
    # -----------------------------------------------------

    consulta_roles = text("""
        SELECT
            r.nombre
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
            {
                "usuario_id":
                    registro["usuario_id"]
            }
        )

        roles = [
            fila[0]
            for fila
            in resultado_roles.fetchall()
        ]

    # -----------------------------------------------------
    # 12. COMPROBAR QUE EL USUARIO TENGA UN ROL ACTIVO
    # -----------------------------------------------------
    # Un usuario autenticado sin rol no debe acceder a una
    # plataforma funcional del sistema.
    # -----------------------------------------------------

    if not roles:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un rol activo asignado"
        )

    # -----------------------------------------------------
    # 13. COMPROBAR SI EL USUARIO TIENE MFA ACTIVO
    # -----------------------------------------------------
    # Si MFA está activo, la contraseña constituye únicamente
    # el primer factor. En este punto NO se crea una sesión y
    # NO se emite un JWT de acceso.
    # -----------------------------------------------------

    consulta_mfa = text("""
        SELECT activo
        FROM mfa_totp
        WHERE usuario_id = :usuario_id
        LIMIT 1
    """)

    with engine.connect() as conexion:
        estado_mfa = conexion.execute(
            consulta_mfa,
            {"usuario_id": registro["usuario_id"]}
        ).mappings().first()

    mfa_activo = bool(
        estado_mfa is not None and estado_mfa["activo"]
    )

    # =====================================================
    # MFA OBLIGATORIO PARA TODAS LAS CUENTAS
    # =====================================================
    # Una contraseña correcta ya no genera por sí sola una sesión.
    # Siempre se emite un desafío temporal de primer factor:
    #
    # - MFA activo:
    #     el desafío se utiliza para verificar el TOTP.
    #
    # - MFA no configurado:
    #     el desafío autoriza exclusivamente el enrolamiento
    #     obligatorio y la posterior confirmación del primer TOTP.
    #
    # En ninguno de los dos casos se entrega todavía access_token.
    # =====================================================
    desafio = secrets.token_urlsafe(32)
    desafio_hash = hashlib.sha256(
        desafio.encode("utf-8")
    ).hexdigest()

    expira_desafio = (
        datetime.now(timezone.utc)
        + timedelta(minutes=MFA_CHALLENGE_EXPIRE_MINUTES)
    )

    crear_desafio = text("""
        INSERT INTO mfa_desafios (
            usuario_id,
            desafio_hash,
            fecha_expiracion,
            usado,
            intentos
        )
        VALUES (
            :usuario_id,
            :desafio_hash,
            :fecha_expiracion,
            FALSE,
            0
        )
    """)

    # Solo puede existir un flujo MFA pendiente por usuario.
    invalidar_anteriores = text("""
        UPDATE mfa_desafios
        SET
            usado = TRUE,
            usado_en = NOW()
        WHERE usuario_id = :usuario_id
          AND usado = FALSE
          AND fecha_expiracion > NOW()
    """)

    with engine.begin() as conexion:
        conexion.execute(
            invalidar_anteriores,
            {"usuario_id": registro["usuario_id"]}
        )
        conexion.execute(
            crear_desafio,
            {
                "usuario_id": registro["usuario_id"],
                "desafio_hash": desafio_hash,
                "fecha_expiracion": expira_desafio,
            }
        )

    if mfa_activo:
        return {
            "mfa_requerido": True,
            "mfa_enrolamiento_requerido": False,
            "desafio_mfa": desafio,
            "expires_in": MFA_CHALLENGE_EXPIRE_MINUTES * 60,
        }

    # MFA no está activo: el usuario NO recibe sesión/JWT.
    # Debe completar primero el enrolamiento obligatorio.
    return {
        "mfa_requerido": True,
        "mfa_enrolamiento_requerido": True,
        "desafio_mfa": desafio,
        "expires_in": MFA_CHALLENGE_EXPIRE_MINUTES * 60,
    }

# =========================================================
# MFA / TOTP - ENROLAMIENTO OBLIGATORIO PREVIO A LA SESIÓN
# =========================================================
# Estos endpoints se utilizan cuando el usuario ya validó correo
# y contraseña, pero todavía NO tiene MFA activo.
#
# SEGURIDAD:
# - el desafío no es un JWT y no concede acceso al portal;
# - PostgreSQL conserva únicamente SHA-256 del desafío;
# - el secreto TOTP se almacena cifrado con Fernet;
# - el secreto/URI nunca se devuelve como texto;
# - el QR no se almacena en disco;
# - la sesión/JWT definitivo solo se emite tras confirmar TOTP.
# =========================================================

@router.post("/mfa/enrolamiento-obligatorio")
def iniciar_enrolamiento_mfa_obligatorio(
    datos: EnrolamientoMFAObligatorioRequest
):
    desafio = datos.desafio.strip()

    if not desafio:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

    desafio_hash = hashlib.sha256(
        desafio.encode("utf-8")
    ).hexdigest()

    consulta = text("""
        SELECT
            d.id AS desafio_id,
            d.usuario_id,
            d.intentos,
            u.email,
            u.activo AS usuario_activo,
            c.activo AS credencial_activa,
            c.bloqueado AS credencial_bloqueada,
            COALESCE(m.activo, FALSE) AS mfa_activo
        FROM mfa_desafios d
        JOIN usuarios_plataforma u
            ON u.id = d.usuario_id
        JOIN credenciales c
            ON c.usuario_id = d.usuario_id
        LEFT JOIN mfa_totp m
            ON m.usuario_id = d.usuario_id
        WHERE d.desafio_hash = :desafio_hash
          AND d.usado = FALSE
          AND d.fecha_expiracion > NOW()
        LIMIT 1
    """)

    with engine.connect() as conexion:
        registro = conexion.execute(
            consulta,
            {"desafio_hash": desafio_hash}
        ).mappings().first()

    if registro is None:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

    if (
        not registro["usuario_activo"]
        or not registro["credencial_activa"]
        or registro["credencial_bloqueada"]
    ):
        with engine.begin() as conexion:
            conexion.execute(
                text("""
                    UPDATE mfa_desafios
                    SET usado = TRUE, usado_en = NOW()
                    WHERE id = :desafio_id
                      AND usado = FALSE
                """),
                {"desafio_id": registro["desafio_id"]}
            )

        raise HTTPException(
            status_code=403,
            detail="El estado de la cuenta no permite iniciar sesión"
        )

    if registro["mfa_activo"]:
        raise HTTPException(
            status_code=409,
            detail="MFA ya se encuentra activo para este usuario"
        )

    if registro["intentos"] >= MFA_CHALLENGE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=423,
            detail="Desafío MFA bloqueado por máximo de intentos"
        )

    secreto = generar_secreto_totp()
    secreto_cifrado = cifrar_secreto_totp(secreto)

    qr_png = generar_qr_aprovisionamiento_png(
        secreto=secreto,
        identificador_usuario=str(registro["email"]),
    )

    guardar = text("""
        INSERT INTO mfa_totp (
            usuario_id,
            secreto_cifrado,
            activo,
            ultimo_contador_validado,
            fecha_enrolamiento,
            fecha_creacion,
            fecha_modificacion
        )
        VALUES (
            :usuario_id,
            :secreto_cifrado,
            FALSE,
            NULL,
            NULL,
            NOW(),
            NOW()
        )
        ON CONFLICT (usuario_id)
        DO UPDATE SET
            secreto_cifrado = EXCLUDED.secreto_cifrado,
            activo = FALSE,
            ultimo_contador_validado = NULL,
            fecha_enrolamiento = NULL,
            fecha_modificacion = NOW()
        WHERE mfa_totp.activo = FALSE
        RETURNING usuario_id
    """)

    with engine.begin() as conexion:
        guardado = conexion.execute(
            guardar,
            {
                "usuario_id": registro["usuario_id"],
                "secreto_cifrado": secreto_cifrado,
            }
        ).mappings().first()

    if guardado is None:
        raise HTTPException(
            status_code=409,
            detail="MFA ya se encuentra activo para este usuario"
        )

    registrar_evento(
        MFA_ENROLAMIENTO_INICIADO,
        actor_usuario_id=registro["usuario_id"],
        objetivo_usuario_id=registro["usuario_id"],
        resultado="EXITO",
        detalle={"motivo": "ENROLAMIENTO_TOTP_OBLIGATORIO"}
    )

    return Response(
        content=qr_png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.post("/mfa/activar-obligatorio")
def activar_mfa_obligatorio(
    datos: ActivarMFAObligatorioRequest
):
    desafio = datos.desafio.strip()

    if not desafio:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

    desafio_hash = hashlib.sha256(
        desafio.encode("utf-8")
    ).hexdigest()

    consulta = text("""
        SELECT
            d.id AS desafio_id,
            d.usuario_id,
            d.intentos,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo AS usuario_activo,
            c.activo AS credencial_activa,
            c.bloqueado AS credencial_bloqueada,
            c.requiere_cambio_password,
            m.secreto_cifrado,
            m.activo AS mfa_activo
        FROM mfa_desafios d
        JOIN usuarios_plataforma u
            ON u.id = d.usuario_id
        JOIN credenciales c
            ON c.usuario_id = d.usuario_id
        JOIN mfa_totp m
            ON m.usuario_id = d.usuario_id
        WHERE d.desafio_hash = :desafio_hash
          AND d.usado = FALSE
          AND d.fecha_expiracion > NOW()
        LIMIT 1
    """)

    with engine.connect() as conexion:
        registro = conexion.execute(
            consulta,
            {"desafio_hash": desafio_hash}
        ).mappings().first()

    if registro is None:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

    if (
        not registro["usuario_activo"]
        or not registro["credencial_activa"]
        or registro["credencial_bloqueada"]
    ):
        with engine.begin() as conexion:
            conexion.execute(
                text("""
                    UPDATE mfa_desafios
                    SET usado = TRUE, usado_en = NOW()
                    WHERE id = :desafio_id
                      AND usado = FALSE
                """),
                {"desafio_id": registro["desafio_id"]}
            )

        raise HTTPException(
            status_code=403,
            detail="El estado de la cuenta no permite iniciar sesión"
        )

    if registro["mfa_activo"]:
        raise HTTPException(
            status_code=409,
            detail="MFA ya se encuentra activo para este usuario"
        )

    if registro["intentos"] >= MFA_CHALLENGE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=423,
            detail="Desafío MFA bloqueado por máximo de intentos"
        )

    secreto = descifrar_secreto_totp(
        registro["secreto_cifrado"]
    )

    validacion = validar_codigo_totp(
        secreto=secreto,
        codigo=datos.codigo,
    )

    if not validacion.valido or validacion.contador is None:
        registrar_fallo = text("""
            UPDATE mfa_desafios
            SET
                intentos = intentos + 1,
                usado = CASE
                    WHEN intentos + 1 >= :max_intentos
                    THEN TRUE
                    ELSE usado
                END,
                usado_en = CASE
                    WHEN intentos + 1 >= :max_intentos
                    THEN NOW()
                    ELSE usado_en
                END
            WHERE id = :desafio_id
              AND usado = FALSE
            RETURNING intentos, usado
        """)

        with engine.begin() as conexion:
            estado = conexion.execute(
                registrar_fallo,
                {
                    "desafio_id": registro["desafio_id"],
                    "max_intentos": MFA_CHALLENGE_MAX_ATTEMPTS,
                }
            ).mappings().first()

        registrar_evento(
            MFA_LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "CODIGO_TOTP_ENROLAMIENTO_INVALIDO",
                "intentos": (
                    estado["intentos"] if estado is not None else None
                ),
            }
        )

        if estado is not None and estado["usado"]:
            raise HTTPException(
                status_code=423,
                detail="Desafío MFA bloqueado por máximo de intentos"
            )

        raise HTTPException(
            status_code=401,
            detail="Código de autenticación no válido"
        )

    # Activamos MFA y consumimos el desafío dentro de una misma
    # transacción. El primer contador TOTP queda registrado para
    # impedir que ese mismo código pueda reutilizarse después.
    activar = text("""
        UPDATE mfa_totp
        SET
            activo = TRUE,
            ultimo_contador_validado = :contador,
            fecha_enrolamiento = NOW(),
            fecha_modificacion = NOW()
        WHERE usuario_id = :usuario_id
          AND activo = FALSE
        RETURNING usuario_id
    """)

    consumir_desafio = text("""
        UPDATE mfa_desafios
        SET
            usado = TRUE,
            usado_en = NOW()
        WHERE id = :desafio_id
          AND usado = FALSE
          AND fecha_expiracion > NOW()
        RETURNING id
    """)

    with engine.begin() as conexion:
        activado = conexion.execute(
            activar,
            {
                "usuario_id": registro["usuario_id"],
                "contador": validacion.contador,
            }
        ).mappings().first()

        desafio_consumido = conexion.execute(
            consumir_desafio,
            {"desafio_id": registro["desafio_id"]}
        ).mappings().first()

        if activado is None or desafio_consumido is None:
            raise HTTPException(
                status_code=409,
                detail="El estado del enrolamiento MFA cambió"
            )

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
        roles = [
            fila[0]
            for fila in conexion.execute(
                consulta_roles,
                {"usuario_id": registro["usuario_id"]}
            ).fetchall()
        ]

    if not roles:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un rol activo asignado"
        )

    registrar_evento(
        MFA_ACTIVADO,
        actor_usuario_id=registro["usuario_id"],
        objetivo_usuario_id=registro["usuario_id"],
        resultado="EXITO",
        detalle={"motivo": "CONFIRMACION_TOTP_OBLIGATORIA"}
    )

    respuesta = _emitir_sesion_y_token(
        registro={
            "usuario_id": registro["usuario_id"],
            "id_externo": registro["id_externo"],
            "nombre": registro["nombre"],
            "email": registro["email"],
        },
        roles=roles,
        requiere_cambio_password=bool(
            registro["requiere_cambio_password"]
        ),
    )

    registrar_evento(
        MFA_LOGIN_EXITOSO,
        actor_usuario_id=registro["usuario_id"],
        resultado="EXITO",
        detalle={
            "session_id": respuesta["session_id"],
            "motivo": "PRIMER_ENROLAMIENTO_TOTP_COMPLETADO",
        }
    )

    return respuesta


# =========================================================
# MFA / TOTP - SEGUNDO FACTOR DEL LOGIN
# =========================================================
# Este endpoint NO utiliza Depends(obtener_usuario_desde_token),
# porque todavía no existe una sesión autenticada definitiva.
#
# El desafío:
# - es aleatorio;
# - expira en pocos minutos;
# - es de un solo uso;
# - se almacena únicamente como SHA-256;
# - limita los intentos TOTP.
# =========================================================

@router.post("/mfa/verificar-login")
def verificar_mfa_login(
    datos: VerificarMFALoginRequest
):
    desafio = datos.desafio.strip()

    if not desafio:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

    desafio_hash = hashlib.sha256(
        desafio.encode("utf-8")
    ).hexdigest()

    consulta_desafio = text("""
        SELECT
            d.id AS desafio_id,
            d.usuario_id,
            d.intentos,
            u.id_externo,
            u.nombre,
            u.email,
            u.activo AS usuario_activo,
            c.activo AS credencial_activa,
            c.bloqueado AS credencial_bloqueada,
            c.requiere_cambio_password
        FROM mfa_desafios d
        JOIN usuarios_plataforma u
            ON u.id = d.usuario_id
        JOIN credenciales c
            ON c.usuario_id = d.usuario_id
           AND c.activo = TRUE
        WHERE d.desafio_hash = :desafio_hash
          AND d.usado = FALSE
          AND d.fecha_expiracion > NOW()
        LIMIT 1
    """)

    with engine.connect() as conexion:
        registro = conexion.execute(
            consulta_desafio,
            {"desafio_hash": desafio_hash}
        ).mappings().first()

    if registro is None:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

    # -----------------------------------------------------
    # REVALIDACIÓN DEL ESTADO DE LA CUENTA ANTES DEL MFA
    # -----------------------------------------------------
    # El desafío MFA pudo haberse generado cuando la cuenta estaba
    # habilitada y posteriormente la credencial pudo ser bloqueada.
    #
    # Por seguridad, el segundo factor vuelve a comprobar el estado
    # actual del usuario y de su credencial antes de permitir que el
    # flujo continúe hacia la creación de la sesión definitiva.
    # -----------------------------------------------------
    if (
        not registro["usuario_activo"]
        or not registro["credencial_activa"]
        or registro["credencial_bloqueada"]
    ):
        # Un desafío emitido antes de que la cuenta cambiara de estado
        # no debe recuperar validez si posteriormente la cuenta es
        # reactivada o desbloqueada. Lo consumimos antes de rechazar.
        invalidar_desafio_estado = text("""
            UPDATE mfa_desafios
            SET
                usado = TRUE,
                usado_en = NOW()
            WHERE id = :desafio_id
              AND usado = FALSE
        """)

        with engine.begin() as conexion:
            conexion.execute(
                invalidar_desafio_estado,
                {"desafio_id": registro["desafio_id"]}
            )

        registrar_evento(
            MFA_LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={"motivo": "ESTADO_CUENTA_NO_PERMITE_MFA"}
        )

        raise HTTPException(
            status_code=403,
            detail="El estado de la cuenta no permite iniciar sesión"
        )

    if registro["intentos"] >= MFA_CHALLENGE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=423,
            detail="Desafío MFA bloqueado por máximo de intentos"
        )

    consulta_mfa = text("""
        SELECT secreto_cifrado
        FROM mfa_totp
        WHERE usuario_id = :usuario_id
          AND activo = TRUE
        LIMIT 1
    """)

    with engine.connect() as conexion:
        configuracion = conexion.execute(
            consulta_mfa,
            {"usuario_id": registro["usuario_id"]}
        ).mappings().first()

    if configuracion is None:
        raise HTTPException(
            status_code=401,
            detail="MFA no se encuentra disponible para esta cuenta"
        )

    secreto = descifrar_secreto_totp(
        configuracion["secreto_cifrado"]
    )

    validacion = validar_codigo_totp(
        secreto=secreto,
        codigo=datos.codigo,
    )

    if not validacion.valido or validacion.contador is None:
        # Incremento atómico. Al alcanzar el máximo, el desafío queda
        # consumido y ya no admite nuevos códigos.
        registrar_fallo = text("""
            UPDATE mfa_desafios
            SET
                intentos = intentos + 1,
                usado = CASE
                    WHEN intentos + 1 >= :max_intentos
                    THEN TRUE
                    ELSE usado
                END,
                usado_en = CASE
                    WHEN intentos + 1 >= :max_intentos
                    THEN NOW()
                    ELSE usado_en
                END
            WHERE id = :desafio_id
              AND usado = FALSE
            RETURNING intentos, usado
        """)

        with engine.begin() as conexion:
            estado = conexion.execute(
                registrar_fallo,
                {
                    "desafio_id": registro["desafio_id"],
                    "max_intentos": MFA_CHALLENGE_MAX_ATTEMPTS,
                }
            ).mappings().first()

        registrar_evento(
            MFA_LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={
                "motivo": "CODIGO_TOTP_INVALIDO",
                "intentos": (
                    estado["intentos"] if estado is not None else None
                ),
            }
        )

        if estado is not None and estado["usado"]:
            raise HTTPException(
                status_code=423,
                detail="Desafío MFA bloqueado por máximo de intentos"
            )

        raise HTTPException(
            status_code=401,
            detail="Código de autenticación no válido"
        )

    # -----------------------------------------------------
    # CONSUMO ANTI-REPLAY DEL CONTADOR TOTP
    # -----------------------------------------------------
    # consumir_contador_totp() realiza el UPDATE condicional en
    # PostgreSQL y solo acepta contadores posteriores al último
    # utilizado por esta cuenta.
    # -----------------------------------------------------
    contador_consumido = consumir_contador_totp(
        usuario_id=registro["usuario_id"],
        contador=validacion.contador,
    )

    if not contador_consumido:
        registrar_evento(
            MFA_LOGIN_FALLIDO,
            actor_usuario_id=registro["usuario_id"],
            resultado="FALLO",
            detalle={"motivo": "TOTP_REUTILIZADO"}
        )
        raise HTTPException(
            status_code=401,
            detail="Código de autenticación no válido"
        )

    # El desafío se consume de forma atómica. Si otra petición lo
    # utilizó primero, no se crea ninguna sesión.
    consumir_desafio = text("""
        UPDATE mfa_desafios
        SET
            usado = TRUE,
            usado_en = NOW()
        WHERE id = :desafio_id
          AND usado = FALSE
          AND fecha_expiracion > NOW()
        RETURNING id
    """)

    with engine.begin() as conexion:
        desafio_consumido = conexion.execute(
            consumir_desafio,
            {"desafio_id": registro["desafio_id"]}
        ).mappings().first()

    if desafio_consumido is None:
        raise HTTPException(
            status_code=401,
            detail="Desafío MFA no válido o expirado"
        )

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
        roles = [
            fila[0]
            for fila in conexion.execute(
                consulta_roles,
                {"usuario_id": registro["usuario_id"]}
            ).fetchall()
        ]

    if not roles:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un rol activo asignado"
        )

    respuesta = _emitir_sesion_y_token(
        registro={
            "usuario_id": registro["usuario_id"],
            "id_externo": registro["id_externo"],
            "nombre": registro["nombre"],
            "email": registro["email"],
        },
        roles=roles,
        requiere_cambio_password=bool(
            registro["requiere_cambio_password"]
        ),
    )

    registrar_evento(
        MFA_LOGIN_EXITOSO,
        actor_usuario_id=registro["usuario_id"],
        resultado="EXITO",
        detalle={
            "session_id": respuesta["session_id"],
            "motivo": "SEGUNDO_FACTOR_TOTP",
        }
    )

    return respuesta


# =========================================================
# LOGOUT
# Revoca la sesión actual
# =========================================================

@router.post("/logout")
def logout(
    usuario=Depends(
        obtener_usuario_desde_token
    )
):
    consulta = text("""
        UPDATE sesiones
        SET
            revocada = TRUE,
            fecha_revocacion = NOW()
        WHERE id = :session_id
          AND usuario_id = :usuario_id
          AND revocada = FALSE
        RETURNING
            id,
            usuario_id,
            jti,
            revocada,
            fecha_revocacion
    """)

    with engine.begin() as conexion:
        sesion = conexion.execute(
            consulta,
            {
                "session_id":
                    usuario["session_id"],

                "usuario_id":
                    usuario["id"]
            }
        ).mappings().first()

    if sesion is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "La sesión ya fue revocada "
                "o no existe"
            )
        )

    return {
        "mensaje":
            "Sesión cerrada correctamente",

        "session_id":
            sesion["id"],

        "revocada":
            sesion["revocada"],

        "fecha_revocacion":
            sesion["fecha_revocacion"]
    }


# =========================================================
# LISTAR SESIONES ACTIVAS DEL USUARIO
# =========================================================
# Devuelve únicamente metadatos no sensibles.
# El JTI no se expone en la respuesta.
# =========================================================

@router.get("/sesiones")
def listar_sesiones(
    usuario=Depends(
        obtener_usuario_desde_token
    )
):
    consulta = text("""
        SELECT
            id,
            usuario_id,
            fecha_inicio,
            fecha_expiracion,
            revocada,
            fecha_revocacion
        FROM sesiones
        WHERE usuario_id = :usuario_id
          AND revocada = FALSE
          AND fecha_expiracion > NOW()
        ORDER BY fecha_inicio DESC
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "usuario_id": usuario["id"]
            }
        )

        sesiones = [
            dict(fila)
            for fila in resultado.mappings().all()
        ]

    return {
        "total": len(sesiones),
        "sesiones": sesiones
    }


# =========================================================
# REVOCAR UNA SESIÓN PROPIA
# =========================================================
# El usuario solo puede revocar una sesión que le pertenezca.
# No se devuelve el JTI.
# =========================================================

@router.post("/sesiones/{sesion_id}/revocar")
def revocar_sesion(
    sesion_id: int,
    usuario=Depends(
        obtener_usuario_desde_token
    )
):
    consulta = text("""
        UPDATE sesiones
        SET
            revocada = TRUE,
            fecha_revocacion = NOW()
        WHERE id = :sesion_id
          AND usuario_id = :usuario_id
          AND revocada = FALSE
          AND fecha_expiracion > NOW()
        RETURNING
            id,
            usuario_id,
            revocada,
            fecha_revocacion
    """)

    with engine.begin() as conexion:
        sesion = conexion.execute(
            consulta,
            {
                "sesion_id": sesion_id,
                "usuario_id": usuario["id"]
            }
        ).mappings().first()

    if sesion is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Sesión no encontrada, ya revocada, "
                "expirada o no pertenece al usuario"
            )
        )

    return {
        "mensaje": "Sesión revocada correctamente",
        "sesion": dict(sesion)
    }


# =========================================================
# RESTABLECIMIENTO ADMINISTRATIVO DE MFA
# =========================================================
# JERARQUÍA DE AUTORIZACIÓN:
#
# ADMIN_TI
#   -> puede restablecer MFA únicamente de ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> puede restablecer MFA únicamente de líderes pertenecientes
#      a compañías activas que tenga asignadas.
#
# SEGURIDAD:
# - se reutiliza validar_administracion_usuario() como fuente RBAC;
# - no se confía en IDs de compañía enviados por el frontend;
# - se impide la autoadministración;
# - se elimina el secreto TOTP anterior;
# - se invalidan desafíos MFA pendientes;
# - se revocan sesiones activas;
# - NO se modifica la contraseña;
# - NO se devuelve secreto TOTP, QR, JWT, JTI ni credenciales.
#
# Después del restablecimiento, el login existente detectará que no
# existe un MFA activo y obligará al usuario a realizar un nuevo
# enrolamiento antes de emitir una sesión definitiva.
# =========================================================

@router.post(
    "/usuarios/{usuario_id}/mfa/restablecer"
)
def restablecer_mfa_usuario_admin(
    usuario_id: int,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # CONSULTAS DE LA OPERACIÓN
    # -----------------------------------------------------
    # DELETE elimina también el secreto cifrado anterior. De esta
    # manera el siguiente enrolamiento parte de una vinculación
    # completamente nueva y no reutiliza material TOTP previo.
    # -----------------------------------------------------
    eliminar_mfa = text("""
        DELETE FROM mfa_totp
        WHERE usuario_id = :usuario_id
        RETURNING usuario_id
    """)

    invalidar_desafios = text("""
        UPDATE mfa_desafios
        SET
            usado = TRUE,
            usado_en = NOW()
        WHERE usuario_id = :usuario_id
          AND usado = FALSE
        RETURNING id
    """)

    revocar_sesiones = text("""
        UPDATE sesiones
        SET
            revocada = TRUE,
            fecha_revocacion = NOW()
        WHERE usuario_id = :usuario_id
          AND revocada = FALSE
          AND fecha_expiracion > NOW()
        RETURNING id
    """)

    # -----------------------------------------------------
    # TRANSACCIÓN ATÓMICA
    # -----------------------------------------------------
    # La autorización y todos los cambios de seguridad se realizan
    # en una sola transacción. Si una operación falla, PostgreSQL
    # revierte el conjunto completo.
    # -----------------------------------------------------
    with engine.begin() as conexion:
        objetivo = validar_administracion_usuario(
            conexion=conexion,
            usuario_actual=usuario_actual,
            usuario_objetivo_id=usuario_id
        )

        if not objetivo["activo"]:
            raise HTTPException(
                status_code=400,
                detail="El usuario se encuentra inactivo"
            )

        mfa_eliminado = conexion.execute(
            eliminar_mfa,
            {"usuario_id": usuario_id}
        ).mappings().first()

        desafios_invalidados = conexion.execute(
            invalidar_desafios,
            {"usuario_id": usuario_id}
        ).fetchall()

        sesiones_revocadas = conexion.execute(
            revocar_sesiones,
            {"usuario_id": usuario_id}
        ).fetchall()

        # T06: persistir auditoría sanitizada antes del COMMIT.
        registrar_evento(
            "MFA_RESTABLECIDO_ADMIN",
            actor_usuario_id=usuario_actual["id"],
            objetivo_usuario_id=usuario_id,
            resultado="EXITO",
            conexion=conexion,
            detalle={
                "mfa_previo_eliminado": mfa_eliminado is not None,
                "desafios_invalidados": len(desafios_invalidados),
                "sesiones_revocadas": len(sesiones_revocadas),
            }
        )

    return {
        "mensaje": (
            "MFA restablecido correctamente. "
            "El usuario deberá vincular Authenticator "
            "en su próximo inicio de sesión."
        ),
        "usuario_id": usuario_id,
        "mfa_activo": False,
        "sesiones_revocadas": len(sesiones_revocadas),
    }


# =========================================================
# REVOCAR TODAS LAS SESIONES ACTIVAS DE UN USUARIO
# =========================================================
# Permite a los administradores autorizados invalidar todas
# las sesiones activas de otro usuario.
#
# AUTORIZACIÓN:
#
# ADMIN_TI
#   -> puede administrar usuarios ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> puede administrar usuarios de las compañías que tenga
#      asignadas.
#
#   -> no puede administrar ADMIN_TI.
#   -> no puede administrar otros ADMIN_SOPORTE.
#
# LÍDERES
#   -> no pueden revocar sesiones de otros usuarios.
#
# SEGURIDAD:
# - se reutiliza validar_administracion_usuario();
# - no se confía únicamente en los roles incluidos en JWT;
# - las reglas se verifican contra PostgreSQL;
# - no se devuelve JTI ni información sensible.
# =========================================================
# =========================================================

@router.post(
    "/usuarios/{usuario_id}/sesiones/revocar"
)
def revocar_sesiones_usuario_admin(
    usuario_id: int,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # CONSULTA PARA REVOCAR SESIONES
    # -----------------------------------------------------
    # Únicamente se modifican sesiones:
    #
    # - pertenecientes al usuario objetivo;
    # - que todavía no estén revocadas;
    # - cuya fecha de expiración todavía no haya pasado.
    #
    # No necesitamos recuperar ni devolver el JTI.
    # -----------------------------------------------------

    consulta_revocar = text("""
        UPDATE sesiones
        SET
            revocada = TRUE,
            fecha_revocacion = NOW()
        WHERE usuario_id = :usuario_id
          AND revocada = FALSE
          AND fecha_expiracion > NOW()
        RETURNING id
    """)

    # -----------------------------------------------------
    # TRANSACCIÓN ATÓMICA
    # -----------------------------------------------------
    # Primero validamos si el administrador autenticado puede
    # administrar al usuario objetivo.
    #
    # La autorización y la revocación se ejecutan usando la
    # misma transacción para mantener consistencia.
    # -----------------------------------------------------

    with engine.begin() as conexion:

        validar_administracion_usuario(
            conexion=conexion,
            usuario_actual=usuario_actual,
            usuario_objetivo_id=usuario_id
        )

        resultado = conexion.execute(
            consulta_revocar,
            {
                "usuario_id":
                    usuario_id
            }
        )

        sesiones = resultado.fetchall()

    # -----------------------------------------------------
    # RESPUESTA SEGURA
    # -----------------------------------------------------
    # Solamente informamos cuántas sesiones fueron revocadas.
    #
    # No devolvemos:
    # - JWT;
    # - JTI;
    # - password_hash;
    # - información interna de las sesiones.
    # -----------------------------------------------------

    return {
        "mensaje":
            "Sesiones activas revocadas",

        "usuario_id":
            usuario_id,

        "total_revocadas":
            len(sesiones)
    }

# =========================================================
# DESBLOQUEAR CUENTA DE USUARIO
# =========================================================
# Permite retirar un bloqueo de seguridad producido por
# múltiples intentos fallidos de autenticación.
#
# REGLAS DE AUTORIZACIÓN:
#
# ADMIN_TI
#   -> puede administrar/desbloquear ADMIN_SOPORTE.
#
# ADMIN_SOPORTE
#   -> puede administrar/desbloquear líderes únicamente
#      dentro de las compañías que tenga asignadas.
#
# LÍDERES
#   -> no pueden utilizar este endpoint.
#
# IMPORTANTE:
# El desbloqueo NO modifica la contraseña.
# Únicamente restablece el estado asociado al bloqueo por
# intentos fallidos.
# =========================================================

@router.post(
    "/usuarios/{usuario_id}/desbloquear"
)
def desbloquear_usuario(
    usuario_id: int,
    usuario_actual=Depends(
        requiere_roles(
            "ADMIN_TI",
            "ADMIN_SOPORTE"
        )
    )
):
    # -----------------------------------------------------
    # TRANSACCIÓN DE DESBLOQUEO
    # -----------------------------------------------------
    # validar_administracion_usuario() aplica las mismas
    # reglas de autorización y multitenancy utilizadas por
    # las demás operaciones administrativas.
    # -----------------------------------------------------

    with engine.begin() as conexion:

        validar_administracion_usuario(
            conexion=conexion,
            usuario_actual=usuario_actual,
            usuario_objetivo_id=usuario_id
        )

        consulta_desbloquear = text("""
            UPDATE credenciales
            SET
                intentos_fallidos = 0,
                bloqueado = FALSE,
                bloqueado_en = NULL,
                fecha_modificacion = NOW()
            WHERE usuario_id = :usuario_id
              AND activo = TRUE
            RETURNING
                usuario_id,
                bloqueado,
                intentos_fallidos
        """)

        resultado = conexion.execute(
            consulta_desbloquear,
            {
                "usuario_id":
                    usuario_id
            }
        ).mappings().first()

        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail="Credencial activa no encontrada"
            )

    # -----------------------------------------------------
    # AUDITORÍA - DESBLOQUEO ADMINISTRATIVO
    # -----------------------------------------------------
    # El evento se registra después de confirmar la transacción.
    # actor_usuario_id identifica al administrador autenticado y
    # objetivo_usuario_id identifica la cuenta desbloqueada.
    registrar_evento(
        CUENTA_DESBLOQUEADA,
        actor_usuario_id=usuario_actual["id"],
        objetivo_usuario_id=usuario_id,
        resultado="EXITO",
        detalle={
            "motivo": "DESBLOQUEO_ADMINISTRATIVO"
        }
    )

    # -----------------------------------------------------
    # RESPUESTA SEGURA
    # -----------------------------------------------------
    # No devolvemos contraseña, hash, JWT ni JTI.
    # -----------------------------------------------------

    return {
        "mensaje":
            "Usuario desbloqueado correctamente",

        "usuario_id":
            resultado["usuario_id"],

        "bloqueado":
            resultado["bloqueado"],

        "intentos_fallidos":
            resultado["intentos_fallidos"]
    }

# =========================================================
# ELIMINAR SESIONES EXPIRADAS
# Solo ADMIN
#
# Posteriormente esta función podrá ejecutarse
# automáticamente desde un worker.
# =========================================================

@router.delete(
    "/sesiones/expiradas"
)
def limpiar_sesiones_expiradas(
   usuario_actual=Depends(
     requiere_roles("ADMIN_TI")
   )
):
    consulta = text("""
        DELETE FROM sesiones
        WHERE fecha_expiracion <= NOW()
        RETURNING
            id
    """)

    with engine.begin() as conexion:
        resultado = conexion.execute(
            consulta
        )

        sesiones_eliminadas = (
            resultado.fetchall()
        )

        # -----------------------------------------------------
    # AUDITORÍA DE LIMPIEZA DE SESIONES EXPIRADAS
    # -----------------------------------------------------
    # Esta operación administrativa elimina sesiones que ya
    # alcanzaron su fecha de expiración.
    #
    # Se registra únicamente:
    # - El administrador que ejecutó la operación.
    # - El resultado de la operación.
    # - La cantidad total de sesiones eliminadas.
    #
    # No se registran JWT, JTI, contraseñas, hashes ni los
    # identificadores individuales de las sesiones eliminadas.
    # -----------------------------------------------------
    registrar_evento(
        SESIONES_EXPIRADAS_ELIMINADAS,
        actor_usuario_id=usuario_actual["id"],
        resultado="EXITO",
        detalle={
            "motivo": "LIMPIEZA_SESIONES_EXPIRADAS",
            "total_eliminadas": len(sesiones_eliminadas)
        }
    )

    return {
        "mensaje":
            "Sesiones expiradas eliminadas",

        "total_eliminadas":
            len(sesiones_eliminadas)
    }

# =========================================================
# INFORMACIÓN DEL USUARIO AUTENTICADO
# =========================================================
# Devuelve únicamente información necesaria para que el
# frontend identifique al usuario y aplique su navegación.
#
# SEGURIDAD:
# - obtener_usuario_desde_token() puede manejar internamente
#   datos de sesión como session_id y JTI.
# - esos identificadores internos NO se exponen al cliente.
# - tampoco se devuelven JWT, hashes ni credenciales.
# =========================================================

@router.get("/me")
def obtener_mi_usuario(
    usuario=Depends(
        obtener_usuario_desde_token
    )
):
    """
    Devuelve el contexto mínimo y seguro del usuario autenticado.

    SEGURIDAD:
    - No expone contraseñas, hashes, JWT, JTI ni datos de sesión.
    - ADMIN_TI y ADMIN_SOPORTE conservan la respuesta administrativa
      que ya utiliza el frontend.
    - Los líderes reciben únicamente su propia compañía activa.
    - No se concede a los líderes acceso al endpoint /companias.
    - Se exige exactamente una compañía activa para una identidad líder.
    """

    # ---------------------------------------------------------
    # Roles efectivos obtenidos de la identidad autenticada.
    # ---------------------------------------------------------
    roles_usuario = set(
        usuario.get("roles", [])
    )

    roles_lider = {
        "LIDER_FACTURACION",
        "LIDER_LOGISTICA",
        "LIDER_GESTION_HUMANA",
    }

    # ---------------------------------------------------------
    # VIGENCIA SEGURA DE LA CONTRASEÑA DEFINITIVA
    # ---------------------------------------------------------
    # La interfaz necesita advertir al usuario durante los últimos
    # 8 días de vigencia. Consultamos únicamente la fecha de
    # expiración; nunca se consulta ni se devuelve password_hash.
    #
    # El backend conserva la fuente de verdad. React utilizará
    # estos metadatos exclusivamente para presentar el aviso.
    # ---------------------------------------------------------
    consulta_vigencia_password = text("""
        SELECT
            c.password_expira_en,
            EXISTS (
                SELECT 1
                FROM mfa_totp m
                WHERE m.usuario_id = :usuario_id
                  AND m.activo = TRUE
            ) AS mfa_activo
        FROM credenciales c
        WHERE c.usuario_id = :usuario_id
          AND c.activo = TRUE
        LIMIT 1
    """)

    with engine.connect() as conexion:
        vigencia_password = conexion.execute(
            consulta_vigencia_password,
            {"usuario_id": usuario["id"]}
        ).mappings().first()

    password_expira_en = (
        vigencia_password["password_expira_en"]
        if vigencia_password is not None
        else None
    )

    # Estado no sensible del segundo factor. El frontend utiliza
    # únicamente este booleano; nunca recibe el secreto TOTP.
    mfa_activo = bool(
        vigencia_password["mfa_activo"]
        if vigencia_password is not None
        else False
    )

    dias_para_expirar_password = None
    mostrar_aviso_password = False

    if (
        password_expira_en is not None
        and not usuario["requiere_cambio_password"]
    ):
        ahora = datetime.now(timezone.utc)
        segundos_restantes = (
            password_expira_en - ahora
        ).total_seconds()

        if segundos_restantes > 0:
            # Redondeo hacia arriba sin importar math.ceil: cualquier
            # fracción de día restante se presenta como un día completo.
            dias_para_expirar_password = int(
                (segundos_restantes + 86399) // 86400
            )
            mostrar_aviso_password = (
                dias_para_expirar_password <= 8
            )
        else:
            dias_para_expirar_password = 0

    # ---------------------------------------------------------
    # Respuesta base.
    # Mantiene exclusivamente información segura del usuario.
    # ---------------------------------------------------------
    respuesta = {
        "id": usuario["id"],
        "id_externo": usuario["id_externo"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "activo": usuario["activo"],
        "roles": usuario["roles"],
        "requiere_cambio_password":
            usuario["requiere_cambio_password"],

        # Metadatos no sensibles para el aviso preventivo de
        # expiración de contraseña en la interfaz.
        "password_expira_en": (
            password_expira_en.isoformat()
            if password_expira_en is not None
            else None
        ),
        "dias_para_expirar_password":
            dias_para_expirar_password,
        "mostrar_aviso_password":
            mostrar_aviso_password,

        # Estado seguro de MFA. No expone secreto, QR ni códigos.
        "mfa_activo": mfa_activo,
    }

    # ---------------------------------------------------------
    # CONTEXTO MULTITENANT PARA LÍDERES
    # ---------------------------------------------------------
    # Solo los roles organizacionales necesitan conocer su propia
    # compañía para ser direccionados a su plataforma.
    #
    # ADMIN_TI y ADMIN_SOPORTE continúan utilizando los endpoints
    # administrativos correspondientes.
    # ---------------------------------------------------------
    if roles_usuario.intersection(roles_lider):

        consulta_compania = text("""
            SELECT
                c.id,
                c.codigo,
                c.nombre
            FROM usuario_companias_plataforma uc
            JOIN companias c
                ON c.id = uc.compania_id
            WHERE uc.usuario_id = :usuario_id
              AND c.activo = TRUE
            ORDER BY c.id
            LIMIT 2
        """)

        with engine.connect() as conexion:
            companias_usuario = (
                conexion.execute(
                    consulta_compania,
                    {
                        "usuario_id": usuario["id"]
                    }
                )
                .mappings()
                .all()
            )

        # -----------------------------------------------------
        # Una identidad líder debe pertenecer exactamente a una
        # compañía activa.
        #
        # 0 compañías  -> configuración inválida.
        # >1 compañía  -> configuración ambigua.
        #
        # En ambos casos se evita seleccionar silenciosamente
        # una compañía incorrecta.
        # -----------------------------------------------------
        if len(companias_usuario) != 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "La identidad no tiene una asociación "
                    "de compañía válida"
                )
            )

        compania = companias_usuario[0]

        # -----------------------------------------------------
        # Solo exponemos los datos mínimos requeridos por React.
        # -----------------------------------------------------
        respuesta["compania"] = {
            "id": compania["id"],
            "codigo": compania["codigo"],
            "nombre": compania["nombre"],
        }

    return respuesta

# =========================================================
# FIN CODIGO autenticacion.py
