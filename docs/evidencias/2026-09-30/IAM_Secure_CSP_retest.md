# IAM Secure — Corrección CSP y validación local

## Hallazgo inicial

ZAP 2.17.0 identificó la alerta 10055-6, CSP: style-src unsafe-inline, de riesgo medio y confianza alta. Las dos instancias correspondían a GET y HEAD de la misma URL: http://host.docker.internal:5173/. La cabecera permitía style-src 'self' 'unsafe-inline'.

## Corrección revisada

Se trasladaron los estilos inline de los componentes MFA de App.jsx a clases en App.css, conservando los valores visuales. La política de Vite usa ahora style-src 'self' y mantiene img-src 'self' data: blob: para el QR. El workflow comprueba esta directiva y falla si la CSP contiene unsafe-inline. Se retiró un estado sin uso y el fallback innecesario del spread de headers. El script lint quedó como oxlint src vite.config.js --deny-warnings.

## Evidencia disponible

- La salida de PowerShell compartida por el usuario muestra una reconstrucción exitosa del frontend.
- La petición HEAD a través del proxy ZAP devolvió HTTP 200 y style-src 'self', sin unsafe-inline. Fecha de esa respuesta: 01 de octubre de 2026, 03:27:55 UTC (30 de septiembre, 22:27:55 en Bogotá).
- En una sesión nueva de ZAP, la captura de GET de la raíz muestra la cabecera corregida. El panel de alertas mostrado contiene únicamente Modern Web Application, de nivel informativo; la alerta CSP anterior no aparece en ese panel.
- El lint ejecutado dentro del contenedor con src vite.config.js --deny-warnings --format stylish finalizó sin advertencias ni errores y con código de salida 0, según la salida proporcionada por el usuario.
- git diff --check no mostró errores de espacios. El aviso LF/CRLF en package.json corresponde a conversión de saltos de línea.
- El diff adjunto y los archivos locales fueron revisados: package.json es JSON válido y no quedan atributos style={...} en App.jsx.

## Alcance y pendientes

El retest documenta la corrección del hallazgo CSP en la raíz del frontend observada. No acredita un escaneo activo completo ni cobertura de todas las rutas, roles o flujos MFA. Las capturas anteriores al retest muestran login, verificación MFA y /auth/me con HTTP 200; no corresponden a una nueva validación autenticada completa después del cambio. El usuario indicó que las pantallas se veían bien, pero el enrolamiento QR no cuenta con una prueba visual específica documentada.

La nueva comprobación CSP pasó en el job images (frontend) de la ejecución push 36813081386 para el commit 3093975. El pipeline completo terminó en failure por la auditoría Python de identity-service. Los cinco archivos se guardaron inicialmente en bb1598f. El rebase sobre aded712 terminó sin conflictos y el push publicó 3093975cd5c917b3f3c22b5eed39b2e46387d2eb. La lectura del commit en GitHub confirma los cinco cambios revisados. El hook local de detección de secretos pasó, según la salida del usuario. El cambio del script npm fue validado por lectura y parseo del archivo; el comando subyacente equivalente pasó antes de editar ese script.

Este registro resume las salidas y capturas compartidas en el chat. No sustituye un reporte exportado de ZAP. No incluye contraseñas, tokens ni datos de sesión.

## Publicación y CI

PR existente: https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/1 (borrador).

GitHub Actions inició dos ejecuciones DevSecOps para el commit 3093975: push 36813081386 y pull_request 36813084539. En la primera consulta estaban en ejecución y en cola, respectivamente. La ejecución push 36813081386 terminó en failure. El job sca-python (identity-service) encontró PyJWT 2.14.0 afectado por GHSA-42vr-xj54-vc7v (CVE-2026-101918), con fix_versions 2.15.0, según pip-audit.json del artefacto 11140820962. El job images (frontend), que comprueba la nueva CSP, terminó en success.

## Corrección del bloqueo SCA

Se aplicó localmente el cambio único PyJWT==2.14.0 a PyJWT==2.15.0 en servicios/identity-service/requirements.txt, conservando la codificación UTF-16 y los saltos de línea originales. Se verificó por comparación de bytes que esa versión es el único cambio.

