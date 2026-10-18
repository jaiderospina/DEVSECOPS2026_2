# Imágenes optimizadas y publicación en Docker Hub

## Corte vigente - 14 de octubre de 2026

[E29: cobertura CI y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites.

El [informe PDF](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf) está generado y revisado (21 páginas, índice/autores/orden solicitado). [Avance vigente](../AVANCE_ACTUAL_2026-10-14.md) y [checkpoint de equipo](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) son el punto actual; los documentos fechados al 6/7 de octubre son históricos. Video/capturas finales, seis riesgos no aceptados, visibilidad y decisión de nueva release siguen pendientes.

Corte: 7 de octubre de 2026 (America/Bogota).

## Implementación

La rama feat/bulk-users-excel-20261005 contiene un Dockerfile multietapa para el frontend:
Node 22 Alpine compila React/Vite y genera la configuración; Nginx stable-alpine-slim
sirve únicamente el bundle y esa configuración. La etapa final no contiene Node,
npm, node_modules ni el código fuente React. Escucha en 5173 como usuario nginx.
El panel y permissions-grid reutilizan esta imagen; Compose conserva sus puertos
5173 y 5176 y las variables públicas VITE_* de compilación.

Las cabeceras de seguridad se generan desde security-policy.js, compartido con Vite
Preview. La CSP conserva MFA con imágenes data/blob, las APIs locales y los orígenes
HTTP/HTTPS personalizados. No permite scripts/estilos inline. Nginx admite los hosts
locales, host.docker.internal e IP; los nombres restantes reciben 403, con cabeceras.
El fallback SPA no se aplica a archivos inexistentes de /assets/, y se bloquean rutas
de archivos ocultos. Para acceder por un dominio distinto se debe revisar y ampliar
explícitamente server_name, además de CORS y las URLs públicas.

El .dockerignore excluye archivos .env del contexto. Las variables VITE_* son públicas:
no introducir JWT_SECRET, MFA, contraseñas, tokens ni credenciales SMTP en ellas.

## Verificación

El pipeline construye las siete imágenes propias, comprueba el UID efectivo mediante
un contenedor con el usuario predeterminado y guarda reports/runtime-user.json.
Esta sonda acredita el usuario del contenedor, sin sustituir una prueba integral del
arranque de cada backend con PostgreSQL. Para frontend sí se comprueba el proceso
principal, su arranque HTTP y cabeceras, hosts, ambas páginas y errores 403/404.

El job frontend-ui ejecuta las once comprobaciones existentes de grilla, carga Excel
e inactividad contra dos contenedores Nginx reales. Las APIs/correo continúan simuladas;
el reloj de inactividad está controlado. Se añaden seis pruebas Node de CSP, URLs y
configuración. Las suites Pytest y el gate CRITICAL de Trivy se conservan.

La comparación de tamaño reconstruye el Dockerfile anterior del commit e20b783
con el mismo contexto y argumentos. reports/frontend-size.json registra bytes sin
comprimir de imágenes linux/amd64; no son tamaños de descarga ni una medición de RAM.
El pipeline exige una imagen final menor que la anterior.

[CI del código 9b6affc](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37572601777): **27/27 trabajos aprobados**.
Se verificaron 147 Pytest, 11 comprobaciones Chromium contra Nginx y seis pruebas
Node. Tamaño frontend: 252806015 → 13069479 bytes, reducción
del 94.83 %. [Registro duradero](../evidencias/2026-10-06/CONTENEDORES_CI_9b6affc.json).

## Publicación verificada: 1.0.0

[Workflow de publicación](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/.github/workflows/publish-dockerhub.yml).

Cuenta confirmada por el usuario: jeancarlosalmenarez8318.

| Contexto | Imagen en Docker Hub |
|---|---|
| identity-service | jeancarlosalmenarez8318/iam-secure-identity |
| sync-service | jeancarlosalmenarez8318/iam-secure-sync-worker |
| audit-service | jeancarlosalmenarez8318/iam-secure-audit |
| audit-dispatcher | jeancarlosalmenarez8318/iam-secure-audit-dispatcher |
| frontend | jeancarlosalmenarez8318/iam-secure-frontend |
| usuarios | jeancarlosalmenarez8318/iam-secure-usuarios |
| permissions-service | jeancarlosalmenarez8318/iam-secure-permissions |

permissions-grid reutiliza frontend e identity-bootstrap reutiliza Identity.
PostgreSQL utiliza la imagen oficial postgres:17; no es una imagen propia del equipo.

El flujo es manual y recibe version en formato MAJOR.MINOR.PATCH, sin prefijo v.
La primera publicación 1.0.0 terminó correctamente en el [run 37574847806](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37574847806): **29/29 trabajos aprobados**. Las siete imágenes tienen 1.0.0 y latest; se comprobaron los 14 push/pull y ambas etiquetas comparten digest por imagen. [Registro duradero](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json).
Reutiliza todo el CI antes del job publish. Después reconstruye y escanea las siete
imágenes de release, también con las CVE críticas sin corrección, antes de publicar
cualquiera. Rechaza una versión existente y publica VERSION y latest. Finalmente
descarga ambas etiquetas, compara sus IDs y conserva digests/metadatos de las siete
imágenes como artifacts durante treinta días. Una interrupción del registro durante
los push puede dejar una publicación parcial; solo se acredita el cierre cuando las
siete descargas y verificaciones completan satisfactoriamente.

## Configuración utilizada y futuras publicaciones

1. En Docker Hub: Account settings → Personal access tokens → Generate new token.
   Usar un token para GitHub Actions con permisos de lectura y escritura, sin borrado,
   y una expiración apropiada. Guardarlo directamente como secreto, sin compartirlo
   en capturas, chat, commits o archivos del proyecto.
2. En [GitHub, secretos de Actions](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/settings/secrets/actions),
   crear un repository secret llamado DOCKERHUB_TOKEN y pegar allí el token.
3. Preparar los siete repositorios de imágenes en Docker Hub bajo la cuenta indicada.
   La entrega debe permitir que el evaluador descargue las imágenes; revisar su
   visibilidad al crearlos.
4. El workflow y el código optimizado están integrados en master mediante PR #3.
   Para una publicación nueva utilizar la revisión final elegida, verificar sus checks
   y seleccionar una versión semántica nueva; 1.0.0 es una publicación histórica.
5. En Actions → Publish Docker Hub images → Run workflow, elegir master o la revisión
   de código aprobada y una versión nueva en version, sin sobrescribir 1.0.0. Para API en otro host, configurar las variables
   públicas VITE_API_URL y VITE_PERMISSIONS_API_URL antes de construir.
6. Comprobar éxito de todo el flujo y archivar la evidencia de los siete digests.
   El README solo debe cambiar la publicación y etiquetas a Cumplido tras verificarla.

Fuentes: [Tokens de Docker](https://docs.docker.com/security/access-tokens/personal-access-tokens/),
[secretos de GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
y [ejecución manual](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

## Estado y límites

La publicación se ejecutó desde feat/bulk-users-excel-20261005, commit
ab444034719b6da3aab08009606de6dd7d12f26d. Se verificaron login, construcción,
UID no root, frontend Nginx mínimo, Trivy CRITICAL, push de 14 etiquetas y
su descarga con comparación de IDs. No se leyó ni solicitó el valor del token.
El PR #3 ya está integrado en master (19b54ee). La publicación histórica no se
actualiza por ese merge; nuevos cambios requieren versión y verificación propias.

Las descargas del workflow utilizaron la sesión Docker Hub del equipo; no se
ha comprobado una descarga anónima ni el despliegue completo de la aplicación
desde estas imágenes en otro PC. La publicación no implementa por sí sola IaC,
producción simulada, cobertura ni una release de GitHub.

## Evidencia y conservación

- [Ejecución aprobada, 29 trabajos](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37574847806).
- [Resumen de digests versionado](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json).
- [Artifact dockerhub-release-evidence](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37574847806/artifacts/11461914923):
  siete informes Trivy y siete metadatos docker inspect, 14 archivos;
  expiración 6 de noviembre de 2026. El resumen Git conserva los digests;
  el artifact completo debe descargarse antes de su expiración.

| Imagen | Digest de 1.0.0 y latest |
|---|---|
| [iam-secure-identity](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-identity/tags) | sha256:839ce22bfbf6a50396fc75a77a691750b0bce9ce99e00d9b6c222d12492e750b |
| [iam-secure-sync-worker](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-sync-worker/tags) | sha256:f5eb8558bfb73d0e69c40d2db99c620d6695d6958e22b41ed55b0447f3e9fc20 |
| [iam-secure-audit](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-audit/tags) | sha256:a6082e5f009c6138f44a543014bc701fce25f25cb3edfa3fb44338edceffe7b2 |
| [iam-secure-audit-dispatcher](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-audit-dispatcher/tags) | sha256:2917901afd11f22a808cdc37e9392c020fa43a3eb0144017ed8611792668ea42 |
| [iam-secure-frontend](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-frontend/tags) | sha256:cad264c9bf5aa6e91a5817349e1f433e224c63edba05364b0f9d75881ecd42bb |
| [iam-secure-usuarios](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-usuarios/tags) | sha256:35e32e2be0840ee09bde2375c44066a66ab67dfa320e0c9d7279d70a0af049d3 |
| [iam-secure-permissions](https://hub.docker.com/r/jeancarlosalmenarez8318/iam-secure-permissions/tags) | sha256:b80cf3ad35ce6a7502570924930e8592d2afd3a42ad07879a61be6475edfccda |

Para obtener una imagen por versión:

```powershell
docker pull jeancarlosalmenarez8318/iam-secure-frontend:1.0.0
```

Para publicaciones nuevas, ejecutar el workflow en una rama con el frontend
optimizado y elegir una versión semántica nueva. 1.0.0 ya existe y el workflow
la protege frente a nuevas publicaciones; latest cambiará al publicar otra versión.
