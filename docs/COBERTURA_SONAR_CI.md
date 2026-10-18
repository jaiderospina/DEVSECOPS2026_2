# Cobertura medida para SonarCloud

Trabajo iniciado el 14 de octubre de 2026 en la rama `codex/sonar-coverage` del repositorio espejo. El umbral del Quality Gate se mantiene en **80 % de cobertura del código nuevo**. Importar un XML, aprobar pruebas o medir cobertura total no acredita por sí solo ese umbral.

## Flujo reproducible

1. Las suites Python ejecutan `coverage.py 7.16.2` con medición de líneas y ramas, rutas relativas y seguimiento de subprocesos. Los servicios se prueban en procesos separados para evitar colisiones entre módulos llamados `main`/`database`.
2. Las pruebas de Permissions y carga Excel usan PostgreSQL efímero con las migraciones reales. Las regresiones de seguridad de Identity usan una segunda base `iam_negative_test`, con la señal explícita `IAM_NEGATIVE_DISPOSABLE=1`; nunca leen `.env` ni datos del PC.
3. Los controles SCA/automatización y DAST generan datos de cobertura. El arnés `tests/coverage/run_staging.py` invoca coverage explícitamente para los scripts del host: el entorno saneado del staging elimina las variables de autoarranque de coverage. Esto no implica instrumentación de todas las API o de los procesos dentro de Docker.
4. Las 16 pruebas Node existentes generan LCOV de los cuatro módulos que ejecutan: política CSP, generador Nginx y construcción de URL de carga y auditoría. No equivale a cobertura completa de componentes React.
5. Sonar descarga artefactos **de la misma ejecución**, combina los datos Python y verifica que las rutas XML corresponden a archivos reales del checkout. LCOV usa rutas relativas a la raíz del repositorio.
6. `sonar.python.coverage.reportPaths` y `sonar.javascript.lcov.reportPaths` importan XML/LCOV antes de esperar el Quality Gate. Los directorios temporales de reportes se excluyen del análisis de fuentes; el código de aplicación conserva su alcance.
7. Se guarda el resultado del análisis identificado por su `analysisId`, commit y rama, junto con las métricas por archivo. El gate final de la propuesta requiere Sonar donde está habilitado; ramas/repositorios fuera del alcance mantienen la omisión explícita.

La ejecución de Sonar está limitada al workflow directo `DevSecOps` en `master` del espejo, para eventos push/workflow_dispatch. La organización rechaza acceder a métricas de otras ramas. La propuesta exige `SONAR_TOKEN` en esos casos. Los callers de CD/publicación no transfieren ese secreto y conservan la omisión explícita de Sonar de su validación reutilizada; el bloqueo nuevo corresponde al CI directo. El usuario autorizó integrar y validar en `master` del espejo tras las pruebas de la rama, y sincronizar principal/carpeta local después de comprobar el resultado.

## Pruebas adicionales

- Cinco casos HTTP reales del gateway sobre loopback: GET autorizado, rechazo de métodos de escritura y escapes de alcance, sustitución de credenciales y eliminación de cabeceras de sobrescritura, ausencia de credenciales para acceso público, respuestas/fallos upstream y cierre de keepalive.
- Siete casos del ciclo de vida: limpieza propia al finalizar, limpieza tras un hallazgo bloqueante, fallo de limpieza registrado, rechazo previo de salida insegura/existente o runtime ausente, repetición segura de limpieza y redacción de salidas de procesos.

Las pruebas de orquestación usan dobles de Docker. No construyen, eliminan ni modifican recursos reales. El staging de CI conserva sus controles de aislamiento, política MEDIUM/HIGH y limpieza del proyecto propio.

## Resultados y límites

- [Primera validación de suites](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38577080891), commit `3362234`: pipeline aprobado; Sonar omitido porque esa primera configuración solo analizaba `master`.
- Los datos de esa ejecución registraron 2.450/3.472 sentencias Python ejecutadas (70,56 % de líneas; 67,18 % combinado con ramas). Su alcance incluye los archivos Python medidos por las suites, no toda la aplicación ni el código nuevo de Sonar.
- Las 16 pruebas Node ejecutadas localmente midieron 95,80 % de líneas y 92,06 % de ramas de cuatro módulos; su importación posterior queda acreditada por E29.
- Los doce casos nuevos aprobaron localmente. Las pruebas POSIX de aislamiento y permisos se verifican en Linux CI; los contratos de modo 0700/0600 no se sustituyen por permisos Windows.
- La segunda ejecución `38578900923`, commit `78579c5`, validó las suites, el staging instrumentado y la consolidación portable del XML. Sonar recibió el análisis, pero su consulta del Quality Gate y métricas falló por la restricción de la organización a la rama principal: `Organization is not allowed to access data from non main branches`. No acredita aprobado/rechazado por cobertura.
- [Validación final de la rama](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38581937525), commit `048c52e`: pipeline aprobado, incluido staging con el arnés explícito, 26 pruebas DAST (doce nuevas), 11 SCA y 21 de automatización. LCOV de los cuatro módulos generado y sus rutas verificadas en Linux. Sonar omitido en la rama por la restricción confirmada de la organización.

[E29: cobertura CI y Quality Gate](evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites. La sincronización se realiza después de esa validación; consultar Git para el SHA del commit documental final.

## Artefactos a revisar en Actions

`sonar-coverage-evidence`: `coverage.xml`, `coverage.json`, `coverage.txt`, `frontend-coverage.lcov`, `sonar-analysis-receipt.json`, `sonar-quality-gate.json`, `sonar-coverage-project.json` y `sonar-coverage-files.json`. Los reportes solo se atribuyen al commit/rama del recibo. Para diagnosticar el umbral, revisar las condiciones del Quality Gate y los archivos con líneas/condiciones nuevas sin cubrir, no el porcentaje global de coverage.py.

El [informe PDF](informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf) incorpora el cierre de cobertura del corte `f87243e` (E30). La edición E28 anterior se conserva como histórico. El [checkpoint](CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) y los históricos permanecen como referencia del corte integrado anterior.

## Cierre validado

[E29: cobertura CI y Quality Gate](evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites.

Python: 2888/3697 líneas ejecutadas (78,12 %), 74,80 % incluyendo ramas; Sonar usa sus propias métricas y su periodo de código nuevo. El diagnóstico de 26ae3ae alcanzó 88,1 % nueva, pero falló por seis instalaciones CI; la corrección usa locks/hashes/wheels e incorpora coverage al inventario Trivy, sin cambiar los pins runtime.

El corte E29 ejecutó **86 pruebas de carga Excel y 121 específicas T13/T15** en CI con PostgreSQL efímero. El check externo Sonar informó **43 issues nuevos y cero aceptados**, con todas las condiciones del gate aprobadas; no equivale a resolver toda la deuda técnica ni los seis riesgos STRIDE no aceptados.

## Ejecutar pruebas de integración

Usar PostgreSQL nuevo y exclusivamente efímero con las migraciones y variables de los jobs CI. Las suites realizan TRUNCATE sobre sus tablas de fixture; nunca apuntarlas a la base normal del PC ni cargar .env de desarrollo. Para continuar la validación completa, usar Actions del espejo y conservar los reportes de esa ejecución.
