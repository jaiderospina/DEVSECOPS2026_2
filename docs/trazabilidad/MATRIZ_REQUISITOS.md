# Matriz de Requisitos y Trazabilidad — IAM Secure

Revisado: 14 de octubre de 2026. Fuente: Requisitos.docx aportado, secciones 3-6. E32 acredita 61a1f7a: CI/cobertura y Quality Gate aprobado; E27 y E28 conservan el corte anterior y el PDF histórico. Los snapshots mantienen sus fechas y alcances.

## 1. Convención y evidencias

Cumplido: implementación con evidencia para el alcance indicado. Parcial: existe avance concreto y falta cierre. Pendiente: sin implementación/evidencia suficiente. No se asigna un porcentaje ni se confunde código publicado, integración en master y despliegue.

| Código | Evidencia |
|---|---|
| E1 | [CI de etapa 2, 147 Pytest y contenedores](../evidencias/2026-10-06/CONTENEDORES_CI_9b6affc.json): 27/27 trabajos, 11 comprobaciones Chromium y seis pruebas Node |
| E2 | [Inactividad publicada/probada](../evidencias/2026-10-06/INACTIVIDAD_CI_624ab1d.json) |
| E3 | [Aceptación local](../VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md) y [capturas](../usuario/capturas/README.md) |
| E4 | [Docker Hub 1.0.0](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json): 29/29 trabajos, siete imágenes y 14 etiquetas push/pull verificadas |
| E5 | [Permisos etapa 1](../PERMISOS_ETAPA_1.md) y tests/permissions |
| E6 | [Cierre ZAP](../CHECKPOINT_2026-09-30_CIERRE.md), [retest CSP](../evidencias/2026-09-30/IAM_Secure_CSP_retest.md) y capturas ZAP |
| E7 | [Threat Dragon](../diagramas/threat-model/README.md), modelo/esquema y [STRIDE](../seguridad/stride-matrix.md) |
| E8 | [Sync](../SYNC_WORKER_VALIDACION.md) y [Audit](../AUDIT_VALIDACION.md) |
| E11 | [Trivy SCA: alcance validado y CI bloqueado](../evidencias/2026-10-07/SCA_TRIVY_20261007.json), ocho manifiestos locales y seis inventarios Python de CI |
| E10 | [Ansible/CD, 29/29 trabajos](../evidencias/2026-10-07/ANSIBLE_CD_37578596462.json): producción simulada, Checkov, idempotencia y persistencia |
| E9 | [README](../../README.md), Compose, código y workflows versionados |
| E14 | [Snapshot histórico de Seguridad/SCA — 7 de octubre](../evidencias/2026-10-07/SONAR_SECURITY_CI_20261007.json): 95 regresiones, diez manifiestos, cero HIGH/CRITICAL y tres MEDIUM en esa ejecución; el estado vigente se interpreta junto con E18–E21 y Seguridad |
| E15 | [Auditoría XLSX inicial](../evidencias/2026-10-07/AUDITORIA_EXCEL_20261007.json): 98 pruebas de ese alcance |
| E16 | [Actor identificado](../evidencias/2026-10-07/AUDITORIA_ACTOR_20261007.json): 86 PostgreSQL, 35 auditoría |
| E17 | [Aceptación y checkpoint](../evidencias/2026-10-07/AVANCE_CONFIRMADO_20261007.json): informe/Excel confirmados por el usuario, CI/Sonar y release pendientes |
| E18 | [Validación local T13/T15](../evidencias/2026-10-13/T13_T15_VALIDACION.md): T13 92, T15 29, regresión Identity 6 / Permissions 32 / Excel 86; 245 aprobadas. Tratamiento técnico verificado; T13/T15 quedaron `Mitigated` tras la decisión humana documentada en E23. |
| E19 | [Threat Modeling/DFD actualizado](../evidencias/2026-10-13/threat-model/): Threat Dragon y STRIDE T01–T20, DFD nivel 0/1 revisados y exportados, con validación de esquema, referencias y paridad. |
| E20 | [DAST activo controlado](../evidencias/2026-10-11/dast-active-readonly/): laboratorio aislado GET-only, 7 scans, 39 combinaciones API/rol, 1.947 requests y 0 alertas dentro del alcance ejecutado. |
| E21 | [Instalación limpia reproducible](../evidencias/2026-10-13/instalacion-limpia/VALIDACION_INSTALACION_LIMPIA.md): iMac Intel independiente, secretos nuevos, build 7/7, migraciones, bootstrap, MFA, SMTP real, ADMIN_SOPORTE, Permissions Grid y persistencia. |
| E22 | [Cobertura local de cinco servicios Python](../evidencias/2026-10-13/coverage-python/README.md): 2.830 sentencias, 889 sin cubrir, 69%; XML saneado de rutas locales, reporte y hashes de trazabilidad. No representa cobertura total del proyecto. |
| E23 | [Aceptación humana de riesgo residual](../evidencias/2026-10-13/ACEPTACION_RIESGO_RESIDUAL.md): decisión para T01–T20 en alcance académico/local. T13/T15 `Mitigated`; 12 amenazas Open con riesgo residual aceptado solo para ese alcance; T03/T04/T06/T07/T10/T14 Open con riesgo no aceptado y tratamiento pendiente. No constituye aceptación productiva. |
| E24 | [E24: CI/CD del espejo](../evidencias/2026-10-13/ci-espejo/README.md): 8262da2, CI 28/28 y CD 30/30; Checkov, idempotencia, persistencia y Trivy SCA 10 manifiestos/dos MEDIUM. CD de imágenes 1.0.0; SonarCloud no acreditado. |
| E25 | [E25: SonarCloud del espejo](../evidencias/2026-10-13/sonar-espejo/README.md): f026d19, CI 29/29 y Quality Gate passed; check informa 45 issues nuevos, 0 hotspots y 0 % de cobertura de código nuevo, distinto del 69 % local. |
| E26 | [E26: ZAP automatizado](../evidencias/2026-10-13/zap-staging-ci/README.md): CI 29/29, ZAP staging nuevo, 7 scans/39 API-rol/1947 requests; gate, reportes HTML/JSON y limpieza aprobados. |
| E27 | [CI/ZAP y Sonar histórico](../evidencias/2026-10-14/CI_SONAR_ZAP_D6C3440.json): d6c3440, 30/30 jobs y ZAP aprobado; Quality Gate externo failed solo por cobertura nueva 0 % frente a 80 %. |
| E28 | [Informe técnico PDF histórico d6c3440](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14.pdf), 21 páginas, índice/autores/orden y revisión visual; [metadatos y hash](../informe/INFORME_TECNICO_METADATA.json). |
| E29 | [Cobertura y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): f87243e, CI 31/31, nueva 88,1 % frente a 80 % y global 54,5 %; seis hallazgos nuevos de instalación corregidos; XML/LCOV de la misma ejecución y recibo por analysisId. |
| E30 | [PDF actualizado f87243e](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf), 21 páginas, índice, Quality Gate aprobado y hallazgos/límites actualizados; [hash/procedencia](../informe/INFORME_TECNICO_CIERRE_SONAR_METADATA.json). E28 preservado. |
| E31 | [Preparación STRIDE local](../evidencias/2026-10-14/stride-hardening-lab/STRIDE_LOCAL_PREPARATION.json): base/dirty/hashes, pruebas locales históricas. |
| E32 | [STRIDE y CI/Sonar master](../evidencias/2026-10-14/stride-hardening-lab/README.md): 61a1f7a, CI 32/32, nueva 85,6 %/global 56,7 %, laboratorio TLS/roles/reset/backup/carga. Seis riesgos sin aceptación posterior. |
| E33 | [PDF vigente](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_STRIDE_LAB.pdf), 23 páginas, E32/61a1f7a; [hash/QA](../informe/INFORME_TECNICO_STRIDE_LAB_METADATA.json). E28/E30 preservados. |
| E34 | [Laboratorio seguro interactivo activo](../evidencias/2026-10-14/secure-demo/README.md): bdedc77, cuatro HTTPS, nueve runtimes no root, seis logins mínimos, CA autorizada solo para usuario Windows; primer acceso/MFA y decisión residual pendientes. |
| E35 | [Manual Windows/Linux y confirmación humana](../evidencias/2026-10-17/manual-ejecucion/README.md): 23 páginas, 23 apartados, índice enlazado, 4 capturas y sintaxis validada; recorrido contraseña/MFA confirmado en otro PC, sin cambio de aceptación STRIDE. |

