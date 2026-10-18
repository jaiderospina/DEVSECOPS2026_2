-- ============================================================
-- IAM SECURE
-- MFA / TOTP - Segundo factor de autenticación
-- ============================================================
--
-- OBJETIVO:
-- Crear la estructura persistente necesaria para implementar
-- autenticación multifactor mediante aplicaciones Authenticator
-- compatibles con el estándar TOTP.
--
-- SEGURIDAD:
--   1. Existe como máximo una configuración TOTP por usuario.
--   2. El secreto TOTP nunca se almacena en texto plano.
--   3. secreto_cifrado contendrá únicamente el secreto protegido
--      mediante cifrado realizado por Identity Service.
--   4. La clave utilizada para cifrar el secreto NO se almacena
--      en PostgreSQL; se obtiene mediante MFA_ENCRYPTION_KEY.
--   5. Los códigos TOTP de seis dígitos nunca se almacenan.
--   6. ultimo_contador_validado permitirá impedir la reutilización
--      de un código TOTP previamente aceptado.
--   7. El MFA no queda activo hasta completar correctamente
--      el proceso de enrolamiento y validación inicial.
--
-- La relación con usuarios_plataforma es 1:1.
-- ON DELETE CASCADE elimina la configuración MFA si la identidad
-- correspondiente es eliminada.
--
-- El script es idempotente y puede ejecutarse nuevamente sin
-- recrear la tabla ni los índices existentes.
-- ============================================================

CREATE TABLE IF NOT EXISTS mfa_totp (
    id SERIAL PRIMARY KEY,

    usuario_id INTEGER NOT NULL UNIQUE
        REFERENCES usuarios_plataforma(id)
        ON DELETE CASCADE,

    -- Secreto TOTP cifrado por Identity Service.
    -- Nunca debe contener el secreto TOTP en texto plano.
    secreto_cifrado TEXT NOT NULL,

    -- FALSE durante el enrolamiento.
    -- Solo cambia a TRUE después de validar el primer código TOTP.
    activo BOOLEAN NOT NULL DEFAULT FALSE,

    -- Contador temporal del último TOTP aceptado.
    -- Se utilizará para impedir reutilización de códigos.
    ultimo_contador_validado BIGINT NULL,

    fecha_enrolamiento TIMESTAMPTZ NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice adicional para consultas administrativas por estado MFA.
CREATE INDEX IF NOT EXISTS idx_mfa_totp_activo
    ON mfa_totp (activo);

COMMENT ON TABLE mfa_totp IS
    'Configuración MFA/TOTP cifrada asociada a usuarios de IAM Secure';

COMMENT ON COLUMN mfa_totp.secreto_cifrado IS
    'Secreto TOTP cifrado por Identity Service; nunca almacenar texto plano';

COMMENT ON COLUMN mfa_totp.ultimo_contador_validado IS
    'Último contador TOTP aceptado para protección contra reutilización';