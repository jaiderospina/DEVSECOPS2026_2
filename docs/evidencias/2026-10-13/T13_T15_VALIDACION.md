# Evidencia local T13/T15 — 13 de octubre de 2026

Base Git: `946371c81519210d7ae535dc9884cb9003c44568`, rama `feat/bulk-users-excel-20261005`, más cambios locales de pruebas y corrección descritos abajo. Sin staging, commit ni push. No atribuye estos resultados al código del commit base sin los cambios locales.

## Resultados

Ejecución secuencial en Python 3.13, entorno virtual temporal, PostgreSQL 17 desechable y migraciones reales. Cada suite se ejecutó en proceso separado con `pytest -q -x -p no:cacheprovider`; conteos contrastados con JUnit temporal, sin copiar logs o cuerpos HTTP.

| Orden | Suite | Aprobadas | Fallidas / errores / omitidas |
|---|---|---:|---:|
| 1 | tests/identity_security/test_t13_identity.py | 92 | 0 / 0 / 0 |
| 2 | tests/identity_security/test_t15_mfa_reset.py | 29 | 0 / 0 / 0 |
| 3 | tests/identity_http | 6 | 0 / 0 / 0 |
| 4 | tests/permissions | 32 | 0 / 0 / 0 |
| 5 | tests/bulk_users | 86 | 0 / 0 / 0 |
| Total | Cierre documental local | **245** | **0 / 0 / 0** |

T13: cobertura negativa parametrizada de jerarquía ADMIN_TI/ADMIN_SOPORTE/líderes, compañías ajenas, creación y asignación de roles administrativos, administración de compañías y pérdida inmediata de alcance con la misma sesión al retirar asignación, desactivar compañía o retirar rol. Las 92 pruebas incluyen controles positivos y aislamiento de listados; no son 92 casos exclusivamente negativos. Las denegaciones comprueban código HTTP, ausencia de datos ajenos y estado persistido protegido sin cambios; se excluye la actualización normal de actividad de sesión.

T15: ambas rutas reales, jerarquía, compañías, autogestión y pérdida de autorización. Los positivos verifican eliminación del MFA anterior, invalidación de desafíos pendientes, revocación de todas las sesiones activas del objetivo, ausencia de cambios sobre otro usuario, rechazo de sesiones/desafíos anteriores y rechazo del token anterior por Permissions mediante HTTP real hacia Identity. El siguiente login exige enrolamiento, no emite sesión definitiva antes de activar un TOTP nuevo y permite sesión tras esa activación.

## Corrección de seguridad y contratos conservados

`servicios/identity-service/usuarios.py`: `/usuarios/{id}/mfa/restablecer` rechaza objetivo inactivo con HTTP 400 después de comprobar jerarquía y compañía y antes de modificar MFA/desafíos/sesiones. La ruta vigente `/auth/usuarios/{id}/mfa/restablecer` ya rechazaba ese estado; la interfaz reserva el reset para identidades activas. Se ajustó únicamente la prueba T15 de objetivo inactivo.

Se conserva deliberadamente la diferencia sin MFA previo: `/auth` devuelve 200; `/usuarios` devuelve 409. También se conserva ADMIN_TI autorizado únicamente en `/auth` sobre ADMIN_SOPORTE, y `/usuarios` exclusivo de soporte sobre líderes de compañía activa compartida.

## Estado, riesgo residual y limitaciones

T13 y T15 permanecen **Open** en Threat Dragon y el validador. Sus controles técnicos fueron probados en este alcance; queda revisión del riesgo residual y aceptación humana explícita, no cierre automático. El tratamiento textual coincide con STRIDE; no se alteraron elementos, flujos ni arquitectura.

Es evidencia de integración local con PostgreSQL real y sesiones iniciales ficticias sembradas; no acredita un E2E completo de navegador, CI remoto, despliegue o aceptación manual. SMTP se sustituye para impedir envíos externos. Se registró una advertencia de obsolescencia de TestClient/httpx, sin fallas. Atomicidad de auditoría posterior al COMMIT continúa separada en T06; este cierre no modifica esa amenaza ni otros contratos.

## Integridad del alcance probado

SHA-256 de archivos ejecutados, para identificar los cambios locales sin inventar un commit de publicación:

- `tests/identity_security/conftest.py`: `a4f7bf114ea8ccc7dc8154edc97482207c629bbad326ad9889a1788f62f53db6`
- `tests/identity_security/test_t13_identity.py`: `7668fb88b0503a8a320fe8958717c3d8b035934dd69d1d39291b89ab16a67a3b`
- `tests/identity_security/test_t15_mfa_reset.py`: `9abc5ccd5072226cd1c3902c9a0d8f185390d386b108e205cf11828e4137480a`
- `servicios/identity-service/usuarios.py`: `8aec6437934c2e33ce247f1f4e7a17c4c7af088ef6d2935e489a8591fceb8c5b`

Sanitización: evidencia redactada como resumen; no contiene JWT, JTI, códigos/semillas TOTP, contraseñas, claves, cabeceras Authorization ni cuerpos de autenticación. Las huellas anteriores son de archivos de código, no de credenciales.

Validación documental: `python scripts/validate_threat_model.py` en el entorno virtual aprobó esquema y referencias (2 diagramas, 20 amenazas Open), alcance y paridad STRIDE T01–T20. `git diff --check` aprobó sin salida.
