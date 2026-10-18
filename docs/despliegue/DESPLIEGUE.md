# Manual de Despliegue y Operación — IAM Secure

## Guía de instalación vigente — 17 de octubre de 2026

Para ejecutar en otro PC, siga el [manual detallado Windows/Linux](../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.md) o su [PDF](../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.pdf). Incluye configuración propia, SMTP, primer acceso/MFA y pruebas funcionales. [Checkpoint actual](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-17.md). La confirmación humana de primer acceso/MFA en otro PC no acepta riesgos residuales.

## Corte histórico E29 - 14 de octubre de 2026

[E29: cobertura CI y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites.

El [informe PDF](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf) está generado y revisado (21 páginas, índice/autores/orden solicitado). [Avance vigente](../AVANCE_ACTUAL_2026-10-14.md) y [checkpoint de equipo](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) describen el corte histórico; los documentos fechados al 6/7 de octubre son históricos. Video/capturas finales, seis riesgos no aceptados, visibilidad y decisión de nueva release siguen pendientes.

Revisado: 14 de octubre de 2026. Las secciones 1–10 describen desarrollo local y el procedimiento reproducible validado en un segundo computador. La sección 11 documenta producción simulada con Ansible/Compose, implementada y probada en etapa 2; integración del PR #3 completada en master. E24 añade CI/CD aprobado en el espejo para 8262da2.

## 1. Versión y requisitos

Git, Docker Desktop con motor Linux o Docker Engine y Docker Compose v2. No se necesita Python ni Node en el host para iniciar servicios. Puertos host: 5173, 5176, 8003, 8004, 8005 y 5433.

El alcance Excel/inactividad/Nginx y auditoría está integrado en master mediante el PR #3. La corrección Semgrep de 8262da2 coincide en el repositorio principal y el espejo. Las imágenes Docker Hub 1.0.0 siguen representando su revisión histórica.

## 2. Instalación nueva

~~~powershell
git clone https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final.git
Set-Location -LiteralPath .\DevSecOps-proyecto-Final
git switch master
git status --short --branch
Copy-Item -LiteralPath .env.example -Destination .env
~~~

El repositorio es privado: la cuenta GitHub necesita acceso. Ese acceso no crea usuarios de IAM ni copia PostgreSQL. En otro PC se inicia otra base, con secretos y cuentas propios; las identidades del PC original viven en su volumen de base de datos.

Editar .env por el canal local privado. Reemplazar los marcadores, sin publicar sus valores:

| Variable | Uso |
|---|---|
| POSTGRES_PASSWORD | Acceso PostgreSQL |
| JWT_SECRET / JWT_ALGORITHM / JWT_EXPIRE_MINUTES | Firma y política de tokens |
| MFA_ENCRYPTION_KEY | Clave válida de cifrado del secreto TOTP |
| AUDIT_INTERNAL_TOKEN | Audit Dispatcher → Audit Service |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM | Entrega de credenciales |
| SESSION_INACTIVITY_MINUTES | Límite backend; cinco minutos |
| VITE_SESSION_INACTIVITY_MINUTES | Límite del bundle; cinco minutos |
| CORS_ORIGINS / PERMISSIONS_CORS_ORIGINS | Orígenes web permitidos |
| VITE_API_URL / VITE_PERMISSIONS_API_URL | URLs públicas incluidas al compilar |
| BOOTSTRAP_ADMIN_TI_PASSWORD | Solo aprovisionamiento inicial explícito |

La clave MFA debe tener formato Fernet válido; JWT y token Audit deben ser independientes. No introducir secretos en VITE_*. Cambiar VITE_* requiere reconstruir frontend y grilla.

## 3. Validación e inicio

~~~powershell
docker compose config --quiet
git check-ignore -v .env
docker compose build
docker compose up -d
docker compose ps
~~~

Los servicios normales son postgres, identity, frontend, permissions, permissions-grid, sync-worker, audit-service y audit-dispatcher. identity-bootstrap es puntual y solo corre con el perfil bootstrap. usuarios tiene imagen publicada pero no está en este Compose.

PostgreSQL debe aparecer healthy. Un contenedor Up no acredita por sí solo login, correo, MFA o autorización.

## 4. Accesos y verificaciones iniciales

| Componente | Dirección local |
|---|---|
| Panel | http://localhost:5173/ |
| Grilla | Abrir desde el panel; sirve http://127.0.0.1:5176/permissions.html |
| Identity / documentación API | http://localhost:8003/ y /docs |
| Permissions | http://127.0.0.1:8005/ |
| Audit health | http://127.0.0.1:8004/health |
| PostgreSQL | localhost:5433 |

Abrir directamente la grilla no transfiere la sesión: usar el menú del panel. Su token no se guarda en almacenamiento persistente.

~~~powershell
curl.exe --fail http://localhost:8003/
curl.exe --fail http://127.0.0.1:8005/
curl.exe --fail http://127.0.0.1:8004/health
docker compose exec -T postgres psql -U postgres -d iam_secure -At -c "SELECT to_regclass('public.permisos_usuario_compania'), to_regclass('public.cargas_usuarios'), to_regclass('public.cargas_usuario_filas');"
docker compose exec -T identity printenv SESSION_INACTIVITY_MINUTES
~~~

La última instrucción imprime únicamente una política no secreta.

## 5. Migraciones en un volumen existente

Los scripts de postgres-init se aplican automáticamente solo al inicializar un volumen vacío. Un rebuild no aplica migraciones nuevas.

En un entorno previo, tras revisar/resguardar los datos y los scripts correspondientes:

~~~powershell
Get-Content -LiteralPath .\postgres-init\11-create-permisos.sql -Raw -Encoding utf8 |
    docker compose exec -T postgres psql -U postgres -d iam_secure -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw 'No se aplicó la migración 11.' }

