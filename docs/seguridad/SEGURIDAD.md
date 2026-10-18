# Manual de Seguridad — IAM Secure

## Corte vigente - 14 de octubre de 2026

[E29: cobertura CI y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites.

El [informe PDF](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf) está generado y revisado (21 páginas, índice/autores/orden solicitado). [Avance vigente](../AVANCE_ACTUAL_2026-10-14.md) y [checkpoint de equipo](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) son el punto actual; los documentos fechados al 6/7 de octubre son históricos. Video/capturas finales, seis riesgos no aceptados, visibilidad y decisión de nueva release siguen pendientes.

> **Revisado:** 14 de octubre de 2026 (America/Bogota)

## 1. Principios

IAM Secure aplica defensa en profundidad, mínimo privilegio, separación de responsabilidades, externalización de secretos y trazabilidad.

## 2. Contraseñas

- no se almacenan en texto plano;
- se utiliza Argon2;
- las contraseñas temporales se generan en backend;
- existe cambio obligatorio;
- existe expiración configurable;
- el administrador no recibe hashes;
- la API no devuelve contraseñas ni hashes.

## 3. JWT y sesiones

Los JWT incorporan `jti`.

La sesión correspondiente se persiste en PostgreSQL y puede revocarse antes de la expiración criptográfica del token.

Se revocan sesiones ante eventos sensibles como cambios de identidad, rol, estado, compañía, contraseña y MFA cuando corresponde.

### Control de inactividad

La política predeterminada del ajuste publicado es cinco minutos. Identity comprueba la sesión persistida y revoca por inactividad; el frontend aplica su límite local y verifica también el vencimiento tras suspensión/foco.

El panel elimina inmediatamente su token y contexto antes de solicitar /auth/logout, con plazo de red de cinco segundos. La grilla recibe expiresAt por el canal autorizado y retira sus datos/controles al vencer. Los probes entre ventanas no son actividad humana ni consultan/renuevan la API. Una interacción después del vencimiento no revive la sesión.

La corrección y su suite están publicadas en la rama de etapa 2, commit [624ab1d](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/commit/624ab1dc83e469c1b65b0e6fdd94c0524e4d3830), integrada en master mediante el PR #3. El usuario confirmó SESSION_INACTIVITY_MINUTES=5 y expiración visible en carga y grilla. Se necesitan panel/grilla reconstruidos y recargados para utilizar el mismo protocolo.

## 4. MFA/TOTP

El MFA utiliza TOTP.

El secreto se protege mediante una clave Fernet configurada localmente.

No registrar ni incluir en auditoría:

- secreto TOTP;
- código OTP/TOTP;
- URI `otpauth`;
- QR.

El material de configuración MFA solo se presenta al usuario autorizado durante el enrolamiento; no se incorpora a evidencias públicas.

## 5. RBAC

Roles actuales:

```text
ADMIN_TI
ADMIN_SOPORTE
LIDER_FACTURACION
LIDER_LOGISTICA
LIDER_GESTION_HUMANA
```

La autorización se implementa en backend.

## 6. Multitenancy

El acceso administrativo de `ADMIN_SOPORTE` se restringe a compañías activas expresamente asignadas.

Las verificaciones se realizan contra PostgreSQL y no dependen únicamente de información suministrada por el cliente.

## 7. Secretos

El archivo `.env` se mantiene fuera de Git.

`.env.example` contiene únicamente marcadores.

Secretos sensibles incluyen:

- contraseña PostgreSQL;
- JWT secret;
- clave MFA;
- token interno de Audit;
- contraseña SMTP;
- contraseñas de bootstrap.

No ejecutar comandos que impriman configuración expandida con secretos si no es necesario.

## 8. Contenedores

Los Dockerfiles propios declaran usuarios no-root; el CI del commit 9b6affc aprobó sondas de UID efectivo no root para las siete imágenes. Para frontend se verificaron también el proceso principal y el arranque HTTP. Estas sondas no sustituyen la verificación integral del arranque de cada backend con PostgreSQL.

El frontend multietapa usa Node solo para compilar y Nginx stable-alpine-slim para servir el bundle en 5173 como nginx. La imagen final excluye Node, npm, node_modules y fuentes React; .dockerignore excluye .env. La política CSP se comparte con Vite Preview y se genera durante el build. Los hosts se limitan mediante server_name y un servidor predeterminado devuelve 403 a los restantes. Se conservan las cabeceras en errores; archivos ocultos están bloqueados y assets inexistentes reciben 404.

Los workers no exponen puertos.

Audit Service se publica mediante `127.0.0.1:8004`; Permissions mediante `127.0.0.1:8005` y grilla mediante `127.0.0.1:5176` en el Compose local.

## 9. Sync Worker

Controles:

- `FOR UPDATE SKIP LOCKED`;
- propiedad mediante `worker_id`;
- reintentos;
- recuperación de jobs interrumpidos;
- errores almacenados de forma controlada;
- apagado por señales;
- sin JWT, MFA o SMTP en su entorno.

## 10. Auditoría

El evento se sanitiza antes de persistirse en Outbox.

Audit Service aplica una segunda sanitización.

Campos y patrones sensibles incluyen contraseñas, tokens, credenciales, secretos, TOTP, OTP, QR y material criptográfico.

Los objetos no soportados no se convierten mediante `str()`; se representan como `[UNSUPPORTED_TYPE]`.

## 11. Audit Service

Controles principales:

- token interno dedicado;
- comparación segura;
- validación estricta;
- tamaño máximo de detalle;
- errores genéricos hacia el cliente;
- logs sin cuerpo sensible;
- idempotencia por `evento_uuid`;
- sin endpoints de modificación/eliminación.

## 12. Auditoría append-only

La tabla `auditoria_eventos` bloquea `UPDATE` y `DELETE` mediante trigger.

Esto protege la integridad operativa de la evidencia, aunque un administrador de base de datos con privilegios suficientes siempre requiere controles organizacionales adicionales.

## 13. Eventos administrativos

Cobertura actual:

```text
USUARIO_CREADO
USUARIO_MODIFICADO
USUARIO_ESTADO_MODIFICADO
USUARIO_ROL_MODIFICADO
MFA_RESTABLECIDO_ADMIN
COMPANIA_CREADA
COMPANIA_MODIFICADA
COMPANIA_ASIGNADA
COMPANIA_REASIGNADA
COMPANIA_DESASIGNADA
COMPANIA_ESTADO_MODIFICADO
```

Además existen eventos de login, sesiones, contraseña y MFA.

## 14. Pruebas de seguridad y resiliencia

Audit:

- sanitización;
- autenticación interna;
- validación de entrada;
- límite de tamaño;
- manejo seguro de errores;
- healthcheck;
- idempotencia;
- reintentos;
- recuperación;
- concurrencia.

Resultados:

```text
Audit Service: 13/13
Audit Dispatcher: 22/22
Total Audit: 35/35
```

Sync Worker:

```text
23/23
```

## 15. Permissions y carga masiva

Permissions valida la sesión con Identity y restringe acciones por rol, usuario y compañía. No conserva las claves JWT/MFA de Identity. La grilla conserva la sesión recibida en memoria y valida ventana, origen exacto y nonce del canal entre pestañas.

La rama de Excel permite solo compañías asignadas y roles de líder admitidos; separa validación/confirmación y conserva resultados por fila. No recibe contraseñas en el archivo. Los nuevos líderes reciben las tres vistas de su área; la grilla administra excepciones. Un duplicado se rechaza sin modificar la cuenta existente.

La aceptación local documenta creación de una cuenta, rol, duplicado, exportación, excepción de permisos e inactividad. La prueba de varias filas con correos funcionales permanece pausada.

## 16. Threat Dragon y STRIDE

El [modelo Threat Dragon 2.6.2](../diagramas/threat-model/README.md) contiene DFD nivel 0 y nivel 1 actualizados al alcance vigente. La [matriz STRIDE](stride-matrix.md) contiene T01–T20 distribuidas en seis categorías, con paridad entre modelo y matriz validada. El estado vigente es **18 amenazas Open y T13/T15 Mitigated**.

El modelo incorpora Permissions/grilla, carga Excel y los flujos adicionales del alcance actual. Los DFD fueron revisados visualmente y exportados como evidencia el 13 de octubre de 2026. La decisión humana de riesgo residual quedó registrada para el alcance académico/local: T13/T15 están `Mitigated`; otras doce amenazas Open tienen riesgo residual aceptado solo para ese alcance; T03, T04, T06, T07, T10 y T14 permanecen Open con riesgo residual no aceptado y tratamiento pendiente. Esta aceptación no equivale a aceptación productiva. [Evidencia de aceptación](../evidencias/2026-10-13/ACEPTACION_RIESGO_RESIDUAL.md).

## 17. Herramientas y política vigente de CI

| Control | Implementación y configuración | Estado |
|---|---|---|
| Secretos | Hook Gitleaks Docker v8.24.3; CI analiza historial con redacción, reporte JSON y salida de fallo. | Integrado y probado; instalar hook en cada clon. |
| SAST | Semgrep 1.140.0 con reglas OWASP/Python/JavaScript y Bandit 1.8.6. | Validación local vigente: Semgrep analizó 94 archivos con 233 reglas y 0 findings; Bandit no reportó hallazgos de severidad/confianza MEDIUM o superior. Las aprobaciones de CI citadas se conservan como evidencia histórica. |
| SCA Python | pip-audit/Trivy y revisión adicional con Snyk para dependencias runtime. | Runtime vigente revisado sin vulnerabilidades conocidas dentro del alcance ejecutado; no implica SCA global en cero. |
| SCA frontend | npm audit/Trivy y revisión adicional con Snyk del runtime frontend. | Runtime frontend revisado dentro del alcance actual; los hallazgos residuales documentados pertenecen al tooling, no al código runtime de IAM Secure. |
| SCA literal del requisito | Trivy sobre manifiestos/locks y dependencias resueltas; HIGH/CRITICAL bloqueantes. | Job aprobado en f87243e. E24 conserva diez manifiestos/dos MEDIUM de asteval en tooling Checkov; Snyk histórico también documenta ply transitivo. Riesgo residual de tooling separado del runtime, sin afirmar SCA global en cero. |
| Imágenes | Siete imágenes Docker propias; Trivy 0.65.0, CRITICAL, exit-code 1, incluidas CVEs sin corrección. | Integrado y con gate; la evidencia histórica acredita build y escaneo de las siete imágenes antes de publicación. |
| Pruebas | Pytest por servicio, integración PostgreSQL/Identity, Permissions, carga Excel, lint y navegador. | La evidencia histórica de etapa 2 conserva 147 Pytest; el cierre local vigente ejecutó 245 pruebas aprobadas, incluidas 92 de T13 y 29 de T15. El número de pruebas no equivale a porcentaje de cobertura. |
| Modelo | Validación automática del JSON/esquema/referencias y paridad T01–T20 entre Threat Dragon y matriz STRIDE. | Integrada; DFD 0/1 revisados visualmente y exportados. Estado validado: 18 Open y 2 Mitigated (T13/T15), con decisión humana de riesgo residual documentada. |
| DAST | ZAP 2.17.0 con validación pasiva y laboratorio activo controlado GET-only. | E26 acredita automatización en CI: 7 scans, 39 combinaciones API/rol y 1.947 requests sin alertas dentro de ese alcance, reportes HTML/JSON, gate MEDIUM/HIGH y limpieza. Cobertura activa de flujos mutables, login/MFA y XLSX pendiente. |
| IaC | Ansible, Checkov y validador propio de Compose. | Producción simulada probada: 29/29 trabajos, idempotencia y persistencia. [E10](../evidencias/2026-10-07/ANSIBLE_CD_37578596462.json). PR #3 integrado en master; E24 añade validación CI/CD en el espejo. |
| Monitorización | Prometheus/Grafana, Loki/ELK y Falco. | Opcionales, sin implementar. |

El [workflow](../../.github/workflows/devsecops-pipeline.yml) ya es funcional. El gate final requiere success en todos los jobs; no se utiliza continue-on-error para aprobar controles fallidos. Acciones fijadas a SHA y herramientas principales a versión; las bases CVE y reglas remotas pueden cambiar entre ejecuciones. Artefactos con retención de siete días.

## 18. Cabeceras de respuesta

Frontend compilado: CSP script-src 'self', style-src 'self' sin unsafe-inline/unsafe-eval; img-src 'self' data: blob: para QR; conexiones API restringidas a orígenes locales/configurados; frame-ancestors 'none', X-Frame-Options DENY, nosniff, Permissions-Policy y Referrer-Policy.

CI comprueba CSP de estilos y falla ante unsafe-inline. La corrección trasladó estilos MFA a CSS. Vite permite el host de pruebas host.docker.internal exacto y rechaza hosts no autorizados.

Identity: nosniff y CORP same-origin; CORS utiliza orígenes explícitos configurados. Pruebas HTTP/CORS cubren respuestas y preflight de su alcance, no todos los errores posibles. HTTP local no constituye evidencia de TLS/HSTS de producción.

Permissions: `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` y `Cross-Origin-Resource-Policy: same-origin` se aplican mediante el middleware de cabeceras existente. CORP limita las cargas desde otros orígenes en modo `no-cors`; las solicitudes CORS autorizadas conservan su política actual. No sustituye autenticación ni autorización. No se modifican CORS, autenticación ni endpoints. El retest pasivo ZAP posterior a la reconstrucción registró 119 PASS, 0 WARN y 0 FAIL; este resultado acredita el alcance pasivo ejecutado y no sustituye el DAST activo controlado ni un escaneo completo de la aplicación.

Audit: `X-Content-Type-Options: nosniff` se aplica mediante middleware ASGI a respuestas normales, documentación y errores HTTP. `Cross-Origin-Resource-Policy` no se fuerza en el alcance actual porque Audit es un servicio interno publicado solo en `127.0.0.1:8004` y no sirve recursos destinados a ser embebidos por navegadores; esta decisión debe revisarse si cambia su exposición o función.

## 19. ZAP: evidencia y límites

| Prueba | Resultado documentado | Alcance |
|---|---|---|
| Frontend — pasivo vigente | 64 PASS, 3 WARN, 0 FAIL. | Las advertencias restantes corresponden al alcance pasivo documentado; no equivalen por sí solas a vulnerabilidades explotables. |
| Identity API — pasivo | 119 PASS, 0 WARN, 0 FAIL. | Validación pasiva del servicio; no sustituye pruebas activas de autenticación o MFA. |
| Audit API — pasivo | 118 PASS, 1 WARN, 0 FAIL. | WARN de Cross-Origin-Resource-Policy aceptado y documentado por tratarse de un servicio interno publicado en localhost. |
| Permissions API — pasivo | 119 PASS, 0 WARN, 0 FAIL. | Resultado posterior a la corrección de cabeceras y reconstrucción del servicio. |
| DAST activo controlado | 7 scans, 39 combinaciones API/rol, 1.947 requests y 0 alertas dentro del alcance ejecutado. | Laboratorio aislado GET-only con cinco reglas activas LOW; sin spider/AJAX, mutaciones, login/MFA, carga XLSX ni canal entre ventanas. |
| Baseline frontend histórico | Siete URL, 63 PASS, 4 WARN, 0 FAIL, salida 2. | Evidencia anterior a las correcciones finales de CSP/cabeceras; se conserva como trazabilidad histórica. |
| Retest autenticado histórico | Login, MFA y /auth/me 200; panel ADMIN_TI observado. | Safe Mode Docker/Webswing; evidencia pasiva histórica, no cobertura completa de roles y rutas. |

La evidencia histórica de septiembre se conserva en [Registro final](../evidencias/2026-09-30/IAM_Secure_CSP_retest.md), [History](../evidencias/2026-09-30/IAM_Secure_ZAP_History_retest.png), [Alerts](../evidencias/2026-09-30/IAM_Secure_ZAP_Alerts_retest.png) y [detalle MFA](../evidencias/2026-09-30/IAM_Secure_ZAP_MFA_alert_detail.png).

El DAST activo controlado manual está archivado en [dast-active-readonly](../evidencias/2026-10-11/dast-active-readonly/SUMMARY.md). No se acredita un active scan completo ni ausencia global de vulnerabilidades: el laboratorio se limitó a operaciones GET, cinco reglas activas de baja intensidad, sesiones sintéticas y servicios aislados. POST/PUT/PATCH/DELETE, login/MFA, carga XLSX, canal entre ventanas y otros flujos mutables quedaron deliberadamente fuera. [E26](../evidencias/2026-10-13/zap-staging-ci/README.md) acredita posteriormente la automatización contra staging del mismo alcance GET-only.

## 20. Interpretación de reportes

- **Gitleaks:** distinguir secreto real, falso positivo, marcador o credencial revocada. Si es real, revocar/rotar y tratar la exposición; no publicar el valor.
- **Semgrep/Bandit:** registrar regla, archivo/línea, severidad, confianza, explotabilidad, controles y acción; no descartar sin análisis.
- **SCA:** registrar componente/versión, CVE/advisory, versión corregida y decisión. Actualizar y repetir auditoría/tests.
- **Trivy:** revisar cada CVE crítica; la política vigente bloquea también las no corregidas. Una excepción requiere impacto, justificación, control compensatorio, responsable y fecha de revisión.
- **ZAP:** vincular endpoint, regla, riesgo/confianza, evidencia, reproducción y retest. Una alerta informativa de autenticación o sesión no demuestra una vulnerabilidad. PASS con -S no prueba ataques activos.

La actualización de PyJWT 2.14.0 a 2.15.0 después del hallazgo SCA y la retirada de unsafe-inline tienen [registros de corrección, auditoría y retest](../evidencias/2026-09-30/IAM_Secure_CSP_retest.md). El [CI b7704bc](../evidencias/2026-09-30/IAM_Secure_CI_b7704bc.json) conserva el resumen histórico.

## 21. Gestión de vulnerabilidades

Detección → validación → clasificación → responsable → corrección/mitigación/aceptación → reprueba → cierre documentado.

Estados: ABIERTO, EN_ANALISIS, EN_CORRECCION, MITIGADO, ACEPTADO, RESUELTO y FALSO_POSITIVO. Toda aceptación requiere justificación explícita; no suprimir reglas, rebajar severidad o excluir CVEs solo para obtener un pipeline verde.

Conservar tabla de hallazgos con severidad, estado, evidencia, decisión y responsable. Sanitizar reportes: no guardar Authorization, contraseñas, JWT/JTI, cuerpos de autenticación o material MFA. El resumen CI no sustituye los reportes íntegros revisados.

## 22. Evidencias y trabajo restante

[CI de contenedores 37572601777](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37572601777): **27/27 trabajos, 147 Pytest, 11 comprobaciones Chromium contra Nginx y seis pruebas Node aprobados**. Ocho imágenes/Trivy CRITICAL y UID no root, frontend sin herramientas de build y reducción del 94,83 %. [Registro duradero](../evidencias/2026-10-06/CONTENEDORES_CI_9b6affc.json).

[Publicación Docker Hub verificada](../despliegue/IMAGENES_Y_DOCKERHUB.md): reutiliza CI, escanea todas las imágenes antes de push, usa token de Actions por stdin y valida descargas/digests. DOCKERHUB_TOKEN permitió autenticar y publicar 1.0.0/latest: [run 37574847806](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37574847806), 29/29 trabajos aprobados. Las ocho imágenes se construyeron y pasaron Trivy CRITICAL antes del primer push; UID no root y guard del frontend aprobados. Se verificaron las 14 descargas y la coincidencia de digests por imagen; [registro duradero](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json). El token no se leyó ni se solicitó. La integración de etapa 2 en master está completada mediante PR #3; la descarga anónima conserva su alcance pendiente. La instalación limpia en un segundo computador ya fue validada de extremo a extremo el 13 de octubre y cuenta con evidencia versionada. El despliegue Ansible de las imágenes por digest en CI tiene [evidencia de producción simulada](../evidencias/2026-10-07/ANSIBLE_CD_37578596462.json).

[CI del ajuste 624ab1d](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37570583715): **27/27 trabajos aprobados, 147 Pytest y 11 comprobaciones Chromium**. Incluye cinco escenarios de inactividad, lint, SAST/SCA, Gitleaks, siete builds/Trivy y gate. [Resumen durable](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/docs/evidencias/2026-10-06/INACTIVIDAD_CI_624ab1d.json).

- [CI master 37566343307](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37566343307): 26 trabajos aprobados para 9e2020f.
- [CI etapa 2 37414395017](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37414395017): 27 trabajos, 147 Pytest y seis comprobaciones Chromium para 0b3ad04.
- [Permisos](../PERMISOS_ETAPA_1.md), [Audit](../AUDIT_VALIDACION.md), [Sync](../SYNC_WORKER_VALIDACION.md).
- [Pruebas locales de carga/inactividad](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/master/docs/VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md).
- [Estado académico vigente](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/master/README.md#7-estado-actual-de-implementación).

Los controles de T13/T15 cuentan con [evidencia de integración local](../evidencias/2026-10-13/T13_T15_VALIDACION.md): 92 pruebas T13, 29 T15 y 124 regresiones, 245 aprobadas. Tras la revisión humana, T13/T15 están `Mitigated` y su riesgo residual fue aceptado explícitamente para el alcance académico/local. Siguen pendientes revisión de los issues Sonar y validación CI de futuras revisiones, reportes finales, cobertura DAST fuera de GET-only, tratamiento de T03/T04/T06/T07/T10/T14 y entrega académica. La instalación limpia y ZAP automatizado en el staging definido por E26 ya no forman parte de los pendientes. Los controles funcionales implementados conservan su evidencia, pero CI no resuelve por sí solo esos riesgos o entregables.

## Documentación del alcance actual — 7 de octubre de 2026

Arquitectura, Despliegue, Usuario, cuatro UML y matriz fueron actualizados por revisión de código. El manual incorpora ocho capturas aportadas y distingue aceptación local de pruebas simuladas y pendientes. [Arquitectura](../arquitectura/ARQUITECTURA.md) · [Despliegue](../despliegue/DESPLIEGUE.md) · [Usuario](../usuario/MANUAL_USUARIO.md) · [Matriz](../trazabilidad/MATRIZ_REQUISITOS.md).
## Actualización del modelo — 13 de octubre de 2026

DAST activo archivado en f624196: laboratorio aislado, GET controlado, 39 combinaciones API/rol, 7 scans, 1.947 requests, 0 alertas en ese alcance. docs/evidencias/2026-10-11/dast-active-readonly/SUMMARY.md. No es active scan completo de toda la aplicación ni cubre mutaciones, login/MFA o canal entre ventanas. [Evidencia archivada](../evidencias/2026-10-11/dast-active-readonly/SUMMARY.md): f624196 publica los resultados del laboratorio ejecutado sobre 2b0abd4, con cinco reglas LOW y sesiones sintéticas, sin spider/AJAX spider. No acredita carga XLSX, mutaciones, canal postMessage ni reset MFA.

T13/T15: tratamiento técnico probado localmente. T13 acredita RBAC/multitenancy y pérdida inmediata de alcance con 92 pruebas (negativas y controles positivos). T15 acredita ambas rutas MFA con 29 pruebas: jerarquía/compañía, revocación de sesiones y desafíos, rechazo del token anterior en Identity y Permissions y nuevo enrolamiento TOTP antes de emitir sesión definitiva. /usuarios/{id}/mfa/restablecer ahora rechaza objetivos inactivos con HTTP 400 tras validar jerarquía y compañía. Se conserva deliberadamente el contrato sin MFA previo: /auth 200 y /usuarios 409. Regresión: Identity 6, Permissions 32 y Excel 86; total 245 aprobadas. [Evidencia, alcance y limitaciones](../evidencias/2026-10-13/T13_T15_VALIDACION.md). Tras la decisión humana documentada, T13 y T15 están `Mitigated` y su riesgo residual fue aceptado para el alcance académico/local. El reset /auth registra auditoría después del COMMIT, por lo que T06 permanece Open con riesgo residual no aceptado y tratamiento pendiente. [Aceptación de riesgo residual](../evidencias/2026-10-13/ACEPTACION_RIESGO_RESIDUAL.md).

Excel limita archivos a 2 MiB, 500 filas y ZIP expandido a 10 MiB; bloquea macros/vínculos externos e invalida filas con fórmulas. La cuota de diez lotes por diez minutos/actor se verifica después del parsing; no cubre todo el consumo previo. T17–T20 separan permisos, canal, integridad XLSX y disponibilidad de carga; T17–T20 permanecen Open; el modelo completo contiene 18 Open y T13/T15 Mitigated.


## CI/CD en repositorio espejo — 13 de octubre de 2026

[E24: CI/CD del espejo](../evidencias/2026-10-13/ci-espejo/README.md) conserva 28/28 trabajos CI y 30/30 CD aprobados para 8262da2, coincidente en ambos repositorios. Semgrep se ejecuta en Docker manteniendo reglas y política de fallo. Trivy SCA verificó diez manifiestos con dos MEDIUM y cero HIGH/CRITICAL bloqueantes; el riesgo de tooling señalado por Snyk se mantiene separado. El CD probó Checkov, idempotencia y persistencia con imágenes 1.0.0, no una nueva publicación. Ese corte 8262da2 no tenía check SonarCloud. La ejecución posterior f026d19 aprobó 29/29 y Quality Gate passed, E25. Ese workflow histórico no invocaba las 121 pruebas específicas T13/T15; el corte E29 f87243e ya las ejecuta en CI con PostgreSQL efímero.


## Cierre SonarCloud del espejo — 13 de octubre de 2026

[E25: SonarCloud del espejo](../evidencias/2026-10-13/sonar-espejo/README.md): workflow CI de f026d19 aprobado (29/29), incluido el análisis real, y check externo **Quality Gate passed** para el proyecto del espejo. El check informa 45 issues nuevos y 0 % de cobertura de código nuevo; esta métrica no sustituye el 69 % local. Las notas E24/anteriores conservan sus cortes históricos. El resultado no acredita una nueva publicación/deploy Docker, elimina los riesgos residuales ni valida automáticamente posteriores commits.


## ZAP automatizado contra staging — 13 de octubre de 2026

[E26: ZAP automatizado](../evidencias/2026-10-13/zap-staging-ci/README.md) acredita la ejecución remota sobre 574bb3e8195c3583ebd973f33d7f48a738689f7d: 29/29 trabajos CI, escaneo activo GET-only de 7 API/rol y 39 operaciones, gate MEDIUM/HIGH, reportes HTML/JSON saneados y limpieza del proyecto efímero. Servicios construidos desde el checkout; datos/secretos nuevos, sin puertos host ni SMTP. No se usan el Compose, .env ni PostgreSQL local. Login/MFA, XLSX, mutaciones y frontend quedan fuera. E20 conserva su ejecución manual histórica; no se confunden sus cifras con E26.


### Resultado posterior de Sonar en master

[validación posterior de E26](../evidencias/2026-10-13/zap-staging-ci/README.md#validación-posterior-en-master-ci-aprobado-y-sonar-rechazado): `2d8b444` aprobó 30/30 jobs CI, pero el check externo Sonar rechazó el Quality Gate por cobertura nueva 0 %, duplicación 84,6 % y fiabilidad C. E25 es histórico. Este resultado es histórico. E29 documenta cobertura importada y Quality Gate aprobado; los controles y umbrales se conservaron.

El corte E29 ejecutó **86 pruebas de carga Excel y 121 específicas T13/T15** en CI con PostgreSQL efímero. El check externo Sonar informó **43 issues nuevos y cero aceptados**, con todas las condiciones del gate aprobadas; no equivale a resolver toda la deuda técnica ni los seis riesgos STRIDE no aceptados.

## Tratamiento STRIDE verificado - laboratorio local

[Perfil seguro](../seguridad/STRIDE_HARDENING_LAB.md) y [E32](../evidencias/2026-10-14/stride-hardening-lab/README.md): 61a1f7a, [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Sonar nueva 85,6 %/global 56,7 %, Quality Gate passed. TLS/roles/rate/backup se probaron en perfil independiente; reset MFA/outbox atómicos y alertas son código común. La migración 13 debe aplicarse a volúmenes existentes antes de reconstruir Permissions, conservando datos/.env. El Compose de desarrollo mantiene HTTP/DB administrativo. Seis riesgos siguen Open/no aceptación posterior; el equipo debe revisar adopción, límites y decisión residual. E29/E30 mantienen su corte histórico.
