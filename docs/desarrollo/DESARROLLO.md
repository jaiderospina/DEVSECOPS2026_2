# Manual de Desarrollo — IAM Secure

## Corte vigente - 14 de octubre de 2026

[E29: cobertura CI y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites.

El [informe PDF](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf) está generado y revisado (21 páginas, índice/autores/orden solicitado). [Avance vigente](../AVANCE_ACTUAL_2026-10-14.md) y [checkpoint de equipo](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) son el punto actual; los documentos fechados al 6/7 de octubre son históricos. Video/capturas finales, seis riesgos no aceptados, visibilidad y decisión de nueva release siguen pendientes.

Revisado: 14 de octubre de 2026 (America/Bogota).

## 1. Entorno y versiones

El entorno operativo se utiliza en Windows con PowerShell, Git y Docker Desktop/Compose. Python y Node locales son opcionales para desarrollo y pruebas; los servicios normales se construyen dentro de Docker. CI utiliza Python 3.14 para las suites/backend y Node 22 para frontend; modelo/SAST usan Python 3.12.

- **master:** base vigente integrada con Identity, Audit, workers, Permissions/grilla, Excel, inactividad, informe XLSX y automatización ZAP.
- **feat/bulk-users-excel-20261005:** carga Excel y corrección de inactividad publicada en el commit [624ab1d](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/commit/624ab1dc83e469c1b65b0e6fdd94c0524e4d3830); [PR #3](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/3) integrado en master mediante 19b54ee. Rama conservada como referencia histórica.
- Publicar un cambio en una rama no lo incorpora a master ni reconstruye los contenedores del PC.

Los estados y evidencias actuales se resumen en el [README](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/master/README.md#7-estado-actual-de-implementación).

## 2. Obtener y actualizar el proyecto

Clon nuevo:

```powershell
git clone https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final.git
Set-Location -LiteralPath 'DevSecOps-proyecto-Final'
git status --short --branch
```

Para continuar desde la base integrada en un clon limpio:

```powershell
git fetch origin
git switch master
git pull --ff-only origin master
```

Revisar y conservar cambios locales antes de actualizar; no usar reset o force push para descartarlos. Consultar git status antes de integrar; la sincronización verificada dejó C:/Prueba-ProyectoFinal limpia. Un cambio posterior requiere revisión propia.

## 3. Configuración y datos locales

En una instalación nueva:

```powershell
Copy-Item -LiteralPath '.env.example' -Destination '.env'
docker compose config --quiet
```

Completar los marcadores de PostgreSQL, JWT, clave Fernet MFA, SMTP y token interno de Audit según el [Manual de Despliegue](../despliegue/DESPLIEGUE.md). No sobrescribir un .env existente. La configuración expandida puede contener secretos; usar --quiet para la validación.

Git no transfiere usuarios ni datos del volumen PostgreSQL de otro PC. Una instalación nueva requiere inicialización y aprovisionamiento; clonar como colaborador no replica las cuentas existentes. E21 acredita instalación limpia completa en un iMac Intel independiente, con secretos/base nuevos; no copia datos del PC original.

## 4. Construcción, ejecución y migraciones

```powershell
docker compose build
docker compose up -d
docker compose ps
```

Para reconstruir solo los componentes del ajuste de inactividad, una vez actualizado su código:

```powershell
docker compose up -d --build identity frontend permissions-grid
docker compose exec -T identity printenv SESSION_INACTIVITY_MINUTES
```

El valor esperado es 5. Recargar el panel y abrir una grilla nueva desde una sesión activa después de reconstruir ambas entradas del frontend.

| Servicio | Puerto / función |
|---|---|
| frontend | 5173, panel React |
| permissions-grid | 127.0.0.1:5176, pestaña abierta desde el panel |
| identity | 8003, API FastAPI |
| permissions | 127.0.0.1:8005, API por usuario/compañía |
| audit-service | 127.0.0.1:8004 |
| postgres | 5433 en host, 5432 en Docker |
| sync-worker / audit-dispatcher | Workers sin puerto HTTP |
| identity-bootstrap | Perfil bootstrap; ejecución puntual |

Los SQL de postgres-init se ejecutan automáticamente al inicializar un volumen vacío. Un volumen existente necesita el procedimiento explícito de migración de cada etapa; reiniciar Compose no aplica los SQL nuevos. Consultar [Permissions](../PERMISOS_ETAPA_1.md) y [carga Excel en su rama](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/docs/CARGA_MASIVA_EXCEL.md). No borrar el volumen para aplicar una migración.

Detener conservando datos:

```powershell
docker compose down
```

## 5. Código y suites

| Área | Código | Pruebas |
|---|---|---|
| Identity | servicios/identity-service | tests/identity_http |
| Permissions | servicios/permissions-service | tests/permissions |
| Sync | servicios/sync-service | tests/sync_worker |
| Audit | servicios/audit-service | tests/audit_service |
| Dispatcher | servicios/audit-dispatcher | tests/audit_dispatcher |
| Frontend/grilla | servicios/frontend | tests/permissions_ui |
| Excel (etapa 2) | módulos cargas_* de Identity y BulkUsersPage del frontend | tests/bulk_users, tests/bulk_ui |
| Inactividad (etapa 2) | App, PermissionsWindow, usePermissionWindow y seguridad.py | tests/session_idle |

## 6. Ejecutar pruebas

### 6.1 Pytest por servicio

Pytest ya está integrado en CI. Recoge también las suites unittest existentes; se ejecutan en procesos separados por servicio para evitar colisiones entre módulos llamados main. No ejecutar todas las suites conjuntamente ni interpretar conteo de casos como cobertura.

Ejemplo de Identity HTTP/CORS, desde la raíz del repositorio y con Python disponible:

```powershell
python -m venv venv/identity-http
& './venv/identity-http/Scripts/python.exe' -m pip install -r servicios/identity-service/requirements.txt pytest==9.0.3 httpx==0.28.1
& './venv/identity-http/Scripts/python.exe' -m pytest tests/identity_http -q
```

Esta suite utiliza una aplicación de prueba y el middleware real; no importa la autenticación/base de datos ni utiliza credenciales del PC.

Para Sync, Audit y Dispatcher, crear un entorno separado por servicio, instalar su requirements.txt y pytest==9.0.3 y ejecutar respectivamente:

```text
python -m pytest tests/sync_worker -q
python -m pytest tests/audit_service -q
python -m pytest tests/audit_dispatcher -q
```

Resultados históricos comprobados: Sync 23, Audit 13, Dispatcher 22 e Identity HTTP 6. Los logs del run concreto son la fuente del conteo vigente.

### 6.2 Integración con PostgreSQL

tests/permissions y tests/bulk_users necesitan PostgreSQL y migraciones reales. Sus fixtures ejecutan TRUNCATE y crean datos ficticios: se deben ejecutar exclusivamente en una base efímera de pruebas, nunca sobre iam_secure ni su volumen operativo.

El workflow proporciona una base por job:
- permissions-tests: iam_permissions_test; instala dependencias de Permissions/Identity, aplica todos los SQL y crea una clave efímera para integración HTTP con Identity en 18003.
- bulk-users-tests, en etapa 2: iam_bulk_test; aplica migraciones y simula el envío SMTP.

Para reproducir esa integración, ejecutar el workflow DevSecOps mediante workflow_dispatch seleccionando la rama correspondiente, o seguir exactamente la preparación de esos jobs en [.github/workflows/devsecops-pipeline.yml](../../.github/workflows/devsecops-pipeline.yml). Los comandos de ejecución, una vez preparado el entorno efímero, son:

```text
python -m pytest tests/permissions -q
python -m pytest tests/bulk_users -q
```

La segunda suite está integrada en master. Cada suite se ejecuta en su proceso/job. El correo simulado no acredita recepción en un buzón real.

### 6.3 Lint, build y navegador

Con Node/npm disponibles:

```powershell
npm ci --prefix servicios/frontend
npm run lint --prefix servicios/frontend
npm run build --prefix servicios/frontend
```

Para las pruebas de navegador, instalar Playwright en un directorio de herramientas aislado:

```powershell
npm install --prefix venv/browser-tests --ignore-scripts playwright@1.63.0
& './venv/browser-tests/node_modules/.bin/playwright.cmd' install chromium
$env:PLAYWRIGHT_MODULE = (Resolve-Path -LiteralPath 'venv/browser-tests/node_modules/playwright').Path
```

Iniciar las dos entradas de la SPA compilada en terminales separadas:

```powershell
npm run preview --prefix servicios/frontend -- --host 127.0.0.1 --port 5173
```

```powershell
npm run preview --prefix servicios/frontend -- --host 127.0.0.1 --port 5176
```

Desde una tercera terminal en la raíz:

```powershell
node tests/permissions_ui/check.mjs
node tests/bulk_ui/check.mjs
node tests/session_idle/check.mjs
```

Las dos últimas pertenecen a etapa 2. La suite de inactividad permite BROWSER_CHANNEL=msedge como alternativa local y STATIC_DIST_DIR para servir un build mediante interceptación. La ejecución local anterior usa Vite Preview. El CI del commit 9b6affc utiliza Chromium contra dos contenedores Nginx reales, con los mismos contratos API simulados.

En el PC, un intento previo de lint fue bloqueado por Control de aplicaciones de Windows al cargar oxlint; el job frontend-lint del nuevo CI sí aprobó. No se cambió la protección de Windows.

La suite de inactividad utiliza reloj controlado y APIs simuladas. Comprueba cinco escenarios: vencimiento de carga aunque logout no responda; actividad real en grilla y probes sin renovación API; vencimiento independiente de grilla; cierre manual sin esperar red; interacción después de suspensión sin revivir sesión. No crea cuentas ni envía correos reales.

## 7. Git, pre-commit y revisión

El hook Gitleaks Docker está configurado en .pre-commit-config.yaml. Con Python/pre-commit y Docker disponibles:

```powershell
python -m pip install pre-commit
pre-commit install
git diff --check
git status --short
git check-ignore -v .env
```

Para revisar el contenido preparado:

```powershell
git diff --cached --check
git diff --cached --name-status
```

Mantener cambios temáticos, Conventional Commits (feat:, fix:, docs:, test:, security:, refactor:, chore:) y revisión por PR antes de integrar. Las ramas actuales usan feat/; nuevos trabajos deben respetar los disparadores del workflow. Si se utiliza otro prefijo, añadirlo explícitamente a los triggers o validar mediante PR/workflow_dispatch.

La revisión comprende diff, pruebas relacionadas, secretos, compatibilidad de Compose, RBAC/compañías y documentación. No introducir contraseñas, cuerpos de login, JWT/JTI, códigos TOTP o QR en logs, commits o evidencias.

## 8. CI vigente y pendientes

La optimización de la rama de etapa 2 compila con Node y sirve el bundle con Nginx
stable-alpine-slim, como usuario nginx y en el mismo puerto 5173. permissions-grid
reutiliza la imagen en el puerto externo 5176. El runtime no contiene Node, npm,
node_modules ni las fuentes React. Vite Preview sigue disponible para desarrollo.

[CI de contenedores 37572601777](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37572601777):
27/27 trabajos, 147 Pytest, 11 comprobaciones Chromium en Nginx y seis pruebas Node
de configuración aprobados. Siete sondas UID no root; arranque HTTP del frontend
verificado. [Evidencia](../evidencias/2026-10-06/CONTENEDORES_CI_9b6affc.json).

Para ejecutar las seis pruebas de configuración desde la raíz:

```powershell
node --test tests/frontend_container/config.test.mjs
```

La [guía de imágenes y Docker Hub](../despliegue/IMAGENES_Y_DOCKERHUB.md) documenta
el workflow manual preparado, versión/etiquetas, token y requisitos de activación.
El workflow está habilitado en master y la publicación Docker Hub 1.0.0 terminó en el [run 37574847806](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37574847806), 29/29 trabajos aprobados. Las siete imágenes tienen 1.0.0/latest, con 14 descargas y digests coincidentes por imagen. [Resumen duradero](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json); la integración en master está completada. E24 acredita CD de 1.0.0 y E21 instalación independiente desde fuente; una nueva release requiere validación propia.


CI ya implementa Gitleaks, Semgrep, Bandit, pip-audit, npm audit, Pytest, validación del modelo, siete builds/Trivy CRITICAL, lint y navegador; gate exige éxito de sus controles requeridos, incluido ZAP en el espejo; el CI directo del espejo espera y exige el Quality Gate Sonar (los callers reutilizables conservan su omisión explícita). El nuevo test de inactividad está incorporado a frontend-ui en etapa 2 y guarda reports/session-idle.txt.

Las acciones están fijadas a SHA y las herramientas principales a versiones. La mayoría de artefactos tienen retención de siete días; ZAP staging conserva treinta días; conservar evidencia durable revisada para la entrega.

El [CI del ajuste 624ab1d](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37570583715) aprobó **27 trabajos, 147 Pytest y 11 comprobaciones Chromium**, incluidas las cinco nuevas de inactividad. [Evidencia durable](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/docs/evidencias/2026-10-06/INACTIVIDAD_CI_624ab1d.json). Este resultado acredita ese código, no un HEAD futuro.

E22 conserva 69 % local de cinco servicios. E29 acredita cobertura CI importada y Quality Gate aprobado (88,1 % nueva, 54,5 % global) en f87243e; E21 acredita instalación limpia. Continúan nueva release si se decide, riesgos no aceptados, capturas/video y acceso público. IaC/CD conservan sus evidencias. Pytest cumple la alternativa del requisito; no se exige además Jest.

## 9. Evidencias y aceptación

- [Validación Sync](../SYNC_WORKER_VALIDACION.md) y [Audit](../AUDIT_VALIDACION.md).
- [Permissions](../PERMISOS_ETAPA_1.md).
- [ZAP: corrección CSP y retest autenticado](../evidencias/2026-09-30/IAM_Secure_CSP_retest.md).
- [CI de etapa 2](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37414395017): 147 Pytest y seis comprobaciones Chromium para el código 0b3ad04.
- [Pruebas locales de carga e inactividad](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/master/docs/VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md).
- [Historial de avances](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/master/docs/HISTORIAL_AVANCES_2026-10-06.md).

Grilla, carga masiva e inactividad funcionan según las pruebas y confirmación local. La ampliación del lote con Facturación/Logística sigue pausada hasta disponer de correos funcionales. Esa aceptación no sustituye ZAP del nuevo alcance, auditoría local o reproducción integral en otro PC.

## Documentación del alcance actual — 7 de octubre de 2026

Arquitectura, Despliegue, Usuario, cuatro UML y matriz fueron actualizados por revisión de código. El manual incorpora ocho capturas aportadas y distingue aceptación local de pruebas simuladas y pendientes. [Arquitectura](../arquitectura/ARQUITECTURA.md) · [Despliegue](../despliegue/DESPLIEGUE.md) · [Usuario](../usuario/MANUAL_USUARIO.md) · [Matriz](../trazabilidad/MATRIZ_REQUISITOS.md).

## SCA de dependencias

[Trivy SCA](../seguridad/SCA_TRIVY.md) añade inventarios de dependencias resueltas por servicio y coverage/gate obligatorio. Ejecutar python -m unittest discover -s tests/sca -v para las ocho regresiones. Los manifiestos UTF-8/BOM y UTF-16/BOM se normalizan únicamente en el staging. Los informes conservan paquetes, CVEs y severidades; HIGH/CRITICAL bloquean, incluidas las sin corrección.

[Evidencia](../evidencias/2026-10-07/SCA_TRIVY_20261007.json): ocho manifiestos validados localmente, seis jobs Python aprobados en CI y fixture vulnerable rechazada. Ese bloqueo corresponde al corte histórico del repositorio principal; E27 acredita posteriormente CI del espejo. No se declara resuelta la facturación del principal.

## Tratamiento STRIDE verificado - laboratorio local

[Perfil seguro](../seguridad/STRIDE_HARDENING_LAB.md) y [E32](../evidencias/2026-10-14/stride-hardening-lab/README.md): 61a1f7a, [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Sonar nueva 85,6 %/global 56,7 %, Quality Gate passed. TLS/roles/rate/backup se probaron en perfil independiente; reset MFA/outbox atómicos y alertas son código común. La migración 13 debe aplicarse a volúmenes existentes antes de reconstruir Permissions, conservando datos/.env. El Compose de desarrollo mantiene HTTP/DB administrativo. Seis riesgos siguen Open/no aceptación posterior; el equipo debe revisar adopción, límites y decisión residual. E29/E30 mantienen su corte histórico.
