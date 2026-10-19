# Identity Hub — Proyecto final del Grupo 3

**Identity Hub** es un proveedor de identidad: el lugar donde una persona demuestra quién es una sola vez (contraseña y código enviado por correo) y desde donde las aplicaciones de la organización saben quién es y qué puede hacer. Incluye inicio de sesión único (OAuth 2.0 con PKCE), roles y permisos por aplicación y por empresa, auditoría y claves de servicio. Lo acompaña un pipeline DevSecOps completo: análisis de código y dependencias, escaneo de imágenes, pruebas dinámicas, análisis de infraestructura como código, imágenes firmadas en Docker Hub y observabilidad con detección en tiempo de ejecución.

## Dónde está cada cosa

| Qué | Enlace | Para qué sirve |
|---|---|---|
| Código en este repositorio | [rama `IdentityHub-Grupo3`](https://github.com/jaiderospina/DEVSECOPS2026_2/tree/IdentityHub-Grupo3) | El proyecto completo (código, workflows, IaC y documentación) en el estado de la entrega. Es una copia en un solo commit. |
| Repositorio original | [jorgepaez-ops/IdentityHub](https://github.com/jorgepaez-ops/IdentityHub) | Fuente principal: historial completo de commits (incluida la línea base vulnerable y cada remediación), pipeline de CI en ejecución y su evidencia. |
| Pipeline de CI | [GitHub Actions](https://github.com/jorgepaez-ops/IdentityHub/actions/workflows/ci.yml) | Las ejecuciones del pipeline. En la rama de este repositorio los workflows no se ejecutan; corren en el repositorio original. |
| Imágenes en Docker Hub | [api](https://hub.docker.com/r/jorgeivp/identity-hub-api) · [worker](https://hub.docker.com/r/jorgeivp/identity-hub-worker) · [web](https://hub.docker.com/r/jorgeivp/identity-hub-web) | Imágenes publicadas y firmadas de cada servicio. |

## Por dónde empezar

El [README de la rama](https://github.com/jaiderospina/DEVSECOPS2026_2/blob/IdentityHub-Grupo3/README.md) explica qué es el proyecto, cómo levantarlo y ofrece rutas de lectura según el perfil (evaluador, desarrollador, operador). El informe técnico está en [`docs/informe/`](https://github.com/jaiderospina/DEVSECOPS2026_2/tree/IdentityHub-Grupo3/docs/informe).
