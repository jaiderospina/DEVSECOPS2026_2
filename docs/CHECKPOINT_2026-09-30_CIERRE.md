# Checkpoint de cierre — IAM Secure — 30/09/2026

Fecha de referencia: America/Bogota. Preparación del avance académico para el 01/10/2026.

## Retomar desde aquí

- Repositorio local: `C:\Prueba-ProyectoFinal`.
- Repositorio GitHub: [jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final).
- Rama técnica: `feat/threat-model-devsecops-20260930`.
- [PR #1](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/1): abierto y en borrador; no fusionado.
- Último commit funcional comprobado: `b7704bcffd7e64e79fd05b68f9d54189959e67bb`.
- La actualización documental posterior conserva ese commit como referencia de pruebas. Al retomar, verificar el HEAD documental más reciente y el estado local.
- README: se agrega un resumen de cierre; se conservan el contenido original y los complementos anteriores.
- Entorno local: imagen identity reconstruida, PyJWT 2.15.0 confirmado, frontend construido con CSP corregida. Después de ZAP se inició identity con Compose habitual sin override temporal.
- No leer ni publicar `.env`, contraseñas, JWT, códigos MFA ni cuerpos de autenticación.

**Siguiente paso recomendado:** revisar/importar el modelo Threat Dragon 2.6.2 en la interfaz, ajustar su presentación y exportar DFD nivel 0/1 y reporte; conservar 16 amenazas abiertas hasta revisar cada control.

## Avances previos conservados

- 29/09: Sync Worker, 23 pruebas; dos workers procesaron ocho trabajos una sola vez; clon limpio reproducible. Commits `dd8508d` y `8c07ba6`.
- 30/09, sesión inicial: Audit Service/Outbox/Dispatcher y documentación base; cuatro diagramas UML, manuales y matriz académica. La evidencia de auditoría conserva sus resultados originales y límites.
- Rama de avance: modelo Threat Dragon, DFD 0/1, 16 amenazas STRIDE, workflow CI, Gitleaks local en Docker, SAST/SCA/build/Trivy, middleware de cabeceras Identity y pruebas HTTP/CORS. Los complementos de manuales del commit `3e1a497` permanecen intactos.
- Baselines ZAP anteriores: frontend público con WARN pendientes en aquella ejecución; API anónima limitada sin alertas. No convertir PASS de `-S` en ejecución de pruebas activas.

## Cierre de la sesión actual

1. ZAP nativo fue bloqueado por Windows; se utilizó Docker/Webswing sin desactivar la protección.
2. Contenedor de ZAP: `iam-zap-web`, imagen `ghcr.io/zaproxy/zaproxy:stable`, volumen `iam-zap-web-work`. GUI: `http://localhost:8080/zap/`; proxy: `127.0.0.1:8090`.
3. Navegación de prueba mediante Edge con perfil separado y proxy, objetivo `host.docker.internal:5173`, API `:8003`.
4. CORS se permitió temporalmente mediante un override ubicado en TEMP. Se comprobó preflight 200 y origen exacto. Al terminar se ejecutó `docker compose up -d --no-deps identity` sin ese override. No se consultaron otra vez las cabeceras CORS tras restaurar.
5. CSP: se retiraron estilos inline MFA, se mantuvo el soporte QR `blob:`, se usó `style-src 'self'` y se agregó el smoke test de CI. Commit `3093975`.
6. Lint: estado React no utilizado retirado; spread de headers simplificado; script `oxlint src vite.config.js --deny-warnings`. Resultado local en contenedor: salida 0, sin advertencias ni errores. No hay un nuevo job dedicado a lint.
7. CI de `3093975` detectó PyJWT 2.14.0 vulnerable. Se actualizó únicamente esa versión a 2.15.0, conservando la codificación UTF-16 de requirements.txt. Commit `b7704bc`.
8. Validación aislada PyJWT en Python 3.12.14: pip-audit sin vulnerabilidades conocidas, seis pruebas HTTP/CORS y checks de firma/expiración/payload recursivo aprobados.
9. CI Python 3.14 de `b7704bc`: 21 jobs success en push y PR; 64 Pytest (23/13/22/6). SCA identity, frontend CSP y gate final success.
10. Contenedor identity reconstruido: `jwt.__version__` devuelve 2.15.0.
11. Retest autenticado: login, MFA y /auth/me 200 en History; panel ADMIN_TI observado. Alerts muestra únicamente tres categorías informativas, con cuatro instancias visibles. No aparece CSP unsafe-inline.
12. Restauración de Compose habitual confirmada por salida del usuario. El cierre de Edge/ZAP no se confirmó; no asumir contenedor ZAP detenido ni sesión guardada.

## Evidencia durable

- [Registro detallado y límites](evidencias/2026-09-30/IAM_Secure_CSP_retest.md).
- [Resumen CI](evidencias/2026-09-30/IAM_Secure_CI_b7704bc.json).
- [History](evidencias/2026-09-30/IAM_Secure_ZAP_History_retest.png).
- [Alerts](evidencias/2026-09-30/IAM_Secure_ZAP_Alerts_retest.png).
- [Detalle MFA](evidencias/2026-09-30/IAM_Secure_ZAP_MFA_alert_detail.png).
- [Auditoría PyJWT corregido](evidencias/2026-09-30/IAM_Secure_pip-audit_PyJWT_2.15.0.json).
- [JUnit HTTP/CORS local](evidencias/2026-09-30/IAM_Secure_pytest_identity_PyJWT_2.15.0.xml).
- [CI push](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36814230828) y [CI PR](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36814237618).
- [Modelo](diagramas/threat-model/README.md) y [STRIDE](seguridad/stride-matrix.md).

Los reportes completos originales de baseline ZAP no se recibieron ni se archivaron aquí; las PNG corresponden al retest manual observado. No hay reporte completo de escaneo activo. El resumen CI conserva resultados fuera de la retención de artefactos Actions de siete días; no sustituye todos los artefactos originales.

## Pendientes conservados

- Threat Dragon: revisión visual/exportación/revisor y 16 amenazas abiertas.
- Pruebas negativas E2E de RBAC y multitenancy; enrolamiento QR; gap ADMIN_TI → reset MFA ADMIN_SOPORTE.
- ZAP activo con plan de alcance y datos de prueba; automatización ZAP/staging.
- IaC, Checkov/tfsec, orquestación de producción simulada, TLS y roles DB separados.
- Docker Hub/versionado, cobertura/badges, segundo PC, manual con capturas, PDF y video.
- Repositorio privado; resolver acceso del profesor o visibilidad de entrega sin cambiarla automáticamente.
- PR técnico sin merge; la portada README resume la rama, no acredita integración de código a master.

## Procedimiento de reanudación

1. Leer este checkpoint y la sección de avance consolidado del README.
2. Revisar rama, HEAD, `git status --short` y nuevos commits remotos. No hacer force push.
3. Consultar el run CI del HEAD concreto si hubo cambios después de `b7704bc`.
4. Retomar Threat Dragon con el modelo existente; ejecutar `python scripts/validate_threat_model.py` después de guardar cambios.
5. Exportar/revisar DFD y reporte, actualizar la matriz con evidencia y decisión del revisor.
6. Continuar con las pruebas de autorización y plan ZAP activo; luego IaC/Checkov y despliegue.
