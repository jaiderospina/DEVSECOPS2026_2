# Avance actual — Prueba-ProyectoFinal / IAM Secure

Corte: **7 de octubre de 2026, America/Bogota**. Código funcional: `7c076613d0525148a0be4914cb8d8be2fc0645a1`, rama `feat/bulk-users-excel-20261005`. [PR #3](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/3) abierto, en borrador y sin integrar. Master consultado: `fed4a5d1af32e08af7a4618f1352bcaf05918436`.

## Realizado y pendiente por área

| Área | Estado | Completado / evidencia | Pendiente para cerrar |
|---|---|---|---|
| Aplicación local | Cumplido en el alcance aceptado | Identidad/MFA, RBAC, compañías, grilla, carga Excel e inactividad operativos. ADMIN TI genera el informe de auditoría y el usuario confirmó su Excel. | La aceptación local no aprueba el CI integral ni una instalación nueva. |
| Informe de auditoría | Cumplido local; release pendiente | Descarga XLSX con filtros UTC, hojas Auditoria/Resumen, ID, nombre y correo actuales del actor; permisos ADMIN_TI/MFA y límites probados. Usuario confirmó la descarga y las columnas. | Publicar imágenes actualizadas y verificar el despliegue de esta revisión en producción simulada. ADMIN_SOPORTE sigue excluido según el alcance acordado. |
| Carga masiva ampliada | Parcial | Validación, consentimiento, creación, duplicados y exportación probados; 51 regresiones backend incluidas en la última suite. | Lote de varias filas con correos funcionales de Facturación/Logística, pausado hasta disponer de los correos. |
| SCA y dependencias | Parcial | Diez manifiestos/locks con hashes; wheels obligatorios. E14 registra cero HIGH/CRITICAL y tres MEDIUM. Checkov 3.2.506 conserva controles y elimina ecdsa afectada. | CI integral de la revisión vigente y revisión de los tres MEDIUM; no declarar ausencia de todos los hallazgos. |
| SonarCloud | Parcial | Correcciones de rutas/argumentos y de los diez avisos Security/Medium aportados publicadas; regresiones locales aprobadas. | Confirmar análisis y Quality Gate A para el código actual. La consulta de checks de 7c07661 no mostró un check Sonar. No se desactivó el gate ni se aceptaron avisos. |
| GitHub Actions | Parcial | Pipelines CI/CD implementados y ejecuciones históricas aprobadas. Pruebas locales posteriores: E14 95, E15 98 y E16 86 por sus respectivos alcances. | Recuperar capacidad de ejecución y aprobar CI del código actual. GitHub no inició el job consultado por facturación/límite de gasto; el corte documental no equivale a CI aprobado. |
| Ansible, Checkov y CD | Cumplido histórico; revisión actual parcial | Run 37578596462 sobre ed00530: 29/29 trabajos, segunda ejecución changed=0 y persistencia al recrear PostgreSQL. | Repetir el despliegue completo con las imágenes de la revisión que incluye auditoría. El cambio local no sustituye ese CD. |
| Docker Hub y versión | Cumplido para 1.0.0; actualización parcial | Ocho imágenes propias y etiquetas 1.0.0/latest con push/pull y digests verificados en el run 37574847806. | Construir, escanear y publicar una nueva versión con auditoría y correcciones recientes; las imágenes históricas 1.0.0 no incluyen el informe. |
| Threat Dragon, DFD y STRIDE | Parcial | Modelo, DFD 0/1, validación de esquema y 16 amenazas documentados. | Ampliar/revisar el alcance de Permissions, carga e informe de auditoría; exportar DFD y cerrar amenaza-control-riesgo residual. |
| ZAP y staging | Parcial | Baselines y retest pasivo autenticado con correcciones CSP/cabeceras y evidencias conservadas. | Automatizar DAST contra staging y cubrir permisos, compañías, carga, auditoría y roles. No hay escaneo activo completo acreditado. |
| Documentación y capturas | Parcial | README, manuales, matriz, checkpoints y evidencias versionados; ocho capturas anteriores y confirmación de auditoría registrada en E17. | Completar capturas administrativas de entrega, ampliar/revisar manuales técnicos y diagramas para auditoría, exportar DFD/STRIDE y preparar la demostración funcional final. La captura aportada confirma el Excel, sin convertirla en una nueva suite E2E. |
| Badges y cobertura | Parcial | Badge de build master y versión de imágenes con evidencia; suites automatizadas existentes. | Medir cobertura real y añadir su badge. Los conteos de pruebas no son un porcentaje de cobertura; no existe release de GitHub acreditada. |
| Instalación reproducible | Parcial | PC actual operativo y despliegue aislado con PostgreSQL efímero probado. | Instalación desde cero en otro PC con el nuevo alcance, configuración, aprovisionamiento y comprobación de correo real. CI no instaló Docker ni usó SMTP real. |
| Integración del PR #3 | Parcial | Código publicado en feat/bulk-users-excel-20261005 y documentación actualizada; PR abierto en borrador. | Revisión, CI/Sonar y autorización separada antes de integrar. Se conserva sin merge; master no incorpora este avance. |
| Entrega académica | Parcial | Código, manuales, diagramas y resultados disponibles como insumos. | Resolver visibilidad pública, preparar PDF con la estructura requerida y grabar video de 10–15 minutos. PDF/video finales pendientes. |
| Observabilidad opcional | Pendiente opcional | No se acredita implementación. | Prometheus/Grafana, Loki/ELK y Falco son bonificaciones; su ausencia no bloquea los requisitos obligatorios. |

## Aceptación de auditoría

El usuario confirmó la descarga del Excel, luego solicitó el usuario que ejecutó cada evento. Tras actualizar Identity, confirmó «ya esta correcto» y aportó una captura con las columnas del actor diferenciadas del usuario objetivo. Se registra esa aceptación, sin atribuirle una nueva suite automatizada. El informe mantiene 31 días/5.000 eventos, dos hojas, filtros, sanitización, texto sin fórmulas y registro de generación por outbox. Nombres/correos son actuales; el ID permanece histórico.

## Evidencias y límites de validación

- [E14](evidencias/2026-10-07/SONAR_SECURITY_CI_20261007.json): 95 regresiones de seguridad/automatización/SCA/carga; diez manifiestos, cero HIGH/CRITICAL y tres MEDIUM.
- [E15](evidencias/2026-10-07/AUDITORIA_EXCEL_20261007.json): 98 pruebas del informe inicial (82 PostgreSQL y 16 Node), lint y build.
- [E16](evidencias/2026-10-07/AUDITORIA_ACTOR_20261007.json): 86 PostgreSQL (51 carga y 35 auditoría); muestra local de 10 eventos, 10 actores, 12 columnas sin fórmulas.
- [E17](evidencias/2026-10-07/AVANCE_CONFIRMADO_20261007.json): aceptación humana, revisiones, estado de CI y pendientes.
- [CD histórico](evidencias/2026-10-07/ANSIBLE_CD_37578596462.json): run 37578596462, código ed00530, 29/29, Ansible changed=0 y persistencia al recrear PostgreSQL. No se repitió como CD de 7c07661.

Los conteos se solapan y no se suman. No hay medición de cobertura ni SMTP real acreditado por estas suites. El CI de 7c07661 no inició el job consultado; SonarCloud de esa revisión no está confirmado.

## Entorno local y continuidad

El entorno operativo es `C:\Prueba-ProyectoFinal`, no el directorio temporal de trabajo. Se aplicaron cambios seleccionados preservando ajustes locales previos. Frontend e Identity fueron reconstruidos; al añadir el actor solo se recreó Identity. PostgreSQL conserva su inicio anterior y sus datos. Las imágenes locales nuevas no son las ocho imágenes 1.0.0 publicadas.

La carpeta se sincronizó por avance directo desde ce561e3 a la base remota 9df0694 de feat/bulk-users-excel-20261005. En ese punto HEAD local y remoto coincidieron y el árbol de trabajo quedó limpio. Los 18 archivos locales modificados o nuevos coincidían con el contenido remoto por líneas; uno difería solo en terminadores de línea. Se conservó el estado previo en un stash recuperable. Esta revisión documental registra el cierre; E17 conserva el estado anterior como evidencia histórica y [E18](evidencias/2026-10-07/SINCRONIZACION_LOCAL_GITHUB_20261007.json) registra la sincronización. La configuración .env conserva su huella y PostgreSQL sigue saludable con su inicio anterior. Los respaldos históricos se conservan y se genera un respaldo completo del nuevo corte. No ejecutar limpieza efímera sobre esta base personal.

Estimación global orientativa: **80 %** (rango 75–85 %). Es una valoración de planificación, sin ponderación académica oficial, y no representa cobertura de pruebas. Los pendientes de la tabla mantienen su alcance.

El siguiente paso es recuperar capacidad de CI, confirmar Sonar y cerrar la versión/deploy actualizado. ZAP, Threat Dragon, cobertura, segundo PC y entrega académica conservan pendientes propios. Mantener el PR en borrador y el lote de correos reales pausado.