E1/E2/E4/E10 conservan sus revisiones históricas. El PR #3 ya está integrado en master (19b54ee); E24 acredita CI/CD de su corte; E25 acredita posteriormente CI/Sonar de f026d19, sin convertir el CD en una nueva release.

## 2. Requisito 3.1 — Arquitectura

| Requisito | Estado y avance | Evidencia |
|---|---|---|
| SPA React o Vue | ✅ Cumplido: React/Vite y bundle Nginx | E1, servicios/frontend |
| Backend FastAPI/Flask/Node | ✅ Cumplido: Identity, Permissions y Audit FastAPI | E1/E5/E8 |
| Worker asíncrono independiente | ✅ Cumplido: Sync Worker y Audit Dispatcher | E8 |
| Base open source | ✅ Cumplido: PostgreSQL 17 y volumen | E9 |
| JWT u OAuth2 con roles | ✅ Cumplido: JWT, RBAC, sesión persistente; MFA amplía mínimo | E2/E3/E5/E18 |
| Aislamiento por compañía | ✅ Cumplido en alcance probado: autorización en API y pruebas negativas | E3/E5/E18 y tests/bulk_users |

## 3. Requisito 3.2 — Contenedores

| Requisito | Estado y avance | Evidencia |
|---|---|---|
| Dockerfile por servicio propio | ✅ Cumplido en etapa 2: siete imágenes; PostgreSQL oficial, grilla/bootstrap reutilizan | E1 |
| Base mínima | ✅ Cumplido: slim/alpine, frontend final Nginx sin Node/npm | E1 |
| Usuario no root | ✅ Cumplido para siete imágenes: UID efectivo mayor que cero | E1/E4 |
| Capas optimizadas | ✅ Cumplido: dependencias antes del código y frontend multietapa; reducción 94,83 % sin comprimir | E1 |
| Compose de desarrollo | ✅ Cumplido: entorno local operativo | E3/E9 |
| Imágenes Docker Hub del equipo | ✅ Cumplido: siete repositorios jeancarlosalmenarez8318 | E4 |
| Etiqueta semántica | ✅ Cumplido: 1.0.0, metadatos de commit y protección de versión existente | E4 |
| latest | ✅ Cumplido: coincide con 1.0.0 por imagen en la publicación registrada | E4 |

