# E32 - STRIDE verificado en master del espejo

14 de octubre de 2026, America/Bogota. Código **61a1f7acab2c76ef8e3669ae8f6ddc7fc7172df4**, [CI 38638956405](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405): **32/32 trabajos aprobados** y check externo Sonar **Quality Gate passed**. [Recibo CI, laboratorio, métricas y hashes](STRIDE_CI_VALIDATION.json). Nueva cobertura **85,6 % ≥ 80 %**; global Sonar **56,7 %**. El check reporta 42 issues nuevos, cero aceptados; no equivale a ausencia global de deuda/riesgo. Umbrales y periodo conservados.

## Controles y procedencia

- [Laboratorio de este run](ci/stride-secure-lab.json): árbol Git limpio, mismo SHA, 11 comprobaciones aprobadas y limpieza confirmada. Cuatro HTTPS con CA validada/TLSv1.3, rechazo de CA desconocida, HTTP y host inválido; APIs/DB sin puertos directos.
- Seis roles DB independientes, sin superusuario/DDL/escalada. Bootstrap con iam_identity y todos los runtimes no root. Las conexiones reales comprueban permisos permitidos y accesos cruzados denegados.
- MFA real, Permissions protegido, reset atómico en ambas rutas y entrega de auditoría; fallos INSERT/COMMIT revierten todo. Alertas terminales sin payload; eventos históricos best-effort conservan límites.
- Backup autenticado/cifrado, sin plaintext en disco; restore a DB nueva/vacía, ACL reaplicadas y secreto MFA descifrable con la clave original.
- Carga: **30 solicitudes**, **28 respuestas 429**, **cero 5xx**, con XFF falsificado y concurrencia máxima dos. No acredita carga distribuida/productiva.
- [Gateway Trivy](ci/stride-gateway-trivy.json): **cero CRITICAL**; no afirmar cero CVEs de todas las severidades.
- [Seguridad Identity](ci/tests/identity-security.xml): **183 casos** (121 T13/T15 anteriores + 14 T06 + 48 roles), [Excel](ci/tests/bulk-users.xml): **86**, [helpers](ci/stride-tooling.xml): **28**. Dispatcher: 25 y cuatro subtests; Node: 24 casos en CI. Suites y revisiones no se suman como medición única.
- [Sonar por analysisId](ci/sonar-analysis-receipt.json), [gate](ci/sonar-quality-gate.json), [medidas](ci/sonar-coverage-project.json), [Python](ci/coverage.xml), [LCOV](ci/frontend-coverage.lcov). Reportes generados por esta misma ejecución; LCOV mide cinco módulos, no todo React.

+## ZAP del mismo corte

+[ZAP del mismo run](ci/zap/summary.json), [gate](ci/zap/gate.json), [ciclo/limpieza](ci/zap/lifecycle.json), [integridad DB](ci/zap/database-comparison.json): staging nuevo GET-only, 7 scans/39 API-rol, 1.947 solicitudes, cero alertas dentro del alcance. Login/MFA/XLSX/mutaciones/frontend no forman parte de ZAP; el laboratorio específico aporta pruebas distintas.

## E31 preservada e historial

[Preparación local E31](STRIDE_LOCAL_PREPARATION.json) y [laboratorio local](LOCAL_SECURE_LAB.json) conservan base Git, estado dirty y hashes; no acreditan un commit limpio ni se suman al run remoto. La rama d51902c aprobó CI con Sonar omitido por el alcance de la organización; master hizo su propio análisis. La preparación anterior a336451 detectó una contraseña bootstrap aleatoria sin carácter especial y se corrigió el generador antes de esta validación. Ningún umbral/check se relajó.

[Sonar inicial d51902c](ci/history/SONAR_BLOCKED_D51902C.json) bloqueó seguridad C por lectura CLI sin confinamiento y log injection. Se corrigieron confinamiento/archivo privado acotado y JSON ASCII de una línea; cinco regresiones de herramientas y una de log. El nuevo corte pasó con reglas/umbrales preservados. [CD d51902c](ci/history/CD_SIMULATED_D51902C.json) aprobó 33 trabajos más Sonar explícitamente omitido (34 total), ocho runtimes no root/HTTP/persistencia, sobre imágenes históricas 1.0.0; no se publica una release actualizada por ese resultado.

## Alcance y siguiente decisión

T03/T04/T06/T07/T10/T14 tienen tratamientos verificados **en el perfil seguro de laboratorio**. El Compose de desarrollo mantiene HTTP y usuario DB administrativo. Reset MFA/alertas son código común y el runtime existente requiere reconstrucción. La migración 13 debe aplicarse a volúmenes existentes antes de reconstruir Permissions; no borra datos ni aprovisiona passwords. [Uso, controles y límites](../../../seguridad/STRIDE_HARDENING_LAB.md).

Los seis riesgos siguen **Open / sin aceptación residual posterior**. Las decisiones humanas del 13 de octubre se preservan. Adopción efectiva, confianza/custodia de claves, tráfico interno, otros eventos best-effort y operación de fallidos deben valorarse en la revisión del equipo. E28/E30/E29 y Docker 1.0.0 mantienen sus cortes históricos. Los artefactos no incluyen .env, passwords, JWT, claves privadas, dumps ni cuentas reales.