La candidata se validó en un entorno Python aislado en Windows: pip-audit de las dependencias del servicio terminó con código 0 y sin vulnerabilidades conocidas; las seis pruebas HTTP existentes pasaron; las comprobaciones de JWT válido, firma incorrecta, expiración y payload recursivo también pasaron. Las pruebas HTTP cubren cabeceras y CORS, no el flujo completo de autenticación. La validación local usó Python 3.12.14; la nueva ejecución de GitHub CI con Python 3.14 también terminó en success.

Reportes guardados: IAM_Secure_pip-audit_3093975.json (hallazgo original), IAM_Secure_pip-audit_PyJWT_2.15.0.json (auditoría local corregida), IAM_Secure_pytest_identity_PyJWT_2.15.0.xml (seis pruebas HTTP).

El intento de commit desde la terminal de Codex falló en el hook pre-commit por herramientas/intérprete no disponibles en ese entorno. No se creó un commit ni se hizo push de la actualización PyJWT. El usuario completó después el commit y el push desde su PowerShell: b7704bcffd7e64e79fd05b68f9d54189959e67bb. El hook Detect hardcoded secrets pasó.

Fuente de la corrección: https://github.com/advisories/GHSA-42vr-xj54-vc7v y https://github.com/jpadilla/pyjwt/releases/tag/2.15.0.

## Publicación de la actualización PyJWT

GitHub confirmó el commit b7704bcffd7e64e79fd05b68f9d54189959e67bb, con únicamente servicios/identity-service/requirements.txt modificado. Se iniciaron las ejecuciones DevSecOps push 36814230828 y pull_request 36814237618 para ese commit. En la primera consulta ambas estaban en cola; ambas finalizaron posteriormente en success, con 21 jobs exitosos cada una.

## Resultado final de CI para b7704bc

Las ejecuciones push y pull_request terminaron en success. Cada una completó 21 jobs exitosos, incluyendo sca-python (identity-service), images (frontend) y gate.

- Push: https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36814230828
- Pull request: https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36814237618

Los logs de los cuatro jobs Pytest de la ejecución pull_request confirman 64 casos aprobados: sync_worker 23, audit_service 13, audit_dispatcher 22 e identity_http 6. No se añadieron pruebas al repositorio en esta actualización.

El PR #1 permanece abierto y en borrador, con head b7704bcffd7e64e79fd05b68f9d54189959e67bb; no fue fusionado. El archivo IAM_Secure_CI_b7704bc.json conserva el resumen de jobs y resultados consultados.

El usuario reconstruyó la imagen local de identity y el contenedor arrancó. La consulta dentro del contenedor confirmó PyJWT 2.15.0. Los límites de cobertura del retest ZAP descritos arriba siguen vigentes.

## Verificación del contenedor local actualizado

La salida proporcionada por el usuario confirma imagen prueba-proyectofinal-identity construida y contenedor iam-secure-identity iniciado. La consulta de jwt.__version__ dentro del contenedor devolvió PyJWT: 2.15.0.

El preflight OPTIONS de http://host.docker.internal:8003/auth/me, enviado mediante el proxy http://127.0.0.1:8090 con Origin http://host.docker.internal:5173 y cabecera solicitada authorization, respondió HTTP 200 OK, access-control-allow-origin exactamente http://host.docker.internal:5173 y las cabeceras de seguridad nosniff y cross-origin-resource-policy: same-origin. Fecha de respuesta: 01 de octubre de 2026 a las 04:23:49 UTC (30 de septiembre a las 23:23:49 en Bogotá).

Este preflight valida CORS para el origen de pruebas; no autentica al usuario ni demuestra el resultado de GET /auth/me. El retest manual posterior fue respaldado por la captura History descrita al final de este registro; el árbol Alerts posterior se revisó y muestra únicamente los tres tipos informativos registrados en la sección final.

## Retest autenticado después de actualizar PyJWT

El usuario compartió primero la pantalla de verificación MFA y después el panel principal con rol ADMIN_TI. La captura ZAP History posterior, en Safe Mode, muestra:

| ID | Método y ruta visibles | Estado |
| --- | --- | --- |
| 19 | POST /auth/login | 200 OK |
| 22 | POST /auth/mfa/verificar-… (URL truncada en la captura) | 200 OK |
| 24 | GET /auth/me | 200 OK |

