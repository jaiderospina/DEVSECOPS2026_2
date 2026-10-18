# ZAP automatizado contra staging — 13 de octubre de 2026

**E26: ejecución real aprobada.** [CI del espejo](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38511486612), commit **574bb3e8195c3583ebd973f33d7f48a738689f7d**, 29 trabajos aprobados y Sonar omitido por tratarse de una rama de trabajo: 30 jobs registrados, sin fallos. El job `zap-staging` construyó los servicios actuales en un proyecto nuevo sin puertos publicados, base `iam_zap`, secretos efímeros, cuentas @example.invalid y sin SMTP. No se utilizó Compose normal, .env local ni datos del PC.

## Resultado y controles

- ZAP 2.17.0 por digest: **7 scans, 39 combinaciones API/rol, 1947 solicitudes registradas**. Cinco reglas activas a intensidad LOW, todas ejecutadas; no spider ni AJAX spider.
- Gate MEDIUM/HIGH: **aprobado**. Hallazgos registrados: 0; bloqueantes: 0. No se ignoraron alertas. No equivale a ausencia de vulnerabilidades fuera de ese alcance.
- Contratos GET filtrados y gateway sin acceso directo del scanner a APIs/DB; pruebas previas de aislamiento y bloqueo de métodos/rutas ajenos.
- Comparación de base: sin cambios inesperados; solo se admite actividad de sesión durante las peticiones autenticadas. Limpieza confirmada de recursos del proyecto efímero, con paso always de respaldo.
- Los controles nuevos prueban escaneo incompleto, falta de rol/operación/regla, alertas MEDIUM, cambios en DB, métodos no GET, redacción y rechazo de limpieza sobre un runtime no propio.

## Evidencia conservada

[Recibo de API, jobs y hashes](ZAP_STAGING_CI.json) · [resumen de escaneo](reports/SUMMARY.md) · [gate](reports/gate.json) · [ciclo de ejecución y limpieza](reports/lifecycle.json).

Se versionaron los HTML/JSON saneados, cobertura por rol y comparación reducida de base; los valores se conservan tal como fueron archivados por CI. Se excluyen credenciales, JWT/JTI, contexto privado, logs crudos y hashes por celda de credenciales/MFA. El ZIP original permanece como artefacto de GitHub con retención de 30 días; los informes seleccionados y sus huellas quedan duraderos en Git.

## Alcance pendiente

La **automatización ZAP contra este staging está cumplida**. Login/MFA, carga XLSX, POST/PUT/PATCH/DELETE y exploración del frontend quedan fuera del laboratorio GET-only. Las respuestas 403 y las entradas rechazadas por el gateway no demuestran cobertura de lógica protegida. No se acredita una release Docker actualizada, ni nuevos tests T13/T15 remotos, ni un nuevo Quality Gate Sonar de esta rama. E20/E24/E25 conservan sus cortes propios.

La validación del código ocurrió antes de publicar esta evidencia documental; los commits posteriores requieren sus propios checks. Los intentos previos fallaron antes del active scan al comprobar el gateway. Se corrigió su UID/GID para leer el directorio privado del runner Linux sin ampliar capacidades ni permisos de los secretos.


## Validación posterior en master: CI aprobado y Sonar rechazado

[Run 38512781360](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38512781360), commit **2d8b4444447808bd75ed684dd9d0044f4c720d96**: **30/30 trabajos CI aprobados**, incluidos ZAP, análisis Sonar y gate. El nuevo artefacto ZAP confirma 7 scans, 39 operaciones/API-rol, 1.947 requests, sin hallazgos en ese alcance, sin cambios inesperados en DB y limpieza completada; su manifiesto se verificó.

El check externo **SonarCloud Code Analysis** terminó con **Quality Gate failed**: cobertura de código nuevo 0 % (mínimo 80 %), duplicación nueva 84,6 % (máximo 3 %) y fiabilidad C (requiere A). El éxito del job de envío a Sonar no significa aprobación de su Quality Gate. E25 conserva su aprobación histórica, pero no acredita este corte. [Recibo de ambos resultados](MASTER_VALIDATION.json).

El log confirma que los HTML generados estaban dentro del análisis de fuentes. Se ajusta `sonar-project.properties` para excluir solo HTML de evidencia y clasificar `dast/test_*.py` como pruebas. El código mantenido de aplicación y DAST permanece en alcance; no se cambian condiciones del gate ni se excluye código de su medición de cobertura. El impacto del ajuste requiere un análisis posterior. Falta importar cobertura real y tratar los hallazgos de fiabilidad; no se afirma que este ajuste por sí solo apruebe Sonar.
