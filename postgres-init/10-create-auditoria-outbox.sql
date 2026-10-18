-- ============================================================
-- IAM SECURE - AUDITORIA OUTBOX
-- ============================================================
--
-- Cola persistente utilizada para entregar eventos desde los
-- servicios productores hacia Audit Service.
--
-- SEGURIDAD:
-- - solo deben almacenarse eventos previamente sanitizados;
-- - nunca almacenar passwords, hashes, JWT/JTI, TOTP,
--   secretos MFA, QR, tokens internos ni credenciales;
-- - evento_uuid permite entrega idempotente al Audit Service.
--
-- La tabla es operacional y, a diferencia de auditoria_eventos,
-- sus registros sí cambian de estado mientras son procesados.
-- ============================================================


CREATE TABLE IF NOT EXISTS auditoria_outbox (

    id BIGSERIAL PRIMARY KEY,

    -- --------------------------------------------------------
    -- IDENTIFICADOR IDEMPOTENTE
    -- --------------------------------------------------------

    evento_uuid UUID NOT NULL UNIQUE,


    -- --------------------------------------------------------
    -- EVENTO
    -- --------------------------------------------------------

    fecha_evento TIMESTAMPTZ NOT NULL,

    servicio VARCHAR(100) NOT NULL,

    evento VARCHAR(100) NOT NULL,

    resultado VARCHAR(50) NOT NULL,

    actor_usuario_id INTEGER,

    objetivo_usuario_id INTEGER,

    compania_id INTEGER,

    detalle JSONB NOT NULL
        DEFAULT '{}'::jsonb,


    -- --------------------------------------------------------
    -- ESTADO DE ENTREGA
    -- --------------------------------------------------------

    estado VARCHAR(20) NOT NULL
        DEFAULT 'PENDIENTE',

    intentos INTEGER NOT NULL
        DEFAULT 0,

    disponible_desde TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    worker_id VARCHAR(150),

    ultimo_error VARCHAR(500),


    -- --------------------------------------------------------
    -- CONTROL TEMPORAL
    -- --------------------------------------------------------

    creado_en TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    actualizado_en TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    procesando_desde TIMESTAMPTZ,

    completado_en TIMESTAMPTZ,


    -- --------------------------------------------------------
    -- RESTRICCIONES
    -- --------------------------------------------------------

    CONSTRAINT chk_auditoria_outbox_estado
        CHECK (
            estado IN (
                'PENDIENTE',
                'PROCESANDO',
                'COMPLETADO',
                'FALLIDO'
            )
        ),

    CONSTRAINT chk_auditoria_outbox_intentos
        CHECK (
            intentos >= 0
        ),

    CONSTRAINT chk_auditoria_outbox_servicio
        CHECK (
            LENGTH(TRIM(servicio)) > 0
        ),

    CONSTRAINT chk_auditoria_outbox_evento
        CHECK (
            LENGTH(TRIM(evento)) > 0
        ),

    CONSTRAINT chk_auditoria_outbox_resultado
        CHECK (
            LENGTH(TRIM(resultado)) > 0
        ),

    CONSTRAINT chk_auditoria_outbox_detalle
        CHECK (
            jsonb_typeof(detalle) = 'object'
        )
);


-- ============================================================
-- ÍNDICES DE PROCESAMIENTO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_outbox_pendientes
ON auditoria_outbox (
    disponible_desde,
    id
)
WHERE estado = 'PENDIENTE';


CREATE INDEX IF NOT EXISTS idx_auditoria_outbox_procesando
ON auditoria_outbox (
    procesando_desde
)
WHERE estado = 'PROCESANDO';


CREATE INDEX IF NOT EXISTS idx_auditoria_outbox_estado_fecha
ON auditoria_outbox (
    estado,
    creado_en DESC
);


CREATE INDEX IF NOT EXISTS idx_auditoria_outbox_evento_fecha
ON auditoria_outbox (
    evento,
    fecha_evento DESC
);
