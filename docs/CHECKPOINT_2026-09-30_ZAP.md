# Checkpoint de pausa — IAM Secure — 30/09/2026

## Reanudar desde este punto

Repositorio local del usuario: C:\Prueba-ProyectoFinal.
Repositorio GitHub: jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final.
Rama de trabajo: feat/threat-model-devsecops-20260930.
PR #1 en borrador: https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/1
Base funcional/documental antes de este checkpoint: b596dacd9e901f768eacd771e3ea249143f04e1b.
Master no modificado durante esta fase. No leer ni mostrar .env.

**Siguiente paso exacto:** instalar/abrir ZAP Desktop en Windows y preparar exploración manual autenticada en Safe Mode.
El usuario llegó a la página de descarga de ZAP 2.17.0; se indicó Windows (64) Installer.
No existe confirmación de descarga, instalación o apertura de ZAP Desktop.
No existe evidencia de exploración autenticada a través del proxy de ZAP.

## Evidencias y estado comprobado

- Pre-commit Gitleaks nativo falló por Control de aplicaciones Windows que bloqueó Go link.exe. No desactivar política.
- Hook cambiado a gitleaks-docker, imagen v8.24.3, --redact, --staged y pass_filenames false.
- Usuario ejecutó pre-commit: Passed; Gitleaks historial: 30 commits, no leaks found.
- Ajuste publicado por usuario en d8f5b30; working tree limpio en esa comprobación.
- Frontend no-root: corregido EACCES de .vite-temp; prueba CI arranque HTTP añadida.
- Vite preview permite host.docker.internal exacto; CI verifica host permitido 200 y no permitido 403.
- Frontend headers CSP, X-Frame-Options DENY, nosniff, Permissions-Policy y Referrer-Policy comprobados con curl.
- API headers nosniff y CORP same-origin comprobados en / (200) y /auth/me anónimo (401), conservando WWW-Authenticate Bearer.
- Usuario confirmó expresamente cerrar sesión, nuevo login con contraseña y MFA y carga del panel tras cambios de headers.
  Esta es prueba funcional reportada por el usuario; no sustituye un escaneo autenticado.
- Captura aportada previamente: panel ADMIN_TI y cuatro compañías.
- No se recibieron credenciales, JWT, códigos MFA ni archivos .env.

## ZAP

| Prueba | Resultado | Alcance / limitación |
|---|---|---|
| Primer frontend | Tres respuestas 403 | No válido para evaluar SPA |
| Segundo frontend | 7 URL; PASS 60, WARN 7, FAIL 0; exit 2 | Público y pasivo |
| Retest frontend con headers | 7 URL; PASS 63, WARN 4, FAIL 0; exit 2 | Público y pasivo |
| API anónima inicial | PASS 116, WARN 2, FAIL 0; exit 2 | Esquema limitado a GET / y GET /auth/me; -S |
| Retest API | PASS 118, WARN 0, FAIL 0; exit 0 | Mismo alcance limitado; 4 URL importadas según consola |

Advertencias frontend todavía abiertas:
- 10049 caché: revisar HTML frente a assets en servidor de despliegue.
- 10055 style-src unsafe-inline: React utiliza estilos inline; retirar requerirá refactorización.
- 10109 Modern Web Application: informativa; explorar SPA con navegador.
- 90004 COEP: evaluar compatibilidad y aislamiento, no suprimir sin justificación.

Alertas API 10021 y 90004 no reaparecieron en retest anónimo limitado.
-S omite escaneo activo: los PASS listados para SQLi/XSS/RCE NO son evidencia de ejecución de esas pruebas.
Esquema original completo no se usó para escaneo para evitar operaciones mutantes.
Explicar 4 URL importadas consultando JSON, no asumir cuatro endpoints funcionales distintos.

