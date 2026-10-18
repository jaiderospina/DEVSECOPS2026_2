-- ============================================================
-- IAM SECURE - TABLA DE USUARIOS DE PLATAFORMA
-- ============================================================
-- Almacena la información básica de las identidades gestionadas
-- por Identity Service.
--
-- SEGURIDAD Y DISEÑO:
-- 1. "id" es la PK interna usada por las relaciones del sistema.
-- 2. "id_externo" es el identificador organizacional/académico.
-- 3. El correo electrónico es el nombre de usuario de autenticación.
-- 4. Las contraseñas NO se almacenan en esta tabla.
--    La tabla "credenciales" conserva únicamente hashes seguros.
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios_plataforma (
    id SERIAL PRIMARY KEY,

    -- Identificador externo independiente de la PK interna.
    -- Se permite NULL para compatibilidad con registros históricos.
    id_externo VARCHAR(50),

    nombre VARCHAR(100) NOT NULL,

    -- Identificador utilizado durante la autenticación.
    email VARCHAR(150) NOT NULL,

    -- Desactivación lógica de la identidad.
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Evita cadenas vacías o compuestas únicamente por espacios.
    CONSTRAINT ck_usuarios_plataforma_nombre_no_vacio
        CHECK (BTRIM(nombre) <> ''),

    CONSTRAINT ck_usuarios_plataforma_email_no_vacio
        CHECK (BTRIM(email) <> ''),

    CONSTRAINT ck_usuarios_plataforma_id_externo_no_vacio
        CHECK (
            id_externo IS NULL
            OR BTRIM(id_externo) <> ''
        )
);


-- ============================================================
-- UNICIDAD DEL CORREO ELECTRÓNICO
-- ============================================================
-- PostgreSQL distingue mayúsculas/minúsculas en un UNIQUE normal.
-- Como Identity Service autentica el correo sin distinguir el caso,
-- el índice funcional evita registrar, por ejemplo:
-- usuario@empresa.com y Usuario@Empresa.com como cuentas distintas.
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_plataforma_email_lower
ON usuarios_plataforma (LOWER(BTRIM(email)));


-- ============================================================
-- INTEGRIDAD DEL IDENTIFICADOR EXTERNO
-- ============================================================
-- El índice parcial permite NULL para registros históricos, pero
-- impide repetir cualquier identificador externo informado.
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_plataforma_id_externo
ON usuarios_plataforma (BTRIM(id_externo))
WHERE id_externo IS NOT NULL;