E1 registra sondas UID de imágenes; E10 añade arranque conjunto de ocho contenedores, healthchecks y controles HTTP de la producción simulada. E4 verifica pull autenticado, no visibilidad pública/descarga anónima. usuarios tiene imagen propia, pero no está activo en Compose.

## 4. Requisito 3.3 — Repositorio

| Requisito | Estado y avance | Evidencia / cierre |
|---|---|---|
| Código completo GitHub | ✅ Cumplido: base y último avance publicados | E9; PR #3 conserva etapa 2 |
| LICENSE | ✅ Cumplido: MIT versionada | ../../LICENSE |
| README | ✅ Cumplido como documento: propósito, tecnologías, quick start y estado real | E9; badges se evalúan en 4.1 |
| docker-compose.yml | ✅ Cumplido: operativo para desarrollo | E3/E9 |
| .github/workflows CI/CD | ✅ Cumplido en etapa 2: CI y CD de producción simulada ejecutados | E10/E24; PR #3 integrado en master |
| infraestructura Terraform/Ansible | ✅ Cumplido con Ansible: despliegue e idempotencia comprobados | E10; instalación opcional Docker no ejecutada en CI |
| orquestacion despliegue | ✅ Cumplido: Compose de producción simulada image-only ejecutado | E10; ocho contenedores y persistencia PostgreSQL |
| servicios por microservicio | ✅ Cumplido: código organizado y Dockerfiles | E9 |
| docs completos | 🟡 Parcial de cierre: manuales, cuatro UML, matriz, Threat Dragon/STRIDE y DFD 0/1 actualizados; ocho capturas incorporadas | E19; sincronización documental revisada al 14; faltan capturas finales de las demás funciones |
| Integración de etapa 2 en master | ✅ Cumplido: PR #3 fusionado, 19b54ee | Código incorporado; E24 acredita el workflow CI posterior de 8262da2 en el espejo. SonarCloud de f026d19 aprobado en el espejo, E25 |
| Repositorio público | ❌ No cumple actualmente: privado | Cambio de visibilidad pendiente; no realizado por actualizar documentos |

