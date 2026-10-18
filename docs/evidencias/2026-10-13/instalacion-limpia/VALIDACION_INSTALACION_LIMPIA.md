# Validación de instalación limpia — IAM Secure

**Fecha:** 13 de octubre de 2026
**Rama:** `feat/bulk-users-excel-20261005`
**Commit validado:** `6d7e51c` - `fix(security): harden MFA reset and validate RBAC controls`

## Objetivo

Validar que IAM Secure puede clonarse, configurarse, construirse y ejecutarse desde cero en un segundo computador independiente, sin reutilizar la base de datos, los volúmenes, los usuarios ni los secretos del equipo principal.

## Entorno

La prueba se realizó en un iMac Intel independiente.

- Git: `2.50.1`
- GitHub CLI: `2.102.0`
- Docker Engine: `29.8.2`
- Docker Compose: `v5.6.0`

El repositorio se clonó desde GitHub y se confirmó que el `HEAD` correspondía al commit `6d7e51c`.

## Preparación segura

Se creó un `.env` nuevo a partir de `.env.example`. No se copiaron secretos del computador principal.

Se generaron localmente valores nuevos para:

- `POSTGRES_PASSWORD`
- `JWT_SECRET`
- `MFA_ENCRYPTION_KEY`
- `AUDIT_INTERNAL_TOKEN`

Se confirmó que `.env` está ignorado por Git y protegido con permisos `600`.

La configuración fue validada con `docker compose config --quiet`, con resultado `compose_exit=0`.

## Construcción e inicialización
La construcción local finalizó correctamente con **7/7 inágenes construidas**.

Después de `docker compose up -d`, PostgreSQL alcanzó estado `healthy` y quedaron operativos:

- PostgreSQL
- Identity Service
- Frontend
- Permissions Service
- Permissions Grid
- Sync Worker
- Audit Service
- Audit Dispatcher

Se verificaron respuestas HTTP correctas de Identity, Permissions y Audit.

En la base inicializada desde cero existían las estructuras:

- `permisos_usuario_compania`
- `cargas_usuarios`
- `cargas_usuario_filas`

Esto confirmó la aplicación correcta de las migraciones del alcance actual.

## Bootstrap, autenticación y MFA

Se creó el `ADMIN_TI` inicial mediante el bootstrap controlado.

La contraseña temporal se suministró solo mediante variable de entorno. El primer acceso exigió cambio obligatorio de contraseña y enrolamiento MFA/TOTP.

Después del proceso, el usuario pudo ingresar correctamente al panel con rol `ADMIN_TI`.

## SMTP y creación de ADMIN_SOPORTE

Se configuró SMTP de Gmail mediante una contraseña de aplicación almacenada únicamente en el `.env` local.

La prueba controlada de correo produjo:

`smtp_test=OK`

y el mensaje fue recibido correctamente.

Posteriormente, desde `ADMIN_TI`, se creó un `ADMIN_SOPORTE`. El sistema generó una contraseña temporal, la envió por SMTP y exigió cambio de contraseña y MFA en el primer acceso.

El usuario `ADMIN_SOPORTE` pudo autenticarse correctamente.

## RBAC, carga masiva y Permissions Grid

La interfaz mostró las opciones correspondientes al rol `ADMIN_SOPORTE`, incluyendo:

- Identidades
- Compaí�as asignadas
- Carga masiva
- Grilla de permisos

La Grilla de permisos abrió correctamente en `localhost:5176` desde el flujo autorizado del panel.

Se verificó que:

- la sesión se transfirió correctamente;
- el token no quedó expuesto en la URL;
- la interfaz identificó la compaí�a asignada;
- al no existir líderes todavía, se mostró correctamente que no habéa usuarios líderes con asignación válida.

## Persistencia

Antes del reinicio completo del entorno se registró:

```text
usuarios=2
mfa=2
roles_asignados=2
```

Se ejecutó `docker compose down` sin `-v` y luego `docker compose up -d`.

Después de recrear los contenedores, los conteos permanecieron iguales:

```text
usuarios=2
mfa=2
roles_asignados=2
```

También se confirmó un nuevo inicio de sesión exitoso después del reinicio.

Esto demuestra que los datos persistieron correctamente en el volumen de PostgreSQL.

## Resultado

**VALIDACIÓN EXITOSA**

Prueba demostró reproducibilidad del entorno, inicialización desde cero, migraciones, autenticación, cambio obligatorio de contraseña, MFA, RBAC, SMTP real, creación de usuarios administrativos, funcionamiento de Permissions Grid y persistencia de datos.

## Alcance

Esta evidencia demuestra el funcionamiento del entorno local académico en un segundo computador independiente. No constituye una certificación de producción ni demuestra alta disponibilidad, TLS de producción, recuperación ante desastre o ausencia total de vulnerabilidades.

Las validaciones SAST, SCA, DAST y Threat Modeling se documentan por separado.

## Evidencia asociada

La salida técnica sanitizada se conserva en:

`docs/evidencias/2026-10-13/instalacion-limpia/evidencia-tecnica.txt`

No se incluyen contraseñas, JWT, secretos MFA ni credenciales SMTP.
