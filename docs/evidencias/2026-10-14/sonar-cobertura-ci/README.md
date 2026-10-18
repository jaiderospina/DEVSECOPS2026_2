# E29 - Cobertura real CI y Quality Gate

Fecha: 14 de octubre de 2026 (America/Bogota). Revisión: **f87243ebf8486c9e5cc5cb781fef1fceb0816e15**, rama master del espejo. [Ejecución 31/31](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38587861186). [Recibo, hashes y métricas](SONAR_COBERTURA_CI.json).

**Quality Gate passed**, cobertura nueva Sonar **88,1 % ≥ 80 %**, global **54,5 %**. El resultado corresponde al analysisId del [recibo](sonar-analysis-receipt.json); condiciones en [Quality Gate](sonar-quality-gate.json), [métricas de proyecto](sonar-coverage-project.json) y [archivos](sonar-coverage-files.json). No se modificaron umbrales, reglas ni periodo para aprobar.

Python CI: 50 archivos, 2888/3697 sentencias ejecutadas (78,12 %), 74,80 % con ramas. [XML portable](python-ci-coverage.xml), [JSON](coverage.json), [reporte](coverage.txt). LCOV: cuatro módulos JavaScript, 95,80 % de líneas y 92,06 % de ramas; [reporte](frontend-coverage.lcov). Esta medición no cubre integralmente React ni sustituye las métricas nuevas/globales de Sonar.

Doce casos nuevos: cinco HTTP reales del gateway y siete de ciclo de vida/limpieza/redacción. CI valida 26 controles DAST, 11 SCA y 21 de automatización, además de las suites funcionales existentes y las regresiones de seguridad de Identity. El staging mide catorce scripts del host mediante un arnés explícito; los procesos dentro de Docker conservan sus límites.

El primer corte 26ae3ae alcanzó 88,1 % nueva, pero su gate falló por seis instalaciones de dependencias (S8541/S8544). Se corrigieron con `--only-binary :all:`, locks completos y `--require-hashes`; coverage se incorpora también al inventario Trivy. No se aceptaron/ignoraron esos hallazgos. El diagnóstico manual es de solo lectura.

E22 (69 % local, cinco servicios), E25 y E27 son históricos. Se mantiene la release Docker 1.0.0 histórica, las seis amenazas STRIDE no aceptadas, y los límites GET-only/39 API-rol de ZAP. El PDF E28 conserva el snapshot d6c3440; esta evidencia es posterior. Los directorios de reportes generados se excluyen de fuentes Sonar, sin excluir código de aplicación. Cada nuevo HEAD necesita verificar sus checks.

El check externo informa 43 issues nuevos y cero aceptados en este corte; todas las condiciones del gate aprobaron. Se ejecutaron 86 pruebas bulk-users y 121 T13/T15 en CI. Los seis hallazgos de instalación corregidos no son los seis riesgos STRIDE todavía no aceptados.

## ZAP del mismo corte

El artefacto `zap-staging-evidence` del run 38587861186 (f87243e) aprobó 7 scans, 39 operaciones/API-rol y 1947 requests, sin hallazgos en el alcance GET-only. [Gate](zap-approved/gate.json), [limpieza](zap-approved/lifecycle.json), [comparación DB](zap-approved/database-comparison.json) y [resumen](zap-approved/summary.json) preservados con hashes en el recibo. No acredita login/MFA, XLSX, escritura ni frontend completo.
