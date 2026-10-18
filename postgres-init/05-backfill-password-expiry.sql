-- ============================================================
-- IAM SECURE
-- Migración: expiración de contraseñas definitivas heredadas
-- PASO 6.83
-- ============================================================
--
-- OBJETIVO:
-- Asignar una fecha inicial de expiración a credenciales que:
--   1. están activas;
--   2. ya poseen una contraseña definitiva;
--   3. fueron creadas antes de implementar password_expira_en.
--
-- SEGURIDAD:
-- Esta migración NO modifica:
--   - password_hash;
--   - roles;
--   - compañías;
--   - sesiones;
--   - estado de bloqueo.
--
-- Es idempotente porque solamente modifica registros cuyo
-- password_expira_en todavía sea NULL.
--
-- La política académica inicial establece 60 días.
-- La aplicación utiliza PASSWORD_EXPIRE_DAYS para los cambios
-- de contraseña realizados posteriormente.
-- ============================================================

UPDATE credenciales
SET
    password_expira_en = NOW() + INTERVAL '60 days',
    fecha_modificacion = NOW()
WHERE activo = TRUE
  AND requiere_cambio_password = FALSE
  AND password_expira_en IS NULL;