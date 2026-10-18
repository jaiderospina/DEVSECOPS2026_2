-- ============================================================
-- IAM SECURE - CREDENCIALES, ROLES Y ASIGNACIÓN DE ROLES
-- ============================================================
-- Este script crea y mantiene las estructuras utilizadas por
-- Identity Service para autenticación y autorización.
--
-- SEGURIDAD:
-- - PostgreSQL almacena únicamente hashes de contraseña.
-- - Las contraseñas temporales y definitivas tienen su fecha
--   de expiración administrada por el backend.
-- - El bloqueo por intentos fallidos se mantiene persistente.
-- - La recuperación pública dispone de cooldown persistente.
-- - Los permisos efectivos siempre se validan en backend.
-- ============================================================


-- ============================================================
-- TABLA: credenciales
-- ============================================================

CREATE TABLE IF NOT EXISTS credenciales (
    id SERIAL PRIMARY KEY,

    -- Relación uno a uno: cada usuario posee como máximo una
    -- credencial activa en este modelo.
    usuario_id INTEGER NOT NULL UNIQUE,

    -- Debe contener únicamente un hash seguro generado por la
    -- aplicación (actualmente Argon2), nunca texto plano.
    password_hash TEXT NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    -- TRUE obliga al usuario a cambiar su contraseña antes de
    -- acceder a las funciones normales de su rol.
    requiere_cambio_password BOOLEAN NOT NULL DEFAULT FALSE,

    -- Control de bloqueo por intentos consecutivos fallidos.
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado BOOLEAN NOT NULL DEFAULT FALSE,
    bloqueado_en TIMESTAMPTZ NULL,

    -- Vigencia de contraseña temporal. NULL significa que no
    -- existe una contraseña temporal pendiente.
    password_temporal_expira_en TIMESTAMPTZ NULL,

    -- Vigencia de la contraseña definitiva. El backend utiliza
    -- PASSWORD_EXPIRE_DAYS (60 días en la configuración académica).
    password_expira_en TIMESTAMPTZ NULL,

    -- Momento de la última recuperación pública completada.
    -- Permite aplicar el cooldown configurado por el backend.
    ultima_recuperacion_password_en TIMESTAMPTZ NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_credenciales_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios_plataforma(id)
        ON DELETE CASCADE,

    -- El contador nunca puede ser negativo.
    CONSTRAINT ck_credenciales_intentos_fallidos_no_negativo
        CHECK (intentos_fallidos >= 0),

    -- Evita almacenar accidentalmente un hash vacío.
    CONSTRAINT ck_credenciales_password_hash_no_vacio
        CHECK (BTRIM(password_hash) <> '')
);


-- ============================================================
-- MIGRACIÓN IDempotente DE COLUMNAS
-- ============================================================
-- CREATE TABLE IF NOT EXISTS no modifica una tabla existente.
-- Estos ALTER permiten reutilizar el script en una instalación
-- que ya tenga una versión anterior de "credenciales".
-- ============================================================

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS requiere_cambio_password
        BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS intentos_fallidos
        INTEGER NOT NULL DEFAULT 0;

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS bloqueado
        BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS bloqueado_en
        TIMESTAMPTZ NULL;

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS password_temporal_expira_en
        TIMESTAMPTZ NULL;

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS password_expira_en
        TIMESTAMPTZ NULL;

ALTER TABLE credenciales
    ADD COLUMN IF NOT EXISTS ultima_recuperacion_password_en
        TIMESTAMPTZ NULL;


-- ============================================================
-- RESTRICCIONES PARA INSTALACIONES EXISTENTES
-- ============================================================
-- PostgreSQL no dispone de ADD CONSTRAINT IF NOT EXISTS.
-- Se comprueba pg_constraint para que el bloque sea idempotente.
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_credenciales_intentos_fallidos_no_negativo'
          AND conrelid = 'credenciales'::regclass
    ) THEN
        ALTER TABLE credenciales
            ADD CONSTRAINT ck_credenciales_intentos_fallidos_no_negativo
            CHECK (intentos_fallidos >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_credenciales_password_hash_no_vacio'
          AND conrelid = 'credenciales'::regclass
    ) THEN
        ALTER TABLE credenciales
            ADD CONSTRAINT ck_credenciales_password_hash_no_vacio
            CHECK (BTRIM(password_hash) <> '');
    END IF;
END
$$;


-- ============================================================
-- ÍNDICE DE APOYO PARA RECUPERACIÓN/BLOQUEO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_credenciales_usuario_activo
    ON credenciales(usuario_id, activo);


-- ============================================================
-- TABLA: roles_plataforma
-- ============================================================

CREATE TABLE IF NOT EXISTS roles_plataforma (
    id SERIAL PRIMARY KEY,

    nombre VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255),
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_roles_plataforma_nombre_no_vacio
        CHECK (BTRIM(nombre) <> '')
);


-- ============================================================
-- UNICIDAD DE ROLES SIN DISTINGUIR MAYÚSCULAS/MINÚSCULAS
-- ============================================================
-- Los nombres definidos por IAM Secure se manejan en mayúsculas.
-- El índice funcional evita crear variantes del mismo rol.
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_plataforma_nombre_upper
    ON roles_plataforma (UPPER(BTRIM(nombre)));


-- ============================================================
-- TABLA: usuario_roles_plataforma
-- ============================================================

CREATE TABLE IF NOT EXISTS usuario_roles_plataforma (
    id SERIAL PRIMARY KEY,

    usuario_id INTEGER NOT NULL,
    rol_id INTEGER NOT NULL,

    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_usuario_roles_plataforma_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios_plataforma(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_usuario_roles_plataforma_rol
        FOREIGN KEY (rol_id)
        REFERENCES roles_plataforma(id)
        ON DELETE CASCADE,

    -- Evita asignar el mismo rol más de una vez.
    CONSTRAINT uq_usuario_rol_plataforma
        UNIQUE (usuario_id, rol_id)
);


-- ============================================================
-- ÍNDICES DE AUTORIZACIÓN
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_usuario_roles_usuario_id
    ON usuario_roles_plataforma(usuario_id);

CREATE INDEX IF NOT EXISTS idx_usuario_roles_rol_id
    ON usuario_roles_plataforma(rol_id);


-- ============================================================
-- ROLES VIGENTES DEL MODELO IAM SECURE
-- ============================================================
-- ADMIN_TI:
--   administración global de compañías y administradores soporte.
--
-- ADMIN_SOPORTE:
--   administración limitada a compañías expresamente asignadas.
--
-- LIDER_FACTURACION / LIDER_LOGISTICA /
-- LIDER_GESTION_HUMANA:
--   usuarios finales de los portales académicos correspondientes.
-- ============================================================

INSERT INTO roles_plataforma (
    nombre,
    descripcion
)
VALUES
    (
        'ADMIN_TI',
        'Coordinador TI - administración global de empresas y usuarios de soporte'
    ),
    (
        'ADMIN_SOPORTE',
        'Soporte TI - administración de usuarios de las empresas asignadas'
    ),
    (
        'LIDER_FACTURACION',
        'Líder de Facturación - acceso al portal académico de facturación'
    ),
    (
        'LIDER_LOGISTICA',
        'Líder de Logística - acceso al portal académico de logística'
    ),
    (
        'LIDER_GESTION_HUMANA',
        'Líder de Gestión Humana - acceso al portal académico de gestión humana'
    )
ON CONFLICT DO NOTHING;
