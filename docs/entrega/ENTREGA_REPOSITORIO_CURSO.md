# I AM SECURE — entrega del Grupo 1

17 de octubre de 2026, America/Bogota.

Esta rama contiene la aplicación IAM Secure, su código fuente, tests, Docker Compose, workflows, IaC, documentación, informe técnico y manual de usuario. Se publica por solicitud del profesor como una rama del repositorio del curso.

- Repositorio: [jaiderospina/DEVSECOPS2026_2](https://github.com/jaiderospina/DEVSECOPS2026_2).
- Rama de entrega: [I-AM-SECURE](https://github.com/jaiderospina/DEVSECOPS2026_2/tree/I-AM-SECURE). Git no admite espacios en nombres de ramas.
- Código de origen: `0dd6fdd7589b827ebc18960a37e277354ddb7a13` de los repositorios del equipo.
- Base del repositorio del curso: `b6a3aa2616ed23781dc8316debaffb10b01f3823`. Las carpetas académicas preexistentes permanecen en esta rama; el README raíz presenta el proyecto entregado. La rama principal del curso no se modifica por esta entrega.

## Autores

- Oscar Daniel Acosta
- David Enrique Diaz
- Ingrid Tatiana Vesga
- Jean Carlos Almenarez Ríos
- Yeison Fabián Bernal López

Asignatura: Seg en Entornos Cloud y Devops.

## Ejecutar en otro computador

Instale Git y Docker con motor Linux y Compose v2 según los pasos 2–4 del [manual Windows/Linux](../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.md). El recorrido principal no requiere Python ni Node en el host.

En una carpeta nueva de su computador, los siguientes comandos sirven tanto en PowerShell como en Bash:

```console
git clone --branch I-AM-SECURE --single-branch https://github.com/jaiderospina/DEVSECOPS2026_2.git IAM-Secure
cd IAM-Secure
git branch --show-current
git log -1 --oneline
```

Debe aparecer la rama I-AM-SECURE. Si la carpeta IAM-Secure ya existe, revise la instalación anterior; no la sobrescriba ni cambie claves de una base existente.

Continúe **desde el paso 6** del [manual detallado Windows/Linux](../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.md), disponible también en [PDF de 23 páginas](../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.pdf): puertos, archivo .env, claves propias, SMTP, construcción, bootstrap, contraseña definitiva, MFA y prueba funcional.

El paso 5 de ese manual conserva los enlaces a los repositorios de desarrollo del equipo. Para esta entrega pública utilice los comandos anteriores. No necesita acceso a los repositorios privados para descargar esta rama y ejecutar su código.

El recorrido principal usa HTTP local en 5173 y SMTP propio compatible con STARTTLS. El laboratorio HTTPS de 8443–8446 es una alternativa independiente explicada en el paso 22. No combine configuraciones, claves ni volúmenes entre ambos recorridos. El bootstrap no envía correo; crear soportes/líderes requiere SMTP funcional y buzones de prueba controlados por el equipo.

No se publican .env reales, claves privadas, material .private, usuarios/contraseñas de la base ni volúmenes Docker. Cada PC genera sus propios secretos. El escaneo del snapshot con Gitleaks v8.24.3 terminó sin hallazgos.

## Documentos y sustentación

- [README e índice del proyecto](../../README.md).
- [Manual funcional del usuario](../usuario/MANUAL_USUARIO.md).
- [Informe técnico PDF — 23 páginas](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_STRIDE_LAB.pdf).
- [Arquitectura y UML](../arquitectura/ARQUITECTURA.md).
- [Threat Dragon y STRIDE](../diagramas/threat-model/README.md).
- [Checkpoint para continuar](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-17.md).
- [Procedencia de la entrega](PROCEDENCIA_ENTREGA.json).

Para sustentar se propone creación/importación Excel de un líder y comprobación de sus permisos, además del acceso con MFA. La publicación no cierra por sí misma el video, las capturas administrativas finales ni la aceptación residual de T03/T04/T06/T07/T10/T14.

## CI y procedencia

Los workflows se incluyen como parte del código. Se conservan sus filtros y condiciones originales: push a master/feat y controles Sonar/ZAP/STRIDE específicos del espejo. Crear esta rama no configura secretos ni inicia un despliegue desde la cuenta del profesor. La ejecución CI del equipo permanece en el [espejo](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions); los enlaces privados pueden requerir acceso de colaborador.

Las evidencias públicas bajo docs conservan su SHA y fecha de origen. E32 acredita 61a1f7a, CI 32/32 y Quality Gate aprobado; E33 es el informe técnico de ese corte. Los documentos no presentan esos checks como ejecutados en esta rama del curso. Para el commit de origen 0dd6fdd, consulte su [ejecución propia](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/39091662463).

Se incorpora una copia de los archivos versionados, sin importar el historial privado del repositorio del equipo. Los cambios de esta entrega se limitan al README de presentación y a esta guía/procedencia; el código de la aplicación conserva sus blobs de origen. Los archivos PDF y sus metadatos permanecen íntegros.
