-- ============================================================
-- IAM SECURE - COMPAÑÍAS Y ASIGNACIÓN MULTITENANT
-- ============================================================
-- Este script crea la estructura utilizada por Identity Service
-- para representar compañías y las relaciones de usuarios con
-- cada tenant.
--
-- MODELO:
-- - ADMIN_TI administra compañías y asignaciones de soporte.
-- - ADMIN_SOPORTE solo administra compañías expresamente
--   asignadas por ADMIN_TI.
-- - Los roles LIDER_* permanecen asociados a su propia compañía.
--
-- IMPORTANTE:
-- La tabla usuario_companias_plataforma es compartida por
-- ADMIN_SOPORTE y LIDER_*.
--
-- Por esta razón NO debe existir una restricción UNIQUE global
-- sobre compania_id: una compañía puede estar relacionada con
-- su administrador de soporte y, simultáneamente, con varios
-- líderes internos.
--
-- La regla de "máximo un ADMIN_SOPORTE por compañía" se aplica
-- en el backend, teniendo en cuenta el rol del usuario.
-- ============================================================


-- ============================================================
-- TABLA: companias
-- ============================================================

CREATE TABLE IF NOT EXISTS companias (
    id SERIAL PRIMARY KEY,

    -- Código organizacional de la compañía.
    codigo VARCHAR(50) NOT NULL,

    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(255),

    -- Permite deshabilitar el tenant conservando sus relaciones.
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_companias_codigo_no_vacio
        CHECK (BTRIM(codigo) <> ''),

    CONSTRAINT ck_companias_nombre_no_vacio
        CHECK (BTRIM(nombre) <> '')
);


-- ============================================================
-- UNICIDAD NORMALIZADA DEL CÓDIGO
-- ============================================================
-- El backend normaliza los códigos a mayúsculas. Este índice
-- protege también la base de datos frente a variantes como
-- "ANDINA", "andina" o valores con espacios exteriores.
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_companias_codigo_normalizado
    ON companias (UPPER(BTRIM(codigo)));


-- ============================================================
-- TABLA: usuario_companias_plataforma
-- ============================================================
-- Relación muchos-a-muchos compartida por administradores de
-- soporte y líderes internos.
-- ============================================================

CREATE TABLE IF NOT EXISTS usuario_companias_plataforma (
    id SERIAL PRIMARY KEY,

    usuario_id INTEGER NOT NULL,
    compania_id INTEGER NOT NULL,

    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_usuario_companias_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios_plataforma(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_usuario_companias_compania
        FOREIGN KEY (compania_id)
        REFERENCES companias(id)
        ON DELETE CASCADE,

    -- Evita repetir exactamente la misma relación.
    CONSTRAINT uq_usuario_compania
        UNIQUE (usuario_id, compania_id)
);


-- ============================================================
-- ÍNDICES PARA AUTORIZACIÓN MULTITENANT
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_usuario_companias_usuario_id
    ON usuario_companias_plataforma(usuario_id);

CREATE INDEX IF NOT EXISTS idx_usuario_companias_compania_id
    ON usuario_companias_plataforma(compania_id);


-- ============================================================
-- COMPAÑÍAS INICIALES DEL EJERCICIO ACADÉMICO
-- ============================================================
-- La inserción utiliza el código normalizado como referencia.
-- El WHERE NOT EXISTS mantiene el bloque idempotente incluso
-- cuando una instalación anterior contiene el código con otra
-- combinación de mayúsculas/minúsculas.
-- ============================================================

INSERT INTO companias (
    codigo,
    nombre,
    descripcion
)
SELECT
    valores.codigo,
    valores.nombre,
    valores.descripcion
FROM (
    VALUES
        (
            'ANDINA',
            'ANDINA SAS',
            'Compañía académica ANDINA'
        ),
        (
            'PACIFICO',
            'PACIFICO SAS',
            'Compañía académica PACIFICO'
        ),
        (
            'CARIBE',
            'CARIBE SAS',
            'Compañía académica CARIBE'
        )
) AS valores(codigo, nombre, descripcion)
WHERE NOT EXISTS (
    SELECT 1
    FROM companias c
    WHERE UPPER(BTRIM(c.codigo)) = valores.codigo
);
