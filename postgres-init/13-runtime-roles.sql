-- T04/T07/T14: runtime roles are neither owners nor administrators.
-- No passwords in migrations. Enable LOGIN separately with private credentials.
BEGIN;
DO $$
DECLARE role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'iam_identity', 'iam_permissions', 'iam_sync', 'iam_audit',
        'iam_dispatcher', 'iam_backup'
    ] LOOP
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', role_name);
        END IF;
        EXECUTE format('ALTER ROLE %I NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS', role_name);
        EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', role_name);
        EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', role_name);
        EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), role_name);
    END LOOP;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO iam_identity, iam_permissions, iam_sync,
    iam_audit, iam_dispatcher, iam_backup;

-- Identity owns application operations, not schema, grants, or delivery state.
GRANT SELECT, INSERT, UPDATE, DELETE ON
    usuarios_plataforma, credenciales, usuario_roles_plataforma, companias,
    usuario_companias_plataforma, mfa_totp, mfa_desafios, sesiones,
    permisos_usuario_compania, cargas_usuarios, cargas_usuario_filas TO iam_identity;
GRANT SELECT ON roles_plataforma, auditoria_eventos TO iam_identity;
GRANT SELECT, INSERT ON sync_jobs TO iam_identity;
GRANT SELECT (id, evento_uuid) ON auditoria_outbox TO iam_identity;
GRANT INSERT (evento_uuid, fecha_evento, servicio, evento, resultado,
    actor_usuario_id, objetivo_usuario_id, compania_id, detalle) ON auditoria_outbox TO iam_identity;
GRANT USAGE, SELECT ON SEQUENCE usuarios_plataforma_id_seq, credenciales_id_seq,
    usuario_roles_plataforma_id_seq, usuario_companias_plataforma_id_seq,
    companias_id_seq, sesiones_id_seq, mfa_totp_id_seq,
    mfa_desafios_id_seq, sync_jobs_id_seq, auditoria_outbox_id_seq TO iam_identity;

-- Permissions must not receive write access to identities to acquire row locks.
-- Fixed, narrow functions retain existing transaction locks without granting
-- UPDATE on identity/tenant/role data. Qualified objects and fixed search_path
-- prevent function/search-path substitution; the runtime role is not the owner.
CREATE OR REPLACE FUNCTION public.iam_lock_active_user(uid integer)
RETURNS TABLE(id integer, nombre varchar, email varchar)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
    SELECT u.id, u.nombre, u.email FROM public.usuarios_plataforma u
    WHERE u.id=uid AND u.activo=TRUE FOR UPDATE OF u;
$$;
CREATE OR REPLACE FUNCTION public.iam_lock_memberships(uid integer, cid integer DEFAULT NULL)
RETURNS TABLE(id integer, codigo varchar, nombre varchar)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
    SELECT c.id, c.codigo, c.nombre
    FROM public.companias c JOIN public.usuario_companias_plataforma uc ON uc.compania_id=c.id
    WHERE uc.usuario_id=uid AND c.activo=TRUE AND (cid IS NULL OR c.id=cid)
    ORDER BY c.id FOR SHARE OF c, uc;
$$;
REVOKE ALL ON FUNCTION public.iam_lock_active_user(integer),
    public.iam_lock_memberships(integer, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.iam_lock_active_user(integer),
    public.iam_lock_memberships(integer, integer) TO iam_permissions;
GRANT SELECT ON usuarios_plataforma, roles_plataforma, usuario_roles_plataforma,
    companias, usuario_companias_plataforma TO iam_permissions;
GRANT SELECT, INSERT, UPDATE ON permisos_usuario_compania TO iam_permissions;
GRANT SELECT (id, evento_uuid) ON auditoria_outbox TO iam_permissions;
GRANT INSERT (evento_uuid, fecha_evento, servicio, evento, resultado,
    actor_usuario_id, objetivo_usuario_id, compania_id, detalle) ON auditoria_outbox TO iam_permissions;
GRANT USAGE, SELECT ON SEQUENCE auditoria_outbox_id_seq TO iam_permissions;

-- Workers only read required identity context and update their queue states.
GRANT SELECT ON sync_jobs, usuarios_plataforma, companias TO iam_sync;
GRANT UPDATE (estado, intentos, disponible_desde, worker_id, resultado,
    ultimo_error, fecha_inicio, fecha_fin, fecha_actualizacion) ON sync_jobs TO iam_sync;
GRANT SELECT ON auditoria_outbox TO iam_dispatcher;
GRANT UPDATE (estado, intentos, disponible_desde, worker_id, ultimo_error,
    actualizado_en, procesando_desde, completado_en) ON auditoria_outbox TO iam_dispatcher;

-- Audit is append-only even if a runtime service is compromised.
GRANT SELECT (id, evento_uuid) ON auditoria_eventos TO iam_audit;
GRANT INSERT (evento_uuid, fecha_evento, servicio, evento, resultado,
    actor_usuario_id, objetivo_usuario_id, compania_id, detalle) ON auditoria_eventos TO iam_audit;
GRANT USAGE, SELECT ON SEQUENCE auditoria_eventos_id_seq TO iam_audit;

-- Backups can read data but cannot alter roles, schema, or application rows.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO iam_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO iam_backup;
COMMIT;