Get-Content -LiteralPath .\postgres-init\12-create-cargas-usuarios.sql -Raw -Encoding utf8 |
    docker compose exec -T postgres psql -U postgres -d iam_secure -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw 'No se aplicó la migración 12.' }

Get-Content -LiteralPath .\postgres-init\13-runtime-roles.sql -Raw -Encoding utf8 |
    docker compose exec -T postgres psql -U postgres -d iam_secure -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw 'No se aplicó la migración 13.' }

docker compose up -d --build --no-deps identity permissions frontend permissions-grid
~~~

La 11 adopta vistas anteriores una sola vez y no reactiva excepciones al repetirla. La 12 crea las tablas de lotes. Conservar las demás migraciones previas; la 13 añade roles/ACL y funciones requeridas por Permissions, sin asignar contraseñas. Estos comandos no reparan una base incompleta.

## 6. Primera cuenta y datos

En una base nueva no existen las cuentas personales del otro PC. Crear el ADMIN_TI inicial mediante el script específico, con contraseña privada. El script es idempotente y usa la identidad académica configurada en su fuente; no representa un envío de correo a una cuenta real.

Ejemplo PowerShell para pasar una contraseña introducida de forma oculta, sin escribirla en la línea de comandos:

~~~powershell
$claveInicial = Read-Host 'Contraseña temporal del ADMIN_TI inicial' -AsSecureString
$env:BOOTSTRAP_ADMIN_TI_PASSWORD = [System.Net.NetworkCredential]::new('', $claveInicial).Password
try {
    docker compose run --rm -e BOOTSTRAP_ADMIN_TI_PASSWORD identity python bootstrap_admin_ti.py
    if ($LASTEXITCODE -ne 0) { throw 'No terminó correctamente el bootstrap.' }
}
finally {
    Remove-Item Env:\BOOTSTRAP_ADMIN_TI_PASSWORD -ErrorAction SilentlyContinue
    $claveInicial = $null
}
~~~

Después completar contraseña/MFA y aprovisionar soportes, compañías y líderes autorizados. El perfil identity-bootstrap ejecuta un catálogo académico diferente que genera credenciales y usa SMTP; no ejecutarlo indiscriminadamente sobre una base existente. Revisar su catálogo y disponibilidad de correo antes de emplearlo.

Clonar Git no copia los datos de otro volumen. Una transferencia de base requiere un procedimiento de backup/restore separado; copiar secretos o recrear usuarios por ensayo no sustituye ese procedimiento.

## 7. Imágenes publicadas

Las siete imágenes del equipo están en Docker Hub con 1.0.0 y latest, construidas desde ab44403. [Repositorios y digests](IMAGENES_Y_DOCKERHUB.md).

~~~powershell
docker pull jeancarlosalmenarez8318/iam-secure-frontend:1.0.0
docker pull jeancarlosalmenarez8318/iam-secure-identity:1.0.0
~~~

El Compose de desarrollo utiliza build local; esos pull no cambian sus servicios a las imágenes publicadas. La configuración image-only de producción simulada está implementada y probada en etapa 2; consultar la sección 11. Las URLs del frontend publicado se fijaron al compilar; un env runtime no recompila el bundle.

El workflow ya verificó las catorce descargas con sesión del equipo. La descarga anónima y el despliegue completo desde Docker Hub en otro PC no están acreditados.

## 8. Aceptación funcional

1. Login, contraseña definitiva y MFA para la cuenta autorizada.
2. ADMIN_TI administra soportes/asignaciones dentro de su política.
3. ADMIN_SOPORTE ve solo sus compañías activas y líderes.
4. Crear líder individual o por Excel; confirmar llegada del correo y acceso.
5. Verificar las tres vistas de su rol; deshabilitar una excepción en la grilla y pulsar Actualizar mis opciones como líder.
6. Validar el mismo Excel: fila inválida por duplicado; descargar resultados.
7. Dejar panel/grilla/carga sin interacción cinco minutos: sesión expirada y controles retirados; reingresar desde el panel.