## 5. Requisito 3.4 — Pipeline DevSecOps

### Fase 1: planificación

| Requisito | Estado y avance | Evidencia / cierre |
|---|---|---|
| Threat Dragon | ✅ Cumplido en modelado: modelo actualizado al alcance vigente, revisado y exportado | E7/E19/E23; estado vigente: 18 amenazas Open y T13/T15 Mitigated; seis riesgos permanecen no aceptados |
| DFD 0 y 1 | ✅ Cumplido: actualizados al alcance vigente, revisados visualmente y exportados | E19; DFD nivel 0 y nivel 1 versionados como evidencia |
| STRIDE | ✅ Cumplido en identificación/modelado: T01–T20 documentadas en seis categorías, con controles y paridad modelo/matriz validada | E7/E18/E19/E23; decisión humana registrada para el alcance académico/local. T03/T04/T06/T07/T10/T14 tienen tratamiento verificado E32; laboratorio interactivo activo E34; primer acceso/MFA y decisión residual posterior pendientes |

### Fase 2: codificación

| Requisito | Estado y avance | Evidencia / cierre |
|---|---|---|
| Hook pre-commit Gitleaks | ✅ Cumplido configurado y prueba registrada | .pre-commit-config.yaml; activar en cada clon |
| Gitleaks en CI | ✅ Cumplido: historia completa y salida redactada | E1/E4 |
| Semgrep y Bandit | ✅ Cumplido en implementación y validación local vigente: Semgrep 1.140.0 analizó 94 archivos con 233 reglas y 0 findings; Bandit 1.8.6 no reportó hallazgos de severidad/confianza MEDIUM o superior | E1/E4 conservan aprobaciones históricas; CI de 8262da2 aprobado en el espejo, E24; SonarCloud de f026d19 aprobado en el espejo, E25 |
| SCA | 🟡 Implementado y validado por alcance: dependencias runtime revisadas sin vulnerabilidades conocidas en el alcance ejecutado; tooling de Checkov conserva hallazgos residuales documentados | E11/E14 y ../seguridad/SEGURIDAD.md; no se declara SCA global en cero y CI de 8262da2 aprobado en el espejo, E24; SonarCloud de f026d19 aprobado en el espejo, E25 |
| Dependency-Check o Trivy sobre manifiestos | 🟡 Parcial de cierre: Trivy cubrió 10/10 manifiestos; tras actualizar Pytest permanecen dos MEDIUM de `asteval` asociados al tooling de Checkov | Snyk del tooling también conserva `asteval` y `ply` transitivo; estos hallazgos no pertenecen al runtime de IAM Secure. CI de 8262da2 aprobado en el espejo; SonarCloud de f026d19 aprobado, E25; decisión residual del tooling pendiente |

### Fase 3: integración/build

| Requisito | Estado y avance | Evidencia |
|---|---|---|
| Construcción automática Docker | ✅ Cumplido: siete imágenes | E1/E4 |
| Trivy/Grype de imágenes | ✅ Cumplido: Trivy CRITICAL incluye sin corrección | E1/E4 |
| Fallo ante CVE crítica sin excepción | ✅ Cumplido: exit-code 1 y gate de jobs; publicación después de scan | E1/E4 |
| Gestión de excepciones | ✅ Documentada como política; no se inventa una excepción activa | ../seguridad/SEGURIDAD.md |

### Fase 4: pruebas

