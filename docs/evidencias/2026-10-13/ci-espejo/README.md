# Validación CI/CD en repositorio espejo — 13 de octubre de 2026

> Corte E24 sobre 8262da2: sus límites se conservan. [E25](../sonar-espejo/README.md) registra la aprobación posterior CI/Sonar de f026d19.

El espejo `yeisonfblopez/DevSecOps-proyecto-Final-ci` ejecutó los workflows sobre **8262da201228f8f601c00a3277f61fd596378350**. Ambos `master` coincidían en ese commit al comparar; no había cambios exclusivos de código por trasladar. El repositorio principal ya incorporaba el ajuste **Semgrep 1.140.0 en Docker**, conservando reglas, código de fallo y el gate. Las primeras ejecuciones del espejo sobre a4d61e7 fallaron; las aprobaciones siguientes corresponden exclusivamente a 8262da2.

| Ejecución | Resultado comprobado |
|---|---|
| [DevSecOps #2](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38502244070) | **28/28 trabajos success**: Gitleaks, Semgrep/Bandit, SCA, siete builds/Trivy, Pytest, Permissions, Excel/auditoría, lint, navegador, modelo y gate. |
| [Deploy simulated production #2](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38502831730) | **30/30 trabajos success**: 28 de validación, IaC y despliegue. Misma revisión; ejecución manual. |

Los informes descargados acreditan Checkov (2 aprobados, 0 fallidos, 0 omitidos), fixture negativa rechazada sin ejecutarla, segunda ejecución Ansible `changed=0 / unreachable=0 / failed=0`, ocho contenedores no root, comprobaciones HTTP, un ADMIN_TI y persistencia tras recrear PostgreSQL. Trivy SCA verificó diez manifiestos, cero bloqueantes HIGH/CRITICAL y **dos MEDIUM**, conservando la política y la fixture vulnerable negativa. Esto no elimina el hallazgo de `ply` documentado por Snyk en tooling.

## Alcance y pendientes

- El CI aprueba **el workflow configurado en 8262da2**, no todas las pruebas existentes. La suite específica `tests/identity_security` de T13/T15 no se invoca en ese workflow y conserva su evidencia local; no se suman las 245 pruebas locales a los jobs del espejo.
- **SonarCloud no está acreditado:** no hay check Sonar en el espejo. El check consultado del mismo SHA en el repositorio original está cancelled con análisis fallido. Un workflow verde no equivale a un Quality Gate Sonar aprobado.
- El CD reutiliza **imágenes 1.0.0 por digest** del manifiesto de producción simulada. No publica imágenes ni despliega automáticamente las recién construidas en CI; no acredita auditoría XLSX/correcciones recientes dentro de esas imágenes históricas.
- ZAP automatizado contra staging, los seis riesgos residuales no aceptados, visibilidad pública, decisión de release actualizado, capturas finales y PDF/video conservan sus pendientes.
- La actualización documental posterior a este corte no se presenta como un nuevo CI aprobado. La restricción de Actions del repositorio original no se da por resuelta; el espejo aporta una validación independiente del mismo código.

## Evidencia conservada

[Recibo de API, jobs, procedencia y hashes](VALIDACION_ESPEJO.json), [runtime inicial](deploy-runtime-first.json), [runtime final/persistencia](deploy-runtime-final.json), [política Compose](iac-compose-policy.json), [gate negativo Checkov](iac-checkov-negative-gate.json) y [resumen SCA](sca-summary.json).

Se conservaron los JSON seleccionados sin alterar sus valores. No se versionaron credenciales, logs de autenticación ni archivos `.env`. Los artefactos originales tienen retención limitada; sus enlaces y IDs quedan registrados en los workflows y el recibo.