Reportes completos permanecen en PC del usuario; no se han recibido ni archivado originales HTML/JSON.
Carpetas temporales reportadas:
- C:\Users\jeanc\AppData\Local\Temp\iam-zap-20260930-030310
- C:\Users\jeanc\AppData\Local\Temp\iam-zap-api-20260930-030909
API retest: api-baseline-retest.html y api-baseline-retest.json.
Conservar originales revisados antes de borrar temporales; no publicar cuerpos de login ni headers Authorization.

## CI

Última evidencia comprobada al guardar:
- Commit b596dac: https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36689565188 — completed/success.
- Commit f293a44: https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36688839630 — completed/success.
- Gates Gitleaks, Semgrep, Bandit, SCA Python/Node, Pytest, modelo, Docker build y Trivy.
- Suites previas 58 casos + nueva suite identity_http 6 casos = 64 casos esperados; consultar artefactos para conteo de CI.
- Nueva suite HTTP/CORS: 6 passed localmente con dependencias fijadas, sin DB ni .env.
- Gate Trivy por CRITICAL incluye vulnerabilidades sin fix.
- Reportes Actions tienen retención 7 días; conservar evidencia antes de expiración.
No equiparar CI aprobado a seguridad completa o despliegue validado.

## Threat Modeling y otros pendientes

Modelo Threat Dragon 2.6.2: DFD 0/1 y esquema/referencias validados; 16 amenazas STRIDE abiertas.
Importación visual, exportación de diagramas y revisión humana pendientes.
ADMIN_TI → restablecer MFA de ADMIN_SOPORTE sigue pendiente; no modificado en esta fase.
Roles DB postgres compartidos, HTTP local, aislamiento y demás riesgos conservan sus pendientes.
ZAP autenticado y activo aún no acreditados.
Integración automatizada ZAP en pipeline, IaC/Checkov, despliegue/TLS, Docker Hub y demás requisitos finales siguen pendientes.

## Procedimiento inmediato al retomar

1. Leer este checkpoint y docs/ZAP_VALIDACION.md; revisar branch/head y estado local sin .env.
2. Confirmar si ZAP Desktop ya está instalado. Si aparece Java o bloqueo de Windows, revisar mensaje sin desactivar controles.
3. Abrir sesión sin persistencia; Safe Mode; Quick Start → Manual Explore.
4. URL http://localhost:5173/; HUD desactivado; Launch Browser.
5. En navegador lanzado por ZAP, login/MFA y consultar Panel, Administradores de soporte, Compañías, Roles y permisos, Sesiones y Mi perfil.
6. Comprobar Sites/History con localhost:5173 y localhost:8003; esperar análisis pasivo.
7. Compartir solo resumen de Alerts/endpoints/códigos; jamás cuerpos de autenticación o Authorization.
8. Registrar cobertura y hallazgos; no cerrar requisitos sin evidencia.


## Complemento de avance — 30 de septiembre de 2026: Threat Modeling, CI y ZAP

Este complemento conserva el contenido anterior como registro histórico. Para las áreas de esta fase, el estado y la evidencia que siguen actualizan las referencias previas a trabajo pendiente. No sustituyen validaciones de alcance diferente.

### Complementación de los manuales existentes

Se añadieron secciones de avance a README, Arquitectura, Desarrollo, Despliegue, Seguridad, Usuario, Matriz, Avance y registros CI/ZAP, conservando íntegros sus contenidos previos.

Evidencia: [Actions run 36690539507](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36690539507), commit `fb620177af87abfdb87978fbb791d957767ef07c`: 21 jobs aprobados, incluido el gate final. Logs comprobados: Sync Worker 23, Audit Service 13, Audit Dispatcher 22 e Identity HTTP/CORS 6; total **64 pruebas Pytest** en Python 3.14.

Conteo esperado del checkpoint anterior ya comprobado en logs: **64 casos aprobados**. El punto de reanudación no cambia: confirmar ZAP Desktop y explorar sesión autenticada en Safe Mode. Los originales ZAP y exportaciones Threat Dragon siguen pendientes.


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
