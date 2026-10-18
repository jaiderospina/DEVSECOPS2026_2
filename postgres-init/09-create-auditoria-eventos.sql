-- ============================================================
-- IAM SECURE - AUDITORÍA PERSISTENTE
-- Audit Service
-- ============================================================
--
-- Esta tabla almacena eventos estructurados de seguridad,
-- autenticación y administración generados por los servicios
-- de IAM Secure.
--
-- PRINCIPIOS:
-- - Append-only: los eventos no se modifican ni eliminan.
-- - Cada evento posee un UUID único para soportar idempotencia.
-- - Los identificadores históricos se conservan aunque una
--   identidad o compañía sea eliminada posteriormente.
-- - El detalle se almacena como JSONB y debe haber sido
--   sanitizado antes de su persistencia.
--
-- SEGURIDAD:
-- - No almacenar contraseñas.
-- - No almacenar hashes.
-- - No almacenar JWT/JTI.
-- - No almacenar secretos MFA/TOTP.
-- - No almacenar QR/otpauth.
-- - No almacenar credenciales SMTP o de base de datos.
-- ============================================================


CREATE TABLE IF NOT EXISTS auditoria_eventos (

    -- --------------------------------------------------------
    -- IDENTIFICADOR INTERNO
    -- --------------------------------------------------------

    id BIGSERIAL PRIMARY KEY,

    -- --------------------------------------------------------
    -- IDENTIFICADOR GLOBAL DEL EVENTO
    -- --------------------------------------------------------
    --
    -- Es generado por el productor del evento.
    --
    -- La restricción UNIQUE permite que Identity Service pueda
    -- reintentar un envío sin insertar dos veces el mismo evento.
    -- --------------------------------------------------------

    evento_uuid UUID NOT NULL,

    -- --------------------------------------------------------
    -- FECHA DEL EVENTO
    -- --------------------------------------------------------
    --
    -- Momento UTC en que ocurrió la acción en el servicio de
    -- origen.
    -- --------------------------------------------------------

    fecha_evento TIMESTAMPTZ NOT NULL,

    -- Momento en que Audit Service recibió y persistió el evento.
    fecha_recepcion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- --------------------------------------------------------
    -- SERVICIO DE ORIGEN
    -- --------------------------------------------------------

    servicio VARCHAR(100) NOT NULL,

    -- --------------------------------------------------------
    -- TIPO DE EVENTO
    -- --------------------------------------------------------
    --
    -- Ejemplos:
    -- LOGIN_EXITOSO
    -- LOGIN_FALLIDO
    -- USUARIO_CREADO
    -- MFA_ACTIVADO
    -- COMPANIA_ASIGNADA
    -- --------------------------------------------------------

    evento VARCHAR(100) NOT NULL,

    -- --------------------------------------------------------
    -- RESULTADO
    -- --------------------------------------------------------
    --
    -- Se mantiene extensible para no acoplar la base de datos
    -- a un conjunto rígido de resultados.
    -- --------------------------------------------------------

    resultado VARCHAR(50) NOT NULL,

    -- --------------------------------------------------------
    -- ACTOR
    -- --------------------------------------------------------
    --
    -- Identidad que originó la acción.
    --
    -- No se utiliza FK intencionalmente. La auditoría debe
    -- conservar el identificador histórico incluso si en el
    -- futuro el usuario deja de existir.
    -- --------------------------------------------------------

    actor_usuario_id INTEGER,

    -- --------------------------------------------------------
    -- IDENTIDAD OBJETIVO
    -- --------------------------------------------------------

    objetivo_usuario_id INTEGER,

    -- --------------------------------------------------------
    -- COMPAÑÍA / TENANT RELACIONADO
    -- --------------------------------------------------------

    compania_id INTEGER,

    -- --------------------------------------------------------
    -- DETALLE ESTRUCTURADO
    -- --------------------------------------------------------
    --
    -- Únicamente información no sensible previamente sanitizada.
    -- --------------------------------------------------------

    detalle JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- ========================================================
    -- RESTRICCIONES
    -- ========================================================

    CONSTRAINT uq_auditoria_eventos_uuid
        UNIQUE (evento_uuid),

    CONSTRAINT ck_auditoria_servicio_no_vacio
        CHECK (
            BTRIM(servicio) <> ''
        ),

    CONSTRAINT ck_auditoria_evento_no_vacio
        CHECK (
            BTRIM(evento) <> ''
        ),

    CONSTRAINT ck_auditoria_resultado_no_vacio
        CHECK (
            BTRIM(resultado) <> ''
        ),

    CONSTRAINT ck_auditoria_detalle_objeto
        CHECK (
            jsonb_typeof(detalle) = 'object'
        )
);


-- ============================================================
-- ÍNDICE CRONOLÓGICO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_fecha_evento
    ON auditoria_eventos(fecha_evento DESC);


-- ============================================================
-- ÍNDICE POR TIPO DE EVENTO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_evento_fecha
    ON auditoria_eventos(
        evento,
        fecha_evento DESC
    );


-- ============================================================
-- ÍNDICE POR SERVICIO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_servicio_fecha
    ON auditoria_eventos(
        servicio,
        fecha_evento DESC
    );


-- ============================================================
-- ÍNDICE POR ACTOR
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_actor_fecha
    ON auditoria_eventos(
        actor_usuario_id,
        fecha_evento DESC
    )
    WHERE actor_usuario_id IS NOT NULL;


-- ============================================================
-- ÍNDICE POR USUARIO OBJETIVO
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_objetivo_fecha
    ON auditoria_eventos(
        objetivo_usuario_id,
        fecha_evento DESC
    )
    WHERE objetivo_usuario_id IS NOT NULL;


-- ============================================================
-- ÍNDICE POR COMPAÑÍA
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_auditoria_compania_fecha
    ON auditoria_eventos(
        compania_id,
        fecha_evento DESC
    )
    WHERE compania_id IS NOT NULL;


-- ============================================================
-- PROTECCIÓN APPEND-ONLY
-- ============================================================
--
-- El Audit Service únicamente debe insertar eventos.
--
-- UPDATE y DELETE quedan bloqueados a nivel de PostgreSQL,
-- proporcionando una segunda capa de protección además de no
-- implementar endpoints de modificación o eliminación.
--
-- Una futura política formal de retención deberá utilizar un
-- procedimiento administrativo controlado y separado.
-- ============================================================

CREATE OR REPLACE FUNCTION fn_auditoria_bloquear_modificacion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Los eventos de auditoría son inmutables';
END;
$$;


DROP TRIGGER IF EXISTS trg_auditoria_solo_insercion
ON auditoria_eventos;


CREATE TRIGGER trg_auditoria_solo_insercion
BEFORE UPDATE OR DELETE
ON auditoria_eventos
FOR EACH ROW
EXECUTE FUNCTION fn_auditoria_bloquear_modificacion();