| Requisito | Estado y avance | Evidencia / cierre |
|---|---|---|
| Pytest/Jest | ✅ Cumplido: 147 casos corresponden a la evidencia histórica de etapa 2; el cierre local vigente ejecutó 245 pruebas aprobadas | E1/E18; cantidad de pruebas no equivale a porcentaje de cobertura |
| Integración y navegador | ✅ Cumplido en alcance acreditado: PostgreSQL real y 11 Chromium Nginx | E1/E5; correo/API de navegador simulados |
| Validación de seguridad T13/T15 | ✅ Controles verificados técnicamente: 92 pruebas T13 y 29 T15; cierre ejecutado de 245 pruebas | E18/E23; T13/T15 están `Mitigated` y su riesgo residual fue aceptado para el alcance académico/local |
| ZAP automatizado contra staging | ✅ Cumplido en alcance GET-only | [E26: ZAP automatizado](../evidencias/2026-10-13/zap-staging-ci/README.md); gate requerido en el espejo, MEDIUM/HIGH bloqueantes, HTML/JSON y limpieza aprobados. Login/MFA, XLSX, mutaciones y frontend no están cubiertos. |
| Regresión funcional Excel/grilla/inactividad | ✅ Cumplido para prueba local aceptada | E3; varias filas/correos reales pausadas |
| Informe de auditoría ADMIN TI y actor | ✅ Cumplido local: dos hojas XLSX, filtros y actor con ID/nombre/correo; confirmado por el usuario | E15/E16/E17; CI del espejo aprobado para 8262da2; release/deploy actualizado pendiente; SonarCloud de f026d19 aprobado en el espejo, sin acceso ADMIN_SOPORTE |

DAST pasivo: frontend 64 PASS, 3 WARN, 0 FAIL; Identity API 119 PASS, 0 WARN/FAIL; Audit 118 PASS y 1 WARN CORP aceptado/documentado; Permissions 119 PASS, 0 WARN/FAIL después de corregir cabeceras. DAST activo controlado E20: 7 scans, 39 combinaciones API/rol y 1.947 requests, con 0 alertas dentro del alcance GET-only y cinco reglas activas de baja intensidad. Esos resultados E6/E20 son históricos y no acreditan active scan completo o ausencia global de vulnerabilidades. La automatización posterior del staging GET-only sí está acreditada por E26/E27.

### Fase 5: release/deploy

| Requisito | Estado y avance | Evidencia / cierre |
|---|---|---|
| Terraform/Ansible | ✅ Cumplido con Ansible para producción simulada | E10; segunda ejecución changed=0, failed=0 |
| Despliegue automatizado IaC | ✅ Cumplido en runner Linux aislado tras CI/IaC | E10; imágenes 1.0.0 fijadas por digest, no recompiladas |
| Checkov/tfsec | ✅ Cumplido con Checkov para Ansible | E10; CKV_ANSIBLE_5/6 y prueba negativa. Compose usa validador propio |
| K3s/Swarm/Compose producción simulada | ✅ Cumplido con Compose diferenciado | E10; no root, read-only, sin capacidades, PostgreSQL sin puerto host y persistencia |
| Imágenes versionadas de release | ✅ Cumplido: 1.0.0/latest y digests | E4; no se creó release de GitHub |

### Fase 6: opcional

Prometheus/Grafana, Loki/ELK y Falco no están implementados. Son bonificaciones, no se declaran obligaciones bloqueadas por su ausencia.

## 6. Requisito 3.5 — Herramientas

GitHub Actions es la plataforma admitida. Se utilizan herramientas open source o de libre uso para los controles implementados (Gitleaks, Semgrep, Bandit, Pytest, Trivy, ZAP, Threat Dragon). La cadena completa permanece parcial porque quedan ampliación DAST fuera del alcance GET-only, tratamiento de los seis riesgos residuales no aceptados, revisión de los issues Sonar y cierre de la entrega académica. IaC/CD están acreditados por E10/E24 y el PR #3 ya está integrado en master. E24 valida las imágenes 1.0.0, no una nueva release.

## 7. Requisito 4 — Documentación

