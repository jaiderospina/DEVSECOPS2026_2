# Etapa 1: API de permisos integrada con IAM y grilla de ADMIN_SOPORTE

Base: 76cc39d92369ffd55ae887df91a5a1f30d5e901f. Fecha: 5 de octubre de 2026.
Se conserva master y la documentación previa. La carga masiva de usuarios es una etapa posterior.

## Comportamiento

ADMIN_SOPORTE abre **Grilla de permisos** desde su panel. La pantalla independiente
ofrece un selector de sus compañías activas y una tabla de usuarios líderes,
área, opción, estado e interruptor. Usa las identidades existentes; no codifica
el correo de un administrador concreto ni crea nuevas cuentas de prueba en el PC.

Cada permiso se guarda por usuario, compañía y código. Al volver a iniciar sesión,
el portal consulta la API y no muestra las opciones deshabilitadas. **Actualizar mis
opciones** permite releer permisos sin cerrar sesión. Abrir una vista vuelve a
comprobar el permiso en backend; ocultar tarjetas no es la única barrera.

Las nueve opciones son las que ya figuraban en Facturación, Logística y Gestión
Humana. Continúan siendo vistas académicas de referencia. No se implementan pagos,
aprobación de facturas, impuestos ni otras operaciones de negocio reales.

## Integración de las dos API

- Identity permanece en 8003 y conserva login, MFA, contraseña, sesiones y roles.
- Permissions es un microservicio distinto en 8005, publicado solo en localhost.
- En cada petición protegida Permissions consulta /auth/me de Identity con el
  Bearer recibido. No recibe JWT_SECRET, la clave MFA ni credenciales SMTP.
- Exige sesión válida, MFA activo y cambio de contraseña completado.
- Relee roles, usuario y asignaciones vigentes en PostgreSQL antes de autorizar.
- ADMIN_SOPORTE administra exclusivamente líderes de sus compañías activas.
  ADMIN_TI mantiene su función de plataforma y no administra permisos internos.
- Un permiso ajeno al rol no puede habilitarse. Compañías o roles ambiguos se deniegan.
- El token no se agrega a URL, logs ni eventos. Se utiliza la sesión actual del
  frontend; no se crea un segundo login.
- La modificación y su evento PERMISO_USUARIO_MODIFICADO se confirman juntos en
  PostgreSQL. Audit Dispatcher entrega el evento por la Outbox existente.
- Una versión por permiso evita sobrescribir cambios de otra sesión: conflicto 409.
- Ausencia de concesión o fallo de verificación implica denegación.

| Método | Ruta de Permissions | Alcance |
|---|---|---|
| GET | /v1/companies | Compañías asignadas al soporte |
| GET | /v1/companies/{id}/permissions | Grilla de esa compañía |
| PUT | /v1/companies/{id}/users/{uid}/permissions/{codigo} | Cambiar habilitado y versión |
| GET | /v1/me/permissions | Opciones del propio líder |
| GET | /v1/me/views/{codigo} | Vista de referencia con permiso verificado |

## Datos y migración

postgres-init/11-create-permisos.sql añade permisos_usuario_compania y
permisos_migraciones. No cambia usuarios, roles, credenciales, MFA ni sesiones.

La primera aplicación habilita las opciones que ya veían los líderes existentes,
solo si tienen un rol líder y exactamente una compañía activa. Un marcador impide
repetir esa concesión inicial: ejecutar nuevamente la migración no reactiva opciones
deshabilitadas ni concede permisos a usuarios creados después. Los usuarios nuevos
requieren habilitación explícita desde la grilla. Se conserva la restricción de
relación usuario-compañía; quitar esa relación elimina sus concesiones.

Los scripts de postgres-init no se ejecutan automáticamente en un volumen existente.
Por eso el paso de migración manual siguiente es obligatorio.

## Activar en C:\Prueba-ProyectoFinal

Revisar primero git status. Si hay cambios locales, conservarlos antes de cambiar
de rama. No usar master para esta etapa.

~~~powershell
Set-Location -LiteralPath 'C:\Prueba-ProyectoFinal'
git status --short --branch
git fetch origin
git switch feat/permissions-grid-20261005

Get-Content -Raw -Encoding utf8 .\postgres-init\11-create-permisos.sql |
    docker compose exec -T postgres psql -U postgres -d iam_secure -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw 'Migración fallida; no continuar.' }

