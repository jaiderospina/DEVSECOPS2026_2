# Avance Threat Modeling y DevSecOps — 2026-09-30

Base inmutable revisada: `06a40d4768257b9ff110feeb099092da245ba847`.
Rama: `feat/threat-model-devsecops-20260930`. Master no se modifica.
No se accedió a .env; revisión desde GitHub, sin acceso al disco Windows.

## Evidencia disponible

- JSON Threat Dragon 2.6.2 validado contra esquema oficial versionado.
- Integridad validada: dos diagramas, flujos con extremos existentes, 16 amenazas abiertas y numeración única.
- Actionlint 1.7.12: workflow sin errores de sintaxis/expresiones.
- Pytest local (Python 3.12.14): Sync 23, Audit 13, Dispatcher 19 aprobadas.
- Primera ejecución local usa Pytest 9.1.1, FastAPI 0.142.1, SQLAlchemy 2.1.1; no equivale a validación del runtime Docker Python 3.14 y dependencias fijadas.
- Importación visual, capturas/exportación Threat Dragon y revisión humana: pendientes.
- GitHub Actions/build/escáneres: consultar ejecución real de esta rama; configuración no equivale a aprobación.

## Gates y alcance

| Control | Política |
|---|---|
| Gitleaks 8.24.3 | Historia completa, redactado, falla ante secretos |
| Semgrep 1.140.0 | p/owasp-top-ten, p/python, p/javascript; falla ante hallazgos |
| Bandit 1.8.6 | Código servicios/scripts, severidad y confianza media/alta |
| pip-audit 2.9.0 | 5 manifiestos Python, resuelve transitivas, falla ante vulnerabilidades |
| npm audit | Lockfile frontend, gate HIGH/CRITICAL, incluye dev dependencies |
| Pytest 8.4.2 | Suites existentes unittest recogidas por Pytest; proceso aislado por servicio |
| Docker build | 6 Dockerfiles incluyendo usuarios heredado; no publicación |
| Trivy 0.65.0 | Imágenes construidas, CVE CRITICAL incluyendo sin fix; exit-code 1 |
| Gate final | Todos los jobs deben terminar success |

No se usan continue-on-error ni exclusiones de CVE para lograr verde.
Fallos de descarga/resolución también fallan el gate.
Acciones GitHub fijadas a SHA; imágenes de herramientas fijadas a versión, digest aún pendiente.
Reglas Semgrep remotas y bases CVE cambian: registrar reportes del run para reproducibilidad.
Reportes privados con retención 7 días; Gitleaks redacta secretos. No publicar reportes sin revisión.
Pre-commit Gitleaks añadido; instalar localmente: `python -m pip install pre-commit && pre-commit install`. Activación en Windows pendiente.

## Pendientes conservados

ZAP, IaC, despliegue, Docker Hub, badges, cobertura global, prueba en segundo PC, repositorio público e informe final pendientes.
No se agrega badge verde sin ejecución.
CI no demuestra RBAC/MFA extremo a extremo ni concurrencia PostgreSQL real: las suites usan dobles.
ADMIN_TI → reset MFA ADMIN_SOPORTE sigue pendiente.
Auditoría append-only HTTP no constituye inmutabilidad DB: servicios comparten rol postgres.
Ver [STRIDE](seguridad/stride-matrix.md) y [modelo](diagramas/threat-model/README.md).

## Segunda validación local con dependencias fijadas

Se instalaron requisitos de audit-service (compartidos con worker/dispatcher) y Pytest 8.4.2 en directorio aislado. En Python 3.12.14: 23 + 13 + 19 = 55 pruebas aprobadas. Runtime Python 3.14 sigue pendiente de CI.

## Primera ejecución Actions y correcciones

Run [36682226520](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36682226520), commit 3d67184:
Gitleaks, cinco SCA Python, npm audit, 55 pruebas Python 3.14, esquema y seis builds/Trivy CRITICAL aprobados.
Gate final falló correctamente por Bandit B310 (audit_client.py:85) y Semgrep missing-user (frontend/Dockerfile:62).

Correcciones: frontend USER node; transporte Audit HTTP(S) explícito con validación de URL, TLS por defecto HTTPS y sin seguimiento de redirecciones. No se suprimen reglas.
Se añaden tres pruebas de esquema/credenciales URL, redirección y HTTPS. Dispatcher local: 22 pruebas aprobadas; total esperado 58. Bandit local pasa con el mismo gate.
Segunda ejecución Actions pendiente de revisar. Threat Dragon aún requiere revisión visual/exportación.

## Resultado CI confirmado

Commit funcional verificado: `ca43fae5bf398143e9ff1c010d29e4f4a34c799d`.
Run [36682579912](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36682579912): todos los 20 jobs expandidos aprobados, incluido gate final.
Gitleaks, Semgrep, Bandit, 5 SCA Python, SCA Node, modelo, 3 suites Pytest (23/13/22: 58 casos), 6 Docker build + Trivy CRITICAL.
La evidencia corresponde a ese commit, no a ejecuciones futuras ni al despliegue de producción.
Artefactos disponibles en Actions con retención de 7 días. Antes de entrega académica descargar y conservar reportes revisados.
Threat Dragon: JSON y referencias validados, apertura/exportación visual pendiente. Pre-commit: configuración versionada; activación en Windows pendiente.


## Complemento de avance — 30 de septiembre de 2026: Threat Modeling, CI y ZAP

Este complemento conserva el contenido anterior como registro histórico. Para las áreas de esta fase, el estado y la evidencia que siguen actualizan las referencias previas a trabajo pendiente. No sustituyen validaciones de alcance diferente.

### CI actualizado y conteo verificado

Evidencia: [Actions run 36690539507](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/36690539507), commit `fb620177af87abfdb87978fbb791d957767ef07c`: 21 jobs aprobados, incluido el gate final. Logs comprobados: Sync Worker 23, Audit Service 13, Audit Dispatcher 22 e Identity HTTP/CORS 6; total **64 pruebas Pytest** en Python 3.14.

Los 21 jobs expandidos incluyen cuatro suites Pytest (antes tres) y comprobaciones de arranque frontend no-root, host permitido/rechazado y headers. El suite identity_http valida CORS y respuestas 200/401/404/422 sin dependencias de DB/.env.

Esta ejecución acredita los gates correspondientes al commit indicado; un commit documental posterior puede generar otro run que debe evaluarse por separado. No mantener un badge aprobado por inferencia.

ZAP se ha ejecutado manualmente en Docker y no está integrado en el workflow. IaC y deploy continúan pendientes. Frontend/Identity recibieron correcciones tras evidencia local: build verde inicial no detectó permisos Vite, por eso se añadió smoke test.

Consultar [ZAP](ZAP_VALIDACION.md) y [checkpoint](CHECKPOINT_2026-09-30_ZAP.md) para cobertura y punto de pausa.