| Apartado | Estado y avance | Documento / cierre |
|---|---|---|
| 4.1 Propósito, tecnologías, licencia, quick start | ✅ Cumplido | ../../README.md |
| 4.1 Badges build/cobertura/versión | 🟡 Parcial: build master y versión de imágenes 1.0.0; cobertura local de cinco servicios Python medida (69%), con badge estático | E9/E4/E22; alcance integral y actualización automática pendientes |
| 4.2 Arquitectura, decisiones y patrones | ✅ Documentado al alcance actual | ../arquitectura/ARQUITECTURA.md |
| 4.2 Cuatro UML como código | ✅ Actualizados: componentes, despliegue, secuencia y casos de uso | ../diagramas/uml/ |
| 4.2 DFD de Threat Dragon | ✅ Cumplido: DFD 0/1 actualizados, revisados visualmente y exportados | E7/E19 |
| 4.3 Desarrollo | ✅ Documentado: clon, configuración, ejecución, pruebas, ramas/commits/revisión | ../desarrollo/DESARROLLO.md |
| 4.4 Despliegue local/operación | ✅ Documentado: requisitos, variables, migraciones, bootstrap y diagnóstico | ../despliegue/DESPLIEGUE.md |
| 4.4 IaC y despliegue completo desde cero | ✅ Cumplido en los alcances documentados: Ansible/producción simulada acreditados y clon limpio validado en un segundo computador independiente | E10/E21; la validación limpia incluyó secretos nuevos, build, migraciones, bootstrap, MFA, SMTP real y persistencia |
| 4.5 Seguridad | ✅ Documentado: herramientas, configuración, reportes y gestión | ../seguridad/SEGURIDAD.md; modelo/DAST conservan sus estados propios |
| 4.6 Manual de usuario | 🟡 Parcial: todas las funciones actuales descritas y ocho capturas reales | ../usuario/MANUAL_USUARIO.md; falta cobertura visual de las demás funciones |
| 4.6 Historia distinta de autenticación | 🟡 Parcial para entrega: flujo Excel/excepción probado y guion documentado | E3; falta demostración final completa/video |

El manual corrige la referencia antigua a MFA ADMIN_TI: la interfaz utiliza /auth/usuarios/{id}/mfa/restablecer y permite administrar soportes conforme a la política. Se acredita implementación por fuente; no se inventa aceptación manual adicional de ese caso.

## 8. Requisito 5 — Entregables

| Entregable | Estado y avance |
|---|---|
| GitHub público con código, pipeline, IaC y docs | 🟡 Parcial: código/CI/CD/Ansible/docs; privado; PR #3 ya integrado |
| Docker Hub con todas las imágenes propias versionadas | ✅ Cumplido: siete imágenes, 1.0.0 y latest, E4 |
| Informe técnico PDF | ✅ E33: PDF actualizado/revisado, 23 páginas, índice/autores y capítulos en el orden requerido |
| Video 10–15 minutos | ⏳ Pendiente: falta grabación del ciclo y la historia funcional |

## 9. Requisito 6 — Informe técnico

Portada, introducción, arquitectura/UML/pipeline, Threat Dragon/STRIDE, implementación de fases, resultados de seguridad y tabla de hallazgos, conclusiones y limitaciones están definidos como contenido necesario. E33 actualiza el PDF en el orden portada, índice, introducción, arquitectura/UML, Threat Dragon/STRIDE, pipeline, resultados/tabla de hallazgos y conclusiones. Observabilidad se incorpora si se implementa.

## 10. Evidencias y prioridades restantes

Conservar el artifact Docker Hub antes de su expiración (6 de noviembre de 2026); E4 mantiene digests duraderos, no copia los 14 reportes íntegros. Conservar también E10 y sus informes duraderos de producción simulada, Ansible, Checkov, idempotencia y persistencia. No contar ejecuciones repetidas como aceptaciones independientes.

1. Conservar E24 y mantener README, matriz, Seguridad y Despliegue alineados con el corte aprobado en el espejo y los límites de SonarCloud/release.
2. Revisar E22 y ampliar cobertura fuera de los cinco servicios Python medidos si se requiere alcance integral; el badge estático refleja la medición local fechada del 69%.
3. Completar primer acceso/cambio de contraseña/MFA del laboratorio activo E34; revisar E32/E34 para T03/T04/T06/T07/T10/T14 y registrar decisión residual posterior. La decisión humana para T01–T20 ya está registrada en E23; T13/T15 están `Mitigated`.
4. Conservar E24/E25/E27 como históricos. E32: CI 32/32 y Quality Gate aprobado, nueva 85,6 % frente a 80 %. Verificar cada nueva revisión y ampliar cobertura global según el alcance.
5. Integración del PR #3 completada; resolver la visibilidad pública exigida para la entrega.
6. Decidir si se publica una nueva versión de imágenes Docker que incorpore el código y las correcciones posteriores a 1.0.0; la versión 1.0.0 se conserva como release histórico.
7. Completar las capturas administrativas y preparar la historia funcional de sustentación.
8. Automatización contra staging GET-only completada en E26; conservar reportes y ampliar flujos no cubiertos cuando corresponda.
9. Completar la ampliación opcional de carga de varias filas de Facturación/Logística cuando existan correos funcionales disponibles; no bloquea el núcleo ya validado.
10. Informe PDF actualizado en E33; preparar/grabar el video de 10–15 minutos.

