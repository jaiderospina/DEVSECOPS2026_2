-- Permisos individuales por usuario y compañía. Sin concesiones automáticas.
CREATE TABLE IF NOT EXISTS permisos_usuario_compania (
    usuario_id INTEGER NOT NULL,
    compania_id INTEGER NOT NULL,
    codigo VARCHAR(80) NOT NULL,
    habilitado BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    modificado_por INTEGER REFERENCES usuarios_plataforma(id) ON DELETE SET NULL,
    fecha_modificacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (usuario_id, compania_id, codigo),
    FOREIGN KEY (usuario_id, compania_id)
        REFERENCES usuario_companias_plataforma(usuario_id, compania_id)
        ON DELETE CASCADE,
    CHECK (codigo IN (
        'facturacion.aprobaciones.consultar', 'facturacion.pagos.consultar',
        'facturacion.impuestos.consultar', 'logistica.despachos.consultar',
        'logistica.entregas.consultar', 'logistica.inventario.consultar',
        'gestion_humana.colaboradores.consultar', 'gestion_humana.novedades.consultar',
        'gestion_humana.vacaciones.consultar'
    ))
);
CREATE INDEX IF NOT EXISTS idx_permisos_compania
    ON permisos_usuario_compania(compania_id, usuario_id);

-- Adopción única de las vistas existentes. Reejecutar no reactiva permisos.
CREATE TABLE IF NOT EXISTS permisos_migraciones (
    nombre VARCHAR(80) PRIMARY KEY,
    aplicada_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
DO $$
BEGIN
    PERFORM pg_advisory_xact_lock(700511);
    IF NOT EXISTS (SELECT 1 FROM permisos_migraciones WHERE nombre = 'vistas_existentes_v1') THEN
        INSERT INTO permisos_usuario_compania (usuario_id, compania_id, codigo, habilitado)
        SELECT u.id, uc.compania_id, p.codigo, TRUE
        FROM usuarios_plataforma u
        JOIN usuario_companias_plataforma uc ON uc.usuario_id = u.id
        JOIN companias c ON c.id = uc.compania_id AND c.activo = TRUE
        JOIN usuario_roles_plataforma ur ON ur.usuario_id = u.id
        JOIN roles_plataforma r ON r.id = ur.rol_id AND r.activo = TRUE
        JOIN (VALUES
            ('LIDER_FACTURACION', 'facturacion.aprobaciones.consultar'),
            ('LIDER_FACTURACION', 'facturacion.pagos.consultar'),
            ('LIDER_FACTURACION', 'facturacion.impuestos.consultar'),
            ('LIDER_LOGISTICA', 'logistica.despachos.consultar'),
            ('LIDER_LOGISTICA', 'logistica.entregas.consultar'),
            ('LIDER_LOGISTICA', 'logistica.inventario.consultar'),
            ('LIDER_GESTION_HUMANA', 'gestion_humana.colaboradores.consultar'),
            ('LIDER_GESTION_HUMANA', 'gestion_humana.novedades.consultar'),
            ('LIDER_GESTION_HUMANA', 'gestion_humana.vacaciones.consultar')
        ) AS p(rol, codigo) ON p.rol = r.nombre
        WHERE u.activo = TRUE
          AND (SELECT COUNT(*) FROM usuario_companias_plataforma x
               JOIN companias cx ON cx.id = x.compania_id AND cx.activo = TRUE
               WHERE x.usuario_id = u.id) = 1
          AND (SELECT COUNT(*) FROM usuario_roles_plataforma xr
               JOIN roles_plataforma rr ON rr.id = xr.rol_id AND rr.activo = TRUE
               WHERE xr.usuario_id = u.id) = 1
        ON CONFLICT (usuario_id, compania_id, codigo) DO NOTHING;
        INSERT INTO permisos_migraciones(nombre) VALUES ('vistas_existentes_v1');
    END IF;
END $$;
