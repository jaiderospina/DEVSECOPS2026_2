# Historial de avances — IAM Secure — 6 de octubre de 2026

Esta cronología conserva el avance acreditado en cada corte. Las cifras históricas corresponden a sus commits/runs concretos; el estado vigente está en las secciones 7, 12 y 13 del README y en el registro de validación local. Los registros detallados permanecen versionados.

| Fecha / hito | Avance acreditado | Evidencia |
|---|---|---|
| 29 de septiembre: Sync Worker | 23 pruebas; dos workers procesaron ocho trabajos una sola vez; clon limpio documentado. | [Validación Sync](SYNC_WORKER_VALIDACION.md), commits `dd8508d` y `8c07ba6`. |
| 30 de septiembre: Audit y documentación | Audit Service/Outbox/Dispatcher, sanitización, idempotencia, reintentos y concurrencia; cuatro UML, manuales y matriz. | [Validación Audit](AUDIT_VALIDACION.md), [avance del día](AVANCE_2026-09-30.md). |
| 30 de septiembre: Threat Modeling y CI | DFD 0/1, 16 amenazas STRIDE; CI de aquel código con 21 jobs y 64 Pytest. | [Modelo](diagramas/threat-model/README.md), [STRIDE](seguridad/stride-matrix.md), [resumen CI b7704bc](evidencias/2026-09-30/IAM_Secure_CI_b7704bc.json), [CI push](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36814230828) y [CI PR](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36814237618). |
| 30 de septiembre: CSP, PyJWT y ZAP | CSP sin unsafe-inline; PyJWT 2.15.0 activo; baselines y retest pasivo autenticado completados. | [Registro final](evidencias/2026-09-30/IAM_Secure_CSP_retest.md), [checkpoint de cierre](CHECKPOINT_2026-09-30_CIERRE.md); capturas en la sección ZAP. |
| 5 de octubre: Permissions/grilla | API 8005, pestaña 5176, compañía destacada, control por usuario/compañía; aceptación local de grilla y cuentas soporte reportada. Run de interfaz: 26 jobs, 96 Pytest y cuatro comprobaciones Chromium. | [Etapa 1](PERMISOS_ETAPA_1.md), [CI 37408693914](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37408693914), [resumen versionado](evidencias/2026-10-05/PERMISOS_GRILLA_PUERTO_5176_CI.json). |
| 5 de octubre: integración | PR #2 fusionado en master, merge `9fccd36a2a917ae74b5f100bbd6126d19acab5c6`; GitHub registró también PR #1 integrado. | [PR #2](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/2); [CI del head validado 37409870379](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37409870379). |
| 6 de octubre: carga Excel e inactividad | Carga funcional comprobada con una cuenta; duplicado, exportación y excepción comprobados. Expiración en ambas vistas confirmada. | [Registro de esta sesión](VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md). Código Excel en rama; ajuste de inactividad local. |
| 6 de octubre: contraste académico y ramas | Estados consolidados frente a Requisitos.docx; evidencias ZAP preservadas en las cuatro ramas. CI del master consultado: 26/26 jobs aprobados. | [Comparación actual](../README.md#13-estado-de-cumplimiento-académico), [CI 37566343307](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37566343307). |

Las pruebas de navegador citadas utilizan contratos simulados. Las menciones antiguas a ZAP sin abrir, PR #1/#2 en borrador, seis imágenes o ausencia de lint pertenecen a cortes superados; sus registros son históricos. El master actual incorpora siete builds y jobs de lint/navegador.

---

[Estado actual en el README](../README.md#7-estado-actual-de-implementación).