La instalación reproducible desde cero en un segundo computador ya fue completada y evidenciada en E21, por lo que no permanece como actividad pendiente.

[README](../../README.md) · [Arquitectura](../arquitectura/ARQUITECTURA.md) · [Desarrollo](../desarrollo/DESARROLLO.md) · [Despliegue](../despliegue/DESPLIEGUE.md) · [Seguridad](../seguridad/SEGURIDAD.md) · [Usuario](../usuario/MANUAL_USUARIO.md).

## 11. Cierre concreto de avances parciales

La [tabla de avance del 7 de octubre](../AVANCE_ACTUAL_2026-10-07.md) se conserva como snapshot histórico. Desde entonces quedaron completadas la actualización/revisión/exportación de Threat Dragon/DFD/STRIDE, la instalación limpia reproducible en un segundo computador y la decisión humana de riesgo residual para T01–T20, acreditadas por E19, E21 y E23. Permanecen como cierres parciales ampliación de cobertura global, priorización de deuda técnica y CI de futuras revisiones, decisión sobre nueva release Docker, ampliación de cobertura DAST fuera de GET-only, capturas administrativas, ampliación de cobertura fuera de los cinco servicios medidos, primer acceso/MFA de E34 y revisión residual de T03/T04/T06/T07/T10/T14, visibilidad del repositorio y video; E33 acredita el PDF actualizado/revisado. La ampliación con correos reales de Facturación/Logística continúa como mejora opcional.

## Evidencia T13/T15 — 13 de octubre de 2026

E18 acredita los controles de integración local de RBAC/multitenancy y ambas rutas de reset MFA. La prueba de objetivo inactivo exige HTTP 400 en ambas rutas; se conserva /auth 200 frente a /usuarios 409 sin MFA previo. Las pruebas técnicas de este alcance están aprobadas. E23 registra la decisión humana posterior: T13/T15 están `Mitigated` y su riesgo residual fue aceptado para el alcance académico/local. Esto no acredita CI remoto, despliegue productivo ni ausencia total de riesgo.


### Resultado posterior de Sonar en master

[validación posterior de E26](../evidencias/2026-10-13/zap-staging-ci/README.md#validación-posterior-en-master-ci-aprobado-y-sonar-rechazado): `2d8b444` aprobó 30/30 jobs CI, pero el check externo Sonar rechazó el Quality Gate por cobertura nueva 0 %, duplicación 84,6 % y fiabilidad C. E25 es histórico. Ese resultado es histórico; E32 documenta el cierre posterior con cobertura real importada y Quality Gate aprobado.


## Punto vigente para continuar - 14 de octubre de 2026

[E32: cobertura CI y Quality Gate](../evidencias/2026-10-14/stride-hardening-lab/README.md): **61a1f7a, CI 32/32 y Quality Gate passed**. Cobertura nueva Sonar **85,6 %**, mínimo 80 %; cobertura global Sonar **56,7 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites. E33 incorpora el cierre Sonar al PDF; E28 conserva el histórico d6c3440. [Avance](../AVANCE_ACTUAL_2026-10-14.md) · [Checkpoint](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md).


## Continuidad documental — 17 de octubre de 2026

El punto actual es el [checkpoint del 17 de octubre](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-17.md) y E35. La confirmación humana del otro PC no se confunde con primer acceso del laboratorio HTTPS local ni acepta riesgos residuales. Los cortes técnicos anteriores conservan sus SHA y métricas.
