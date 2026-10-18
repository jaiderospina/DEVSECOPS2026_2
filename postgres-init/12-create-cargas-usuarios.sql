-- Cargas Excel: datos administrativos y resultados, nunca contraseñas ni tokens.
CREATE TABLE IF NOT EXISTS cargas_usuarios (
    id UUID PRIMARY KEY,
    actor_usuario_id INTEGER NOT NULL REFERENCES usuarios_plataforma(id) ON DELETE CASCADE,
    compania_id INTEGER NOT NULL REFERENCES companias(id) ON DELETE CASCADE,
    estado VARCHAR(16) NOT NULL DEFAULT 'VALIDADA' CHECK (estado IN ('VALIDADA', 'CONFIRMADA')),
    creada_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmar_antes TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 minutes',
    conservar_hasta TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days'
);
CREATE INDEX IF NOT EXISTS idx_cargas_usuarios_actor_compania
    ON cargas_usuarios(actor_usuario_id, compania_id, creada_en DESC);
CREATE TABLE IF NOT EXISTS cargas_usuario_filas (
    carga_id UUID NOT NULL REFERENCES cargas_usuarios(id) ON DELETE CASCADE,
    fila INTEGER NOT NULL CHECK (fila BETWEEN 2 AND 501),
    datos JSONB NOT NULL CHECK (jsonb_typeof(datos) = 'object'),
    estado VARCHAR(16) NOT NULL CHECK (estado IN ('INVALIDA', 'PENDIENTE', 'CREADA', 'ERROR')),
    codigo VARCHAR(48) NOT NULL,
    mensaje VARCHAR(400) NOT NULL,
    usuario_id INTEGER REFERENCES usuarios_plataforma(id) ON DELETE SET NULL,
    procesada_en TIMESTAMPTZ,
    PRIMARY KEY (carga_id, fila)
);