[Prueba local aceptada por el usuario](../VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md). La prueba con varias filas/correos funcionales sigue pausada como ampliación opcional. La instalación y aceptación técnica del alcance vigente en un segundo computador independiente fue validada el 13 de octubre de 2026.

## 9. Operación y diagnóstico

~~~powershell
docker compose logs --tail 50 identity permissions
docker compose logs --tail 50 sync-worker audit-service audit-dispatcher
docker compose ps
~~~

Revisar logs localmente; no publicar .env, contraseñas, QR ni tokens.

| Problema | Comprobación / acción |
|---|---|
| Login no funciona después de clonar | La base del nuevo PC es independiente; comprobar bootstrap y cuentas propias |
| Tabla de carga/permisos ausente | Verificar migraciones 11/12; rebuild no migra volúmenes |
| Grilla queda verificando o expirada | Abrir desde el panel con sesión nueva y versiones frontend/grilla coincidentes |
| Grilla sin líderes | Revisar compañía activa asignada y un único rol/compañía válida del líder |
| Puerto ocupado | Revisar compose ps y procesos del host antes de modificar el mapeo |
| Frontend no alcanza API desde otro host | Revisar URLs compiladas, CORS, publicación del puerto y server_name/CSP de Nginx |
| 403 al usar otro dominio | Nginx restringe hosts; ampliar explícitamente su configuración, no desactivar controles |
| SMTP falla | Revisar configuración y entrega real; la fila fallida se revierte |
| Sesión expira con la carga abierta | Política prevista; reingresar y consultar/retomar lote persistido |
| Cambio de permiso 409 | Otro cambio actualizó la versión; recargar grilla |
| Token inválido tras cambiar JWT_SECRET | Reiniciar sesión; no copiar tokens de otros entornos |

## 10. Detener y conservar datos

~~~powershell
docker compose down
~~~

Conservar postgres_data. No utilizar down -v ni borrar volúmenes en el equipo principal. Backups con datos personales y credenciales cifradas deben permanecer fuera de Git y gestionarse por un canal privado.

## 11. IaC, producción simulada y límites

Ansible, Checkov y CD con Compose de producción simulada quedaron aprobados en el [run 37578596462](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37578596462): 29/29 trabajos, commit ed00530990a494a616fe39770de65c2529915b96.

- [Guía Ansible](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/ed00530990a494a616fe39770de65c2529915b96/infraestructura/README.md): controlador Linux/Python 3.12+, Docker/Compose v2, inventario y variables cifradas con Ansible Vault. Docker puede instalarse opcionalmente en Ubuntu; esa ruta se omitió en el runner con Docker existente.
- [Manifiesto](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/ed00530990a494a616fe39770de65c2529915b96/orquestacion/compose.simulated.json): imágenes 1.0.0 por digest, red interna, volumen propio, puertos de aplicación solo en 127.0.0.1 y PostgreSQL sin puerto host. Ocho contenedores ejecutados con UID no root, raíz read-only y capacidades retiradas.
- [Workflow](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/ed00530990a494a616fe39770de65c2529915b96/.github/workflows/deploy-simulated.yml): valida CI, sintaxis, Checkov y políticas propias de Compose antes de desplegar. En pull_request solo realiza IaC; el despliegue aprobado fue disparado por push en etapa 2.
- Checkov aprobó CKV_ANSIBLE_5/6; una fixture insegura fue rechazada sin ejecución. El validador Compose pasó ocho casos negativos. Checkov no escaneó Compose.
- Ansible registró ok=12, changed=0, unreachable=0 y failed=0 en la segunda ejecución. Se mantuvo un ADMIN_TI y el esquema después de recrear PostgreSQL.
- Cinco sondas HTTP respondieron 200; tres rutas protegidas respondieron 401 sin sesión. Esto no acredita SMTP real ni todos los flujos funcionales.

[Resumen e informes duraderos](../evidencias/2026-10-07/ANSIBLE_CD_37578596462.json). Los artifacts originales tienen retención de 30 días; copias ZIP comprobadas por SHA-256 y reportes íntegros se conservaron al retomar.

Use un proyecto y destino propios siguiendo la guía Ansible; el volumen del PC original no fue tocado. La limpieza con volúmenes del workflow se limita a su proyecto efímero de CI. El playbook normal conserva datos. La simulación no configura TLS/HA ni automatiza ZAP y no sustituye un despliegue de producción real. La instalación limpia del alcance vigente en un segundo computador fue validada por separado el 13 de octubre de 2026. Secrets y SMTP se configuran fuera de Git.

