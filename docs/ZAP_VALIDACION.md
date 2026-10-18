# ZAP — validación inicial

Reporte aportado por el usuario: ZAP 2.17.0, 2026-09-30 07:45:07 UTC, target http://host.docker.internal:5173.
Tres endpoints GET: /, /robots.txt, /sitemap.xml; todos 403, texto/plano. Una alerta informativa 10049 (contenido no almacenable); cero alertas de riesgo alto/medio/bajo.

Estado: escaneo sin cobertura válida del frontend, no evidencia de ausencia de vulnerabilidades. El reporte completo permanece en el PC del usuario; resumen transcrito, no archivado original.
Hipótesis consistente con configuración: preview de Vite rechaza Host host.docker.internal. Se permite ese host exacto y se añaden checks CI para 200 del host permitido y 403 de uno no permitido. Falta repetir el escaneo y confirmar contenido HTML y assets de la SPA.
API, sesión autenticada, rutas protegidas y análisis activo: pendientes. No cambiar caché por alerta informativa sobre respuestas 403.

## Segundo baseline — salida aportada por el usuario

Target http://host.docker.internal:5173/, 7 URLs; HTML, JS y CSS respondieron 200. PASS 60, WARN-NEW 7, FAIL 0; exit code 2.
Reportes originales en el PC: carpeta temporal iam-zap-20260930-025401. Solo se recibió salida de consola; JSON/HTML íntegros aún no archivados.

| Regla | Hallazgo | Tratamiento |
|---|---|---|
| 10020 | Anti-clickjacking ausente | CSP frame-ancestors none y X-Frame-Options DENY propuestos |
| 10021 | X-Content-Type-Options ausente | nosniff propuesto |
| 10038 | CSP ausente | CSP para bundle local, estilos React, QR blob y API local/configurada |
| 10063 | Permissions Policy ausente | Denegar camera/microphone/geolocation |
| 10049 | Storable but non-cacheable | Revisar HTML vs assets en servidor de despliegue; no cambiar datos autenticados a cache publica |
| 10109 | Modern Web Application | Informativa; usar navegador/client spider para explorar SPA |
| 90004 | COEP ausente/invalido | Pendiente evaluar aislamiento y compatibilidad; no suprimir regla |

Las politicas aplican a preview compilado, no al dev server HMR.
CSP permite solo los tres origenes API locales (localhost, 127.0.0.1, host.docker.internal:8003) mas origen VITE_API_URL configurado. Acceso por IP LAN requiere URL API publica explicita al construir y CORS correspondiente en backend.
Estilos inline conservados por componentes React existentes; script-src no permite unsafe-inline/unsafe-eval. QR permite blob/data solo en img-src.
Pendiente: repetir baseline, comprobar login y QR MFA en navegador y revisar consola CSP; no declarar hallazgos cerrados antes de esas pruebas.
No aplicar HSTS sobre HTTP local ni usar el PASS del baseline como prueba de TLS, RBAC, CSRF, MFA o sesiones.

## Retest frontend con headers

Salida aportada por usuario: 7 URL, PASS 63, WARN 4, FAIL 0, exit 2; carpeta temporal iam-zap-20260930-030310.
10020/10021/10038/10063 ya no aparecen como alertas en ese baseline. Pendientes: 10049 cache, 10055 style-src unsafe-inline, 10109 SPA informativa y 90004 COEP. Captura confirma panel ADMIN_TI cargado; no demuestra login nuevo ni paso MFA.

## Primer baseline API anonimo

Esquema reducido a GET / y GET /auth/me; servers host.docker.internal:8003; zap-api-scan.py -S.
Consola: 4 URLs importadas, PASS 116, WARN 2, FAIL 0, exit 2. Carpeta temporal iam-zap-api-20260930-030909.
Solo se recibio consola; revisar JSON para explicar las cuatro URL frente a dos operaciones definidas. No afirmar cuatro endpoints funcionales distintos.
Advertencias: 10021 nosniff ausente y 90004 CORP ausente en GET / (200).
El listado PASS incluye reglas activas aunque -S omite active scan; no acredita pruebas activas SQLi/XSS/RCE ni ausencia de filtracion .env.
Comprobacion manual aportada: openapi.json 200, auth/me sin token 401.

Correccion propuesta: ApiSecurityHeadersMiddleware agrega nosniff y CORP same-origin sin ampliar CORS ni cambiar status/cuerpo. Seis pruebas HTTP/CORS pasan localmente con dependencias fijadas y httpx 0.28.1, sin DB/.env. Suite añadida a Pytest CI.
CORP bloquea cargas cross-origin no-cors; llamadas fetch cors autorizadas siguen sujetas a CORSMiddleware. Validacion navegador login/MFA y retest ZAP pendientes. No se modifican auth, roles o rutas.

## Retest API anonimo confirmado — 2026-09-30

