-- =========================================================
-- IAM Secure - MFA/TOTP
-- 07-create-mfa-desafios.sql
--
-- Desafíos de segundo factor previos a la creación de una
-- sesión autenticada definitiva.
--
-- SEGURIDAD:
-- - No almacena JWT, contraseña, secreto TOTP ni código OTP.
-- - El identificador del desafío es aleatorio y se persiste
--   únicamente como hash SHA-256.
-- - Cada desafío es de un solo uso y tiene expiración corta.
-- - Los intentos se contabilizan en PostgreSQL.
-- =========================================================

CREATE TABLE IF NOT EXISTS public.mfa_desafios (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL
        REFERENCES public.usuarios_plataforma(id)
        ON DELETE CASCADE,

    desafio_hash VARCHAR(64) NOT NULL UNIQUE,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_expiracion TIMESTAMPTZ NOT NULL,

    usado BOOLEAN NOT NULL DEFAULT FALSE,
    usado_en TIMESTAMPTZ NULL,

    intentos INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT ck_mfa_desafios_intentos_no_negativos
        CHECK (intentos >= 0)
);

CREATE INDEX IF NOT EXISTS idx_mfa_desafios_usuario
    ON public.mfa_desafios (usuario_id);

CREATE INDEX IF NOT EXISTS idx_mfa_desafios_expiracion
    ON public.mfa_desafios (fecha_expiracion);

CREATE INDEX IF NOT EXISTS idx_mfa_desafios_pendientes
    ON public.mfa_desafios (usuario_id, fecha_expiracion)
    WHERE usado = FALSE;

COMMENT ON TABLE public.mfa_desafios IS
    'Desafíos MFA de un solo uso previos a emitir una sesión/JWT definitivo.';

COMMENT ON COLUMN public.mfa_desafios.desafio_hash IS
    'SHA-256 del identificador aleatorio entregado temporalmente al cliente.';

COMMENT ON COLUMN public.mfa_desafios.intentos IS
    'Cantidad de verificaciones TOTP fallidas asociadas al desafío.';