El Compose actual es de desarrollo y publica PostgreSQL/Identity/frontend sin TLS. Un acceso remoto requiere diseño de puertos, red, dominio y certificados; no se presenta como configuración de producción.

## 12. Evidencias

- [Ansible/CD de producción simulada, 29/29 trabajos](../evidencias/2026-10-07/ANSIBLE_CD_37578596462.json).

- [Publicación 1.0.0, 29/29 trabajos](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json).
- [Runtime y contenedores, 27/27 trabajos](../evidencias/2026-10-06/CONTENEDORES_CI_9b6affc.json).
- [Instalación limpia reproducible — 13 de octubre](../evidencias/2026-10-13/instalacion-limpia/VALIDACION_INSTALACION_LIMPIA.md): clon limpio en iMac Intel, secretos propios, build 7/7, migraciones, bootstrap `ADMIN_TI`, cambio obligatorio de contraseña, MFA, SMTP real, creación de `ADMIN_SOPORTE`, Permissions Grid y persistencia tras recrear contenedores.
- [Diagramas](../diagramas/uml/DESPLIEGUE.md) · [Seguridad](../seguridad/SEGURIDAD.md) · [Usuario](../usuario/MANUAL_USUARIO.md) · [Matriz](../trazabilidad/MATRIZ_REQUISITOS.md).


## Validación remota en espejo — 13 de octubre de 2026

[E24: CI/CD del espejo](../evidencias/2026-10-13/ci-espejo/README.md): Deploy #2 aprobó 30/30 trabajos para 8262da2, incluidos CI reutilizado, IaC y despliegue. Los informes preservados verifican ocho contenedores no root, HTTP, políticas runtime, un ADMIN_TI, segunda ejecución Ansible changed=0 y persistencia después de recrear PostgreSQL. El manifiesto despliega imágenes publicadas 1.0.0 por digest; no las imágenes recién construidas en CI. No es una publicación ni validación de una nueva versión Docker con auditoría XLSX. La instalación limpia y SMTP real se acreditan por su evidencia independiente del segundo equipo.


## Cierre SonarCloud del espejo — 13 de octubre de 2026

[E25: SonarCloud del espejo](../evidencias/2026-10-13/sonar-espejo/README.md): workflow CI de f026d19 aprobado (29/29), incluido el análisis real, y check externo **Quality Gate passed** para el proyecto del espejo. El check informa 45 issues nuevos y 0 % de cobertura de código nuevo; esta métrica no sustituye el 69 % local. Las notas E24/anteriores conservan sus cortes históricos. El resultado no acredita una nueva publicación/deploy Docker, elimina los riesgos residuales ni valida automáticamente posteriores commits.


## ZAP automatizado contra staging — 13 de octubre de 2026

[E26: ZAP automatizado](../evidencias/2026-10-13/zap-staging-ci/README.md) acredita la ejecución remota sobre 574bb3e8195c3583ebd973f33d7f48a738689f7d: 29/29 trabajos CI, escaneo activo GET-only de 7 API/rol y 39 operaciones, gate MEDIUM/HIGH, reportes HTML/JSON saneados y limpieza del proyecto efímero. Servicios construidos desde el checkout; datos/secretos nuevos, sin puertos host ni SMTP. No se usan el Compose, .env ni PostgreSQL local. Login/MFA, XLSX, mutaciones y frontend quedan fuera. E20 conserva su ejecución manual histórica; no se confunden sus cifras con E26.


### Resultado posterior de Sonar en master

[validación posterior de E26](../evidencias/2026-10-13/zap-staging-ci/README.md#validación-posterior-en-master-ci-aprobado-y-sonar-rechazado): `2d8b444` aprobó 30/30 jobs CI, pero el check externo Sonar rechazó el Quality Gate por cobertura nueva 0 %, duplicación 84,6 % y fiabilidad C. E25 es histórico. Este resultado es histórico. E29 documenta cobertura importada y Quality Gate aprobado; los controles y umbrales se conservaron.

## Tratamiento STRIDE verificado - laboratorio local

[Perfil seguro](../seguridad/STRIDE_HARDENING_LAB.md) y [E32](../evidencias/2026-10-14/stride-hardening-lab/README.md): 61a1f7a, [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Sonar nueva 85,6 %/global 56,7 %, Quality Gate passed. TLS/roles/rate/backup se probaron en perfil independiente; reset MFA/outbox atómicos y alertas son código común. La migración 13 debe aplicarse a volúmenes existentes antes de reconstruir Permissions, conservando datos/.env. El Compose de desarrollo mantiene HTTP/DB administrativo. Seis riesgos siguen Open/no aceptación posterior; el equipo debe revisar adopción, límites y decisión residual. E29/E30 mantienen su corte histórico.