docker compose up -d --build --no-deps permissions frontend
docker compose ps
curl.exe -s -o NUL -w "Permisos: %{http_code}\n" http://localhost:8005/
curl.exe -s -o NUL -w "Frontend: %{http_code}\n" http://localhost:5173/
~~~

Identity, PostgreSQL, Audit Service y Dispatcher deben estar activos.
No mostrar docker compose config resuelto ni leer .env para esta operación.
La configuración existente de PostgreSQL se reutiliza sin editar secretos.

La URL pública de Permissions deriva del navegador con puerto 8005. Si se usa un
puerto diferente o un host remoto, VITE_PERMISSIONS_API_URL puede configurarse como
URL pública de compilación; ajustar además publicación, CORS y CSP a ese entorno.
La publicación localhost de esta etapa no acredita acceso LAN ni TLS.

## Prueba de aceptación local pendiente

1. Iniciar sesión como un ADMIN_SOPORTE existente, por ejemplo jeank04520@yahoo.es.
2. Abrir Grilla de permisos y seleccionar una compañía realmente asignada.
3. Elegir un líder de Facturación existente en esa compañía.
4. Deshabilitar Facturas pendientes por pagar; confirmar que se guarda el cambio.
5. Cerrar sesión e iniciar sesión como ese líder, completando su MFA.
6. Verificar que pendientes por pagar no aparece y que las otras opciones siguen
   según su estado. Rehabilitarla con el soporte y comprobar la recuperación.
7. Probar que un soporte de otra compañía no puede leer ni modificar esas concesiones.
8. Comprobar el evento y su entrega por el Dispatcher con consultas sanitizadas.

No publicar QR, códigos MFA, tokens ni contraseñas como evidencia.

## Validación y límites

Se incluyen pruebas con PostgreSQL real de aislamiento, cambios, versiones,
revocación de alcance, migración idempotente y rollback si falla auditoría.
El contrato HTTP se prueba con transporte simulado y también levantando Identity
real contra PostgreSQL efímero: sesión válida, revocación, expiración y cambio de
contraseña pendiente. Esa prueba construye su propia sesión de laboratorio; no
equivale a completar el login/TOTP real ni a una prueba en el PC. CI añade SCA, build y Trivy del nuevo servicio,
pruebas de permisos, lint y pruebas Chromium de la SPA compilada al gate existente.
Las capturas de Chromium usan contratos API y usuarios simulados; no son evidencia
de una sesión MFA real ni de las compañías del PC.

Estado inicial: implementación para revisión; resultados CI y aceptación manual
deben acreditarse por separado. No declarar controles cumplidos por tener código.

Se reutiliza la instancia PostgreSQL y el usuario DB de Compose actual. Separación
de roles DB y TLS interno siguen pendientes. DFD 0/1 y STRIDE deben ampliarse para
el nuevo servicio; el esquema válido del modelo anterior no acredita esa ampliación.
No se cierran las amenazas existentes ni se afirma ZAP de este nuevo alcance.

Para volver al frontend anterior, detener permissions, cambiar a la rama del
checkpoint y reconstruir frontend. No eliminar el volumen PostgreSQL. Los permisos
y auditoría se conservan para retomar; no hace falta borrar tablas.

## Corrección de dependencia detectada al validar esta etapa

El audit del lock del checkpoint detectó GHSA-68fv-2mgg-jv7q en source-map-js 1.2.1. Se actualiza únicamente esa dependencia transitiva a 1.2.2 con el metadato e integridad resueltos por npm. No se amplía el umbral del gate ni se ignora la alerta. El resultado del pipeline posterior debe comprobarse antes de acreditar el cierre.


## Resultado CI acreditado — 5 de octubre de 2026

El [run 37406285771](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37406285771) terminó con **26/26 trabajos aprobados**, incluido el gate final, sobre el commit de código `2cf379a29882906df35b510d42636cbdfdba3365`. Este resultado actualiza el estado inicial de revisión CI; la aceptación local continúa pendiente.

