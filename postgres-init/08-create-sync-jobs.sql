-- ============================================================
-- IAM SECURE - COLA DE TRABAJOS ASÍNCRONOS
-- Sync Worker / Sync Service
-- ============================================================
--
-- Esta tabla representa la cola persistente utilizada por el
-- proceso asíncrono encargado de aprovisionamiento y
-- sincronización.
--
-- OPERACIONES SOPORTADAS:
-- - PROVISIONAR
-- - MODIFICAR
-- - DESHABILITAR
-- - REVOCAR
--
-- ESTADOS:
-- - PENDIENTE
-- - PROCESANDO
-- - COMPLETADO
-- - FALLIDO
--
-- SEGURIDAD:
-- - No almacena contraseñas.
-- - No almacena hashes.
-- - No almacena JWT/JTI.
-- - No almacena secretos MFA/TOTP.
-- - No almacena credenciales SMTP.
--
-- El worker tomará los trabajos utilizando:
--
--     FOR UPDATE SKIP LOCKED
--
-- Esto permite ejecutar más de una instancia del worker sin
-- procesar simultáneamente el mismo trabajo.
-- ============================================================


CREATE TABLE IF NOT EXISTS sync_jobs (

    id BIGSERIAL PRIMARY KEY,

    -- --------------------------------------------------------
    -- TIPO DE OPERACIÓN
    -- --------------------------------------------------------
    operacion VARCHAR(30) NOT NULL,

    -- --------------------------------------------------------
    -- ESTADO DEL TRABAJO
    -- --------------------------------------------------------
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',

    -- --------------------------------------------------------
    -- IDENTIDAD OBJETIVO
    -- --------------------------------------------------------
    --
    -- SET NULL permite conservar el historial del trabajo en
    -- caso de que una identidad sea eliminada físicamente en
    -- algún escenario futuro.
    -- --------------------------------------------------------
    usuario_id INTEGER,

    -- --------------------------------------------------------
    -- COMPAÑÍA / TENANT OBJETIVO
    -- --------------------------------------------------------
    compania_id INTEGER,

    -- --------------------------------------------------------
    -- USUARIO QUE SOLICITÓ LA OPERACIÓN
    -- --------------------------------------------------------
    solicitado_por_usuario_id INTEGER,

    -- --------------------------------------------------------
    -- CONTROL DE REINTENTOS
    -- --------------------------------------------------------
    intentos INTEGER NOT NULL DEFAULT 0,

    max_intentos INTEGER NOT NULL DEFAULT 3,

    -- Permite retrasar un reintento sin bloquear el worker.
    disponible_desde TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- --------------------------------------------------------
    -- IDENTIFICACIÓN DEL WORKER
    -- --------------------------------------------------------
    --
    -- Ejemplo:
    -- sync-worker-1
    --
    -- No contiene credenciales ni identificadores sensibles.
    -- --------------------------------------------------------
    worker_id VARCHAR(100),

    -- --------------------------------------------------------
    -- RESULTADO SEGURO
    -- --------------------------------------------------------
    --
    -- Solo debe almacenar mensajes operativos no sensibles.
    -- Nunca contraseñas, tokens, hashes o secretos.
    -- --------------------------------------------------------
    resultado VARCHAR(500),

    -- --------------------------------------------------------
    -- ÚLTIMO ERROR
    -- --------------------------------------------------------
    --
    -- El worker debe sanitizar el mensaje antes de almacenarlo.
    -- --------------------------------------------------------
    ultimo_error VARCHAR(1000),

    -- --------------------------------------------------------
    -- FECHAS
    -- --------------------------------------------------------
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    fecha_inicio TIMESTAMPTZ,

    fecha_fin TIMESTAMPTZ,

    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- ========================================================
    -- CLAVES FORÁNEAS
    -- ========================================================

    CONSTRAINT fk_sync_jobs_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios_plataforma(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_sync_jobs_compania
        FOREIGN KEY (compania_id)
        REFERENCES companias(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_sync_jobs_solicitado_por
        FOREIGN KEY (solicitado_por_usuario_id)
        REFERENCES usuarios_plataforma(id)
        ON DELETE SET NULL,

    -- ========================================================
    -- VALIDACIONES
    -- ========================================================

    CONSTRAINT ck_sync_jobs_operacion
        CHECK (
            operacion IN (
                'PROVISIONAR',
                'MODIFICAR',
                'DESHABILITAR',
                'REVOCAR'
            )
        ),

    CONSTRAINT ck_sync_jobs_estado
        CHECK (
            estado IN (
                'PENDIENTE',
                'PROCESANDO',
                'COMPLETADO',
                'FALLIDO'
            )
        ),

    CONSTRAINT ck_sync_jobs_intentos
        CHECK (
            intentos >= 0
        ),

    CONSTRAINT ck_sync_jobs_max_intentos
        CHECK (
            max_intentos > 0
        ),

    CONSTRAINT ck_sync_jobs_intentos_maximos
        CHECK (
            intentos <= max_intentos
        ),

    CONSTRAINT ck_sync_jobs_worker_no_vacio
        CHECK (
            worker_id IS NULL
            OR BTRIM(worker_id) <> ''
        )
);


-- ============================================================
-- ÍNDICE PARA BUSCAR TRABAJOS DISPONIBLES
-- ============================================================
--
-- Este será el índice principal utilizado por el worker para
-- localizar trabajos pendientes de forma eficiente.
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sync_jobs_pendientes
    ON sync_jobs (
        disponible_desde,
        id
    )
    WHERE estado = 'PENDIENTE';


-- ============================================================
-- ÍNDICE POR USUARIO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sync_jobs_usuario_id
    ON sync_jobs(usuario_id);


-- ============================================================
-- ÍNDICE POR COMPAÑÍA
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sync_jobs_compania_id
    ON sync_jobs(compania_id);


-- ============================================================
-- ÍNDICE POR ESTADO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sync_jobs_estado
    ON sync_jobs(estado);


-- ============================================================
-- ÍNDICE PARA OBSERVABILIDAD / HISTÓRICO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sync_jobs_fecha_creacion
    ON sync_jobs(fecha_creacion DESC);