Salida de consola aportada por el usuario: ZAP api-scan -S, esquema limitado a GET / y GET /auth/me, 4 URL importadas, PASS 118, WARN 0, FAIL 0, exit 0. Inicio registrado 08:20:54 UTC (03:20:54 America/Bogota).
Reportes: api-baseline-retest.html y api-baseline-retest.json en carpeta temporal del PC; originales completos aun no archivados en repositorio.
Verificacion curl aportada: GET / 200 y GET /auth/me anonimo 401; ambos incluyen nosniff y CORP same-origin, 401 conserva WWW-Authenticate Bearer.
Las dos alertas 10021/90004 no reaparecen en este alcance. Resultado aprobado exclusivamente para baseline anonimo limitado; no acredita prueba activa SQLi/XSS/RCE ni cobertura autenticada/RBAC/MFA.
Login nuevo y MFA posterior a cambios de headers: pendiente confirmacion expresa; captura previa muestra panel, no el desafio MFA.


## Complemento de avance — 30 de septiembre de 2026: Threat Modeling, CI y ZAP

Este complemento conserva el contenido anterior como registro histórico. Para las áreas de esta fase, el estado y la evidencia que siguen actualizan las referencias previas a trabajo pendiente. No sustituyen validaciones de alcance diferente.

### Confirmación funcional y alcance final de esta pausa

El usuario confirmó expresamente completar cierre de sesión, nuevo login con contraseña, desafío MFA y carga del panel después de las correcciones. Esta confirmación complementa la captura previa; acredita compatibilidad funcional reportada, no captura de tráfico autenticado por ZAP ni prueba de enrolamiento QR.

Baseline API anónimo: dos alertas corregidas no reaparecieron; exit 0. Frontend sigue con cuatro WARN; no se declara seguridad completa.
ZAP Desktop todavía no tiene instalación/apertura confirmada; exploración proxy y análisis activo pendientes.

Evidencia: [Actions run 36690539507](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36690539507), commit `fb620177af87abfdb87978fbb791d957767ef07c`: 21 jobs aprobados, incluido el gate final. Logs comprobados: Sync Worker 23, Audit Service 13, Audit Dispatcher 22 e Identity HTTP/CORS 6; total **64 pruebas Pytest** en Python 3.14.

Los reportes completos ZAP y las URL adicionales importadas requieren revisión/archivo originales; solo se recibió consola. Próximo procedimiento exacto en [checkpoint](CHECKPOINT_2026-09-30_ZAP.md).


## Nuevo punto de pausa — instalador Windows bloqueado

El usuario aportó captura: Control Inteligente de Aplicaciones bloqueó el instalador ZAP_2_17_0_windows (1).exe. No se confirmó instalación de ZAP Desktop ni se desactivó la protección. La captura no permite determinar si la detección es correcta o falso positivo.

Se propone la alternativa oficial Docker/Webswing: https://www.zaproxy.org/docs/docker/webswing/
Comando entregado, **todavía sin ejecución ni arranque confirmado por el usuario**:

```powershell
docker run -d --rm --name iam-zap-ui -u zap -p 127.0.0.1:8080:8080 -p 127.0.0.1:8090:8090 ghcr.io/zaproxy/zaproxy:stable zap-webswing.sh
```

### Retomar exactamente aquí

1. Confirmar si el usuario ejecutó el comando y existe iam-zap-ui. Si no, iniciar Docker Desktop y ejecutar el comando.
2. Abrir http://localhost:8080/zap; ZAP se inicia al acceder a la interfaz. Seleccionar sesión sin persistencia y Safe Mode.
3. Solicitar captura de pantalla principal sin solicitudes sensibles.
4. Webswing no soporta Launch Browser: preparar perfil separado y proxy manual a 127.0.0.1:8090. No cambiar proxy global indiscriminadamente.
5. Dentro de Docker, localhost apunta al contenedor, no al PC. Planificar acceso al objetivo mediante host.docker.internal:5173 y API :8003 o una ruta verificada hacia el host.
6. Antes del login proxificado, revisar CORS_ORIGINS para el origen usado: host.docker.internal:5173 no se considera permitido por inferencia. No leer/imprimir secretos .env.
7. Explorar sesión autenticada y revisar Sites/History frontend+API y Alerts. Esta etapa sigue pendiente, igual que análisis activo, integración ZAP CI, IaC y despliegue.

No hay volumen host en el comando: no se guardan claves CA ni sesiones en el repositorio. No requiere importar CA para objetivos HTTP. El contenedor es temporal (--rm); decidir almacenamiento revisado de reportes antes de detenerlo.

Resultados previos siguen vigentes dentro de su alcance: login/MFA/panel confirmados por usuario; frontend baseline 4 WARN; API baseline anónimo limitado sin alertas. No se acredita aún tráfico autenticado a través de ZAP.