- **96 pruebas Pytest**: Permissions 32, Identity HTTP 6, Audit Dispatcher 22, Sync Worker 23 y Audit Service 13.
- **Dos comprobaciones Chromium**: la grilla deshabilita una opción que desaparece al cargar una sesión nueva del portal, y una API no disponible impide mostrar tarjetas sin autorización verificada. Usan contratos simulados, no credenciales del PC.
- Identity real contra PostgreSQL efímero valida por HTTP sesión válida, revocada, token expirado y cambio de contraseña pendiente, mediante sesiones construidas para laboratorio.
- Gitleaks, Semgrep, Bandit, SCA Python/Node, lint, siete Docker builds y Trivy con umbral CRITICAL aprobados. SCA Node aprueba tras actualizar source-map-js a 1.2.2. El umbral Trivy no acredita ausencia de hallazgos de otras severidades.

[Evidencia estructurada](evidencias/2026-10-05/PERMISOS_ETAPA_1_CI.json). Los resultados corresponden al commit de código indicado; este complemento documental no modifica la implementación. El [PR #2](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/2) permanece en borrador y apunta a la rama del checkpoint, sin merge a master.

**Pendiente antes de acreditar la prueba en el PC:** aplicar la migración en el volumen existente, activar Permissions y recompilar frontend, probar el soporte y líder de una misma compañía con MFA real y comprobar la entrega del evento de auditoría. No se guardan secretos en la evidencia.


## Complemento: página independiente y diseño de la grilla

El usuario reportó que la etapa 1 funcionó en su PC. Es una confirmación funcional reportada; no equivale a una captura o log de todas las pruebas locales pendientes.

El ajuste posterior abre la grilla en una pestaña nueva en **http://localhost:5176/permissions.html** desde el botón de ADMIN_SOPORTE. El panel conserva 5173 y Permissions API conserva 8005. El encabezado destaca el nombre y código de la compañía seleccionada y cambia al seleccionar otra de las compañías asignadas. La página utiliza una paleta violeta/verde, fondo decorado, filas resaltadas al pasar el cursor y etiquetas de estado legibles.

La página HTML de la grilla es una entrada distinta del mismo frontend compilado, servida por el contenedor permissions-grid. Su API continúa siendo el microservicio Permissions existente. No se duplican usuarios ni credenciales.

El panel entrega la sesión mediante postMessage exclusivamente a la ventana que abrió y a su origen exacto en 5176. La grilla verifica el origen 5173, la referencia del panel y un identificador aleatorio de su canal. El token se conserva solo en memoria de la pestaña de la grilla: no se incluye en URL ni se escribe en localStorage/sessionStorage. Abrir esa página directamente no concede una sesión. La API sigue validando cada petición contra Identity y PostgreSQL.

Cerrar sesión, recargar o cerrar el panel invalida el contexto de la pestaña de permisos. Debe mantenerse abierto el panel original. Las interacciones reales en la grilla reinician el temporizador local del panel; el canal no realiza peticiones periódicas para renovar la sesión del servidor. Un fallo al verificar la API conserva la denegación.

El origen de la grilla se permite explícitamente en CORS de Permissions. PERMISSIONS_CORS_ORIGINS es una variable pública opcional, independiente de CORS_ORIGINS de Identity. No se requiere editar .env para los puertos locales predeterminados. Este ajuste no acredita TLS ni acceso LAN.

### Activación del ajuste (sin nueva migración)

~~~powershell
Set-Location -LiteralPath 'C:\Prueba-ProyectoFinal'
git status --short --branch
# Continuar si está limpio y en feat/permissions-grid-20261005.
git pull --ff-only origin feat/permissions-grid-20261005
docker compose up -d --build --no-deps permissions frontend permissions-grid
docker compose ps
curl.exe -s -o NUL -w "Grilla: %{http_code}\n" http://localhost:5176/permissions.html
~~~

Recargar el panel 5173 con Ctrl+F5, iniciar sesión como ADMIN_SOPORTE y abrir la grilla desde su botón. Si el navegador bloquea la pestaña, permitir su apertura para el portal local. Comprobar nombre de compañía, cambio de selector y habilitación/deshabilitación. Mantener pendiente la aceptación local del ajuste hasta recibir evidencia del usuario.

La prueba Chromium se amplía para comprobar el puerto independiente, nombre en encabezado, cambio de compañía, ausencia de token en URL/almacenamiento de la grilla, invalidación al recargar el panel y denegación al abrir la página sin panel. Los contratos API de navegador continúan siendo simulados. El resultado CI anterior acredita la implementación anterior; este ajuste necesita su propio run.

La grilla también verifica periódicamente su canal con el panel mediante mensajes entre ventanas. Si no recibe respuesta, elimina su contexto en memoria. Esto cubre las recargas en las que el navegador no entrega el aviso pagehide; no realiza llamadas de renovación a Identity o Permissions.


### Validación CI del ajuste de puerto y diseño

[Run 37408693914](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37408693914), commit `f930ed6e175952e9bb2a81274369504edcd3152a`: **26 trabajos aprobados, 96 pruebas Pytest y cuatro comprobaciones Chromium**. Se verifican apertura en 5176, nombre de compañía y selector, ausencia de token en URL/almacenamiento de la grilla, bloqueo al recargar el panel, guardado del permiso, ocultación al volver a cargar el portal y denegación ante API no disponible o acceso directo sin panel. La prueba del navegador utiliza contratos simulados y genera dos capturas de laboratorio.

Los controles Gitleaks, Semgrep, Bandit, SCA, lint, Docker build y Trivy CRITICAL siguen aprobados. [Evidencia del ajuste](evidencias/2026-10-05/PERMISOS_GRILLA_PUERTO_5176_CI.json). Este resultado acredita el commit de código indicado; el complemento documental posterior no cambia la implementación. La prueba del ajuste en el PC continúa pendiente.


### Confirmación local reportada — 5 de octubre de 2026

Después de las instrucciones de actualización del ajuste visual y de puerto, el usuario confirmó: «ok, funciona correctamente». Se registra como confirmación funcional reportada del ajuste de la grilla independiente, con compañía destacada y nuevo diseño, en C:\Prueba-ProyectoFinal. Actualiza el pendiente de confirmación local de este ajuste, conservando el historial anterior.

No se recibieron nuevas capturas ni logs en este mensaje. La confirmación no acredita por sí sola cada prueba negativa de aislamiento, la entrega local de Outbox o un nuevo escaneo ZAP. La evidencia CI sigue siendo el run 37408693914 y el commit de código f930ed6e175952e9bb2a81274369504edcd3152a.

Punto para retomar: etapa 1 implementada y con funcionamiento confirmado por el usuario. La creación masiva de usuarios permanece para una etapa posterior, sin iniciar en este checkpoint. Master no se modifica por este registro documental.


### Confirmación de cuentas ADMIN_SOPORTE — 5 de octubre de 2026

El usuario reportó: «ya probe las cuentas de soporte y funcionan correctamente con la grillas». Se registra la validación funcional reportada de las cuentas de soporte probadas con la grilla de permisos, complementando la confirmación anterior del ajuste visual y del puerto 5176.

No se detallaron en este mensaje los correos, el número de cuentas ni los casos ejecutados, y no se adjuntaron capturas o logs. No se infiere de esta confirmación el resultado de pruebas negativas entre compañías o la entrega local de auditoría. La evidencia CI permanece vinculada al run 37408693914.

Checkpoint: integración IAM/Permissions y grilla operativas según las pruebas reportadas por el usuario, incluido el acceso desde sus cuentas de soporte. La creación masiva de usuarios queda como siguiente etapa acordada, todavía sin iniciar.


### Integración en master — 5 de octubre de 2026

El usuario autorizó expresamente agregar los cambios a master. El PR #2 se retargetó a master, se marcó listo y se integró mediante merge `9fccd36a2a917ae74b5f100bbd6126d19acab5c6`, conservando el historial previo. El PR #1 quedó registrado por GitHub como integrado. La comparación del árbol del merge con el head validado `34a02dff1ca2fe9dc5bb2e5b58ebe31de2b46bb8` no muestra diferencias.

[CI del head previo a integrar](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37409870379): 26/26 trabajos aprobados. La integración activa además el pipeline de master; no se anticipa su resultado en esta nota. Los registros anteriores que indican master sin cambios o PR en borrador describen el estado histórico y quedan actualizados por este complemento.

El checkpoint operativo pasa a master, con la etapa 1 y las confirmaciones funcionales reportadas por el usuario. No se acredita creación masiva de usuarios, entrega local de auditoría, pruebas negativas adicionales o ZAP nuevo por efectuar este merge. No requiere repetir la migración ni reconstruir contenedores si el PC ya ejecuta el código validado de la rama de permisos.
