# Punto de continuidad - Prueba-ProyectoFinal

14 de octubre de 2026, America/Bogota. Punto de entrada para continuar por cualquiera de los integrantes; snapshots anteriores preservados.

## 1. Repositorios y carpeta

- Principal: [jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final).
- Espejo de ejecución: [yeisonfblopez/DevSecOps-proyecto-Final-ci](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci).
- Ambos master; carpeta Windows **C:/Prueba-ProyectoFinal**, origin principal. Consultar `git rev-parse HEAD`/refs para el commit documental final; distinguirlo del código probado **61a1f7acab2c76ef8e3669ae8f6ddc7fc7172df4**, E32. No copiar cuentas, .env ni volúmenes entre PCs.

## 2. Qué quedó listo

[E32](evidencias/2026-10-14/stride-hardening-lab/README.md): [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Sonar Quality Gate passed, nueva **85,6 % ≥ 80 %**, global **56,7 %**, 42 issues nuevos/cero aceptados. Se conserva cobertura propia del run, análisis por SHA/analysisId, laboratorio limpio y ZAP saneado con hashes. Principal continúa con bloqueo de facturación; el espejo acredita las pruebas.

Tratamientos de T03/T04/T06/T07/T10/T14 probados en laboratorio: TLS/CA, seis roles DB, reset/outbox atómicos, secretos privados/backup cifrado/restauración MFA y rate limit/concurrencia/XFF. 183 seguridad, 86 Excel, 28 helpers, 25 dispatcher con cuatro subtests y 24 Node. Laboratorio 11 checks y 30 requests/28 429/cero 5xx. Gateway no root, cero CRITICAL Trivy. Las cifras son alcances distintos.

[E33: PDF vigente](informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_STRIDE_LAB.pdf), 23 páginas, portada, índice enlazado, cinco autores/asignatura, UML/DFD y perfil alternativo, STRIDE, pipeline, resultados/hallazgos y conclusiones. [Hash y QA](informe/INFORME_TECNICO_STRIDE_LAB_METADATA.json). E28/E30 y E29 permanecen como históricos. README con sus quince apartados, matriz, manuales y avance alineados.

## 3. Alcance de seguridad y decisión pendiente

TLS, rate limit y logins DB separados se activan en el perfil seguro independiente. El Compose de desarrollo del PC conserva HTTP y postgres. El nuevo reset MFA atómico/alertas pertenece al código común. Ningún test ejecuta contra cuentas/configuración/volumen normales. Tráfico interno Docker, eventos históricos best-effort, operación de fallidos, custodia/rotación y recuperación fuera del laboratorio conservan límites.

Los seis riesgos **Open/no aceptación** mantienen la decisión del 13 de octubre; las pruebas no son aceptación humana. T13/T15 Mitigated y las 12 Open aceptadas solo académico/local permanecen. Revisar el [perfil y límites](seguridad/STRIDE_HARDENING_LAB.md), su adopción efectiva y registrar una decisión residual posterior del equipo.

ZAP sigue GET-only: 7 scans/39 API-rol/1.947 requests, cero alertas en ese alcance, DB/lifecycle aprobados. El laboratorio MFA es una prueba específica distinta de DAST de login/MFA/XLSX/mutaciones/frontend.

## 4. Actualizar un checkout existente

```powershell
git status --short --branch
git fetch origin
git switch master
git merge --ff-only origin/master
git rev-parse HEAD
```

Conservar cambios propios/divergencias; no usar force push/reset para descartar trabajo. En volúmenes existentes las migraciones de entrypoint no vuelven a ejecutarse. **Antes de reconstruir Permissions**, aplicar la migración 13 (ACL/funciones, sin passwords, sin borrado de datos):

```powershell
Get-Content postgres-init/13-runtime-roles.sql -Raw | docker exec -i iam-secure-postgres psql -X -v ON_ERROR_STOP=1 -U postgres -d iam_secure
docker compose build identity permissions frontend permissions-grid audit-dispatcher
docker compose up -d --no-deps identity permissions frontend permissions-grid audit-dispatcher
```

Conservar .env/clave MFA/cuentas/postgres_data, no ejecutar `down -v`. Comprobar HTTP de portal/grilla/Identity/Permissions/Audit y los checks de su SHA. La migración define roles; para los logins individuales y TLS usar la [instalación segura independiente](seguridad/STRIDE_HARDENING_LAB.md), con secretos nuevos y volumen nuevo. No regenerar MFA/JWT sobre datos existentes ni confiar la CA globalmente como efecto automático.

## 5. Siguiente paso y entregables

1. Completar primer acceso/cambio de contraseña/MFA del [laboratorio seguro activo E34](evidencias/2026-10-14/secure-demo/README.md); revisar residual de los seis riesgos y registrar decisión humana.
2. Completar capturas administrativas, historia funcional distinta de autenticación y video de 10–15 minutos; PDF terminado.
3. Resolver acceso de evaluación/repositorio público conforme al requisito.
4. Decidir release final. Docker 1.0.0/CD por digest sigue histórico, aunque CI construya código vigente. Si se publica nueva versión, build/Trivy/push/pull/deploy propios.
5. Ampliar cobertura global/React y DAST fuera de GET-only según alcance; observabilidad y correos adicionales son mejoras opcionales.

Usar una rama desde master actualizado, ejecutar CI en el espejo, comprobar workflow y Sonar del mismo SHA, actualizar informe/documentos y sincronizar ambos master/local después de la validación. Guardar recibos sin secretos. [Avance](AVANCE_ACTUAL_2026-10-14.md) · [README](../README.md) · [Matriz](trazabilidad/MATRIZ_REQUISITOS.md).

## 6. Laboratorio interactivo conservado - E34

En el PC de Jean Carlos está activo `iam-stride-demo-20261014`, creado desde bdedc77, con volumen y secretos nuevos: portal https://localhost:8443, grilla https://localhost:8444/permissions.html, APIs 8445/8446. Nueve servicios no root, seis logins mínimos y respaldo inicial cifrado. CA autorizada solo en CurrentUser/Root; cuatro HTTPS 200 con verificación de Windows. Se preservaron 28 contenedores anteriores, configuración y conteos normales.

[Guía y recibos E34](evidencias/2026-10-14/secure-demo/README.md) explican acceso ADMIN_TI, ubicación privada de contraseña, inicio/parada sin borrar volumen y retiro de confianza de CA. Primer acceso/cambio de contraseña/MFA todavía humanos pendientes; no hay aceptación automática de riesgos. La activación es local a este PC; el compañero debe crear su propio laboratorio/secretos. No regenerar claves sobre el volumen conservado.
