-- ============================================================
-- IAM SECURE - SESIONES PERSISTENTES
-- ============================================================
-- Este script crea y mantiene la tabla utilizada para asociar
-- cada JWT emitido con una sesión persistente en PostgreSQL.
--
-- SEGURIDAD:
-- - jti identifica de forma única la sesión asociada al JWT.
-- - fecha_expiracion controla la expiración absoluta.
-- - ultima_actividad permite aplicar el cierre por inactividad.
-- - revocada/fecha_revocacion permiten invalidación inmediata.
--
-- La duración máxima de inactividad NO se almacena en esta tabla.
-- El backend la obtiene de SESSION_INACTIVITY_MINUTES.
-- Configuración académica actual: 15 minutos.
-- ============================================================


CREATE TABLE IF NOT EXISTS sesiones (
    id SERIAL PRIMARY KEY,

    -- Usuario propietario de la sesión.
    usuario_id INTEGER NOT NULL,

    -- Identificador único generado para el JWT.
    -- No debe exponerse innecesariamente mediante las APIs.
    jti VARCHAR(255) NOT NULL UNIQUE,

    -- Inicio de la sesión.
    fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Última actividad autenticada aceptada por el backend.
    ultima_actividad TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Expiración absoluta de la sesión/JWT.
    fecha_expiracion TIMESTAMPTZ NOT NULL,

    -- Revocación persistente e inmediata.
    revocada BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_revocacion TIMESTAMPTZ NULL,

    CONSTRAINT fk_sesiones_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios_plataforma(id)
        ON DELETE CASCADE,

    -- Una sesión no puede expirar antes de comenzar.
    CONSTRAINT ck_sesiones_expiracion_valida
        CHECK (fecha_expiracion >= fecha_inicio),

    -- Mantiene coherencia entre el indicador y la fecha de
    -- revocación. Una sesión revocada debe registrar cuándo
    -- ocurrió la revocación.
    CONSTRAINT ck_sesiones_revocacion_coherente
        CHECK (
            (revocada = FALSE AND fecha_revocacion IS NULL)
            OR
            (revocada = TRUE AND fecha_revocacion IS NOT NULL)
        ),

    -- Evita almacenar accidentalmente un JTI vacío.
    CONSTRAINT ck_sesiones_jti_no_vacio
        CHECK (BTRIM(jti) <> '')
);


-- ============================================================
-- COMPATIBILIDAD CON INSTALACIONES EXISTENTES
-- ============================================================
-- CREATE TABLE IF NOT EXISTS no modifica tablas existentes.
-- Los ALTER siguientes incorporan los campos necesarios en
-- esquemas creados con versiones anteriores del proyecto.
-- ============================================================

ALTER TABLE sesiones
    ADD COLUMN IF NOT EXISTS ultima_actividad
        TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE sesiones
    ADD COLUMN IF NOT EXISTS revocada
        BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE sesiones
    ADD COLUMN IF NOT EXISTS fecha_revocacion
        TIMESTAMPTZ NULL;


-- ============================================================
-- RESTRICCIONES PARA INSTALACIONES EXISTENTES
-- ============================================================
-- PostgreSQL no dispone de ADD CONSTRAINT IF NOT EXISTS.
-- Se consulta pg_constraint para mantener este bloque idempotente.
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_sesiones_expiracion_valida'
          AND conrelid = 'sesiones'::regclass
    ) THEN
        ALTER TABLE sesiones
            ADD CONSTRAINT ck_sesiones_expiracion_valida
            CHECK (fecha_expiracion >= fecha_inicio);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_sesiones_revocacion_coherente'
          AND conrelid = 'sesiones'::regclass
    ) THEN
        ALTER TABLE sesiones
            ADD CONSTRAINT ck_sesiones_revocacion_coherente
            CHECK (
                (revocada = FALSE AND fecha_revocacion IS NULL)
                OR
                (revocada = TRUE AND fecha_revocacion IS NOT NULL)
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_sesiones_jti_no_vacio'
          AND conrelid = 'sesiones'::regclass
    ) THEN
        ALTER TABLE sesiones
            ADD CONSTRAINT ck_sesiones_jti_no_vacio
            CHECK (BTRIM(jti) <> '');
    END IF;
END
$$;


-- ============================================================
-- ÍNDICES
-- ============================================================
-- La restricción UNIQUE de jti ya crea su propio índice único,
-- por lo que no se crea un segundo índice redundante para jti.
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sesiones_usuario_id
    ON sesiones(usuario_id);

-- Optimiza consultas frecuentes de sesiones activas por usuario.
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario_activas
    ON sesiones(usuario_id, fecha_expiracion)
    WHERE revocada = FALSE;

-- Apoya tareas de limpieza de sesiones expiradas.
CREATE INDEX IF NOT EXISTS idx_sesiones_fecha_expiracion
    ON sesiones(fecha_expiracion);

-- Apoya el control y diagnóstico de inactividad.
CREATE INDEX IF NOT EXISTS idx_sesiones_ultima_actividad
    ON sesiones(ultima_actividad)
    WHERE revocada = FALSE;
