# Cobertura combinada de cinco servicios Python — 13 de octubre de 2026

**69% mostrado por coverage.py: 1.941 / 2.830 sentencias cubiertas; 889 sin cubrir (68,5866%).** Medición local de sentencias; no es cobertura total del proyecto ni cobertura de ramas, ni un resultado de CI/SonarCloud.

| Servicio | Sentencias | Sin cubrir | Cobertura | Pruebas aprobadas reportadas | Subtests |
|---|---:|---:|---:|---:|---:|
| Identity | 2137 | 778 | 64% | 213 | 0 |
| Permissions | 170 | 7 | 96% | 32 | 0 |
| Audit Service | 178 | 25 | 86% | 13 | 0 |
| Audit Dispatcher | 176 | 41 | 77% | 22 | 4 |
| Sync Worker | 169 | 38 | 78% | 23 | 4 |

## Evidencia y procedencia

- `backend-combined-coverage.xml`: XML de coverage.py 7.16.2 saneado únicamente para retirar rutas absolutas del equipo de medición. Los conteos, hits y porcentajes se conservaron. El SHA-256 del XML original previo al saneamiento queda registrado en `summary.json`.
- `coverage-report.txt`: reporte textual preservado de la medición combinada.
- `summary.json`: totales contrastados con el XML por servicio, hashes SHA-256, HEAD al persistir y hash del XML original previo al saneamiento de rutas. Los archivos originales no incluyen el commit de ejecución; no se atribuye retrospectivamente una revisión exacta a la medición.

Rama revisada: `feat/bulk-users-excel-20261005`. Los conteos de tests fueron registrados a partir de las ejecuciones locales exitosas realizadas durante la medición; no se deducen del XML y no se suman a conteos históricos de otras suites. Identity combina sus suites base (127) y bulk_users (86), uniendo datos de cobertura línea por línea, sin promediar porcentajes.

Quedan fuera frontend, `servicios/usuarios`, infraestructura y cualquier otro componente no incluido en el XML. Se mantienen los scripts bootstrap de Identity, incluidos los de 0%. El badge es estático y representa esta medición fechada; no se actualiza automáticamente.

## Reproducir una nueva medición

El archivo binario `.coverage` original no se versiona porque conservaba rutas absolutas del equipo local. Para una nueva medición, ejecutar nuevamente las suites por separado con sus dependencias y PostgreSQL desechable, conservar los datos de Identity base/bulk y de los otros cuatro servicios, y combinarlos con `coverage combine --keep`.

No ejecutar las suites contra una base de producción. En una nueva medición se recomienda registrar desde el inicio el commit, entorno y salidas de pruebas junto al reporte generado.