La ruta MFA completa no es legible en la tabla; la secuencia, el prefijo visible y la navegación observada son consistentes con /auth/mfa/verificar-login. La captura muestra también preflights OPTIONS 200 de login, MFA y /auth/me. Los horarios visibles son 04:25:53 y 04:26:59 del 01/10/26, tal como aparecen en ZAP.

Esta evidencia respalda el login con segundo factor y la consulta del usuario autenticado tras activar PyJWT 2.15.0. No acredita controles de autorización de todos los roles. El panel superior conserva una respuesta de la raíz del frontend con Date 03:32:47 GMT y style-src self; no se toma esa respuesta anterior como una nueva petición CSP de este retest.

La captura History quedó guardada como IAM_Secure_ZAP_History_retest.png. La captura actual del árbol Alerts fue revisada y archivada; el resultado se detalla en la sección final.

## Cierre del retest pasivo observado

La captura del árbol completo mostrado contiene tres tipos de alertas, todos con icono informativo:

| Tipo | Instancias visibles | Interpretación |
| --- | --- | --- |
| Authentication Request Identified | 1, POST /auth/login | Identifica una petición de autenticación; no demuestra una vulnerabilidad. |
| Modern Web Application | 2, GET de la raíz del frontend | Identifica características de la aplicación web; no demuestra una vulnerabilidad. |
| Session Management Response Identified | 1, POST /auth/mfa/verificar-login, confirmado en el detalle de la alerta | Identifica una respuesta de gestión de sesión; no demuestra una vulnerabilidad. |

La categoría seleccionada Authentication Request Identified muestra explícitamente Risk: Informational. Las otras dos se identifican por los iconos informativos y las reglas ZAP previamente revisadas. No aparece CSP: style-src unsafe-inline en este árbol, ni categorías de riesgo bajo, medio o alto. La conclusión se limita al tráfico pasivo y al árbol mostrado, junto con las respuestas HTTP y las cabeceras documentadas. No acredita un escaneo activo completo ni una prueba de todos los permisos o rutas.

El retest pasivo del flujo observado queda completado: PyJWT 2.15.0 activo; CORS del origen ZAP validado; login, verificación MFA y /auth/me con respuestas 200 en el historial; acceso al panel ADMIN_TI observado; alerta CSP anterior ausente; pipeline del commit b7704bc aprobado en sus dos ejecuciones, con 21 jobs por ejecución y 64 pruebas Pytest.

Captura archivada: IAM_Secure_ZAP_Alerts_retest.png. El registro no incluye contraseñas ni tokens.

Referencias de las reglas: https://www.zaproxy.org/docs/alerts/10111/, https://www.zaproxy.org/docs/alerts/10109/, https://www.zaproxy.org/docs/alerts/10112/.

Al terminar las pruebas, el usuario ejecutó docker compose up -d --no-deps identity sin el override temporal. Compose informó que iam-secure-identity inició correctamente. Esto confirma la ejecución del restablecimiento con Compose habitual; no se hizo una nueva consulta de las cabeceras CORS después de ese comando.

## Detalle adicional de la alerta de sesión

Una captura posterior confirma explícitamente la URL http://host.docker.internal:8003/auth/mfa/verificar-login, Risk: Informational, Confidence: High y Parameter/Evidence: access_token para Session Management Response Identified (regla pasiva 10112). La imagen muestra el nombre del campo, sin su valor. Esto completa la identificación de la ruta MFA que estaba truncada en History y confirma el nivel informativo de esta categoría. No constituye por sí mismo una prueba de vulnerabilidad en la sesión.

Captura adicional archivada: IAM_Secure_ZAP_MFA_alert_detail.png. El resultado del retest pasivo observado permanece cerrado con únicamente las tres categorías informativas visibles.

## Cierre de la configuración temporal

La salida final del usuario confirma que docker compose up -d --no-deps identity terminó correctamente y el contenedor iam-secure-identity quedó iniciado. El comando omitió el override de CORS usado para ZAP. No cambia los commits aprobados ni reconstruye otra versión de PyJWT.

La fase de corrección CSP, limpieza lint, actualización PyJWT, validación CI y retest pasivo del flujo observado queda completada con las limitaciones de cobertura ya documentadas. La ventana Edge de pruebas no tiene un cierre confirmado en la evidencia; se recomendó cerrarla y volver a http://localhost:5173/ desde el navegador habitual.
