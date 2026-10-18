# Tratamiento STRIDE en laboratorio local

Validado el 14 de octubre de 2026. Alcance elegido por el usuario: laboratorio local. Los tratamientos se prueban con datos nuevos y sintéticos, sin la configuración, cuentas o volumen de `C:/Prueba-ProyectoFinal`.

## Controles implementados

| Riesgo | Tratamiento | Verificación |
|---|---|---|
| T03 | Gateway TLS 1.2/1.3, certificado localhost/127.0.0.1, APIs privadas sin puertos directos | Cuatro HTTPS con CA verificada; cliente sin CA rechazado; HTTP y host no autorizado rechazados |
| T04/T14 | Seis logins DB separados, sin superusuario, creación de roles/bases o propiedad del esquema; ACL por servicio | Conexiones reales: lectura de credenciales/MFA y modificación de datos ajenos denegadas; operaciones permitidas aprobadas |
| T06 | Ambas rutas de reset MFA escriben outbox en la misma transacción que borrado MFA/revocaciones; error terminal del dispatcher genera alerta sin payload | Fallo de INSERT y COMMIT revierte todos los cambios; entrega real a Audit, idempotencia, denegaciones sin éxito y alertas verificadas |
| T07 | Secretos independientes por servicio, carpeta privada con permisos Unix/ACL Windows, clave TLS PKCS8 cifrada, respaldo PostgreSQL autenticado cifrado y rol de backup de solo lectura | Claves distintas, rechazo de reemplazo/alteración/clave incorrecta; restauración real en DB vacía separada y MFA descifrable con la clave preservada |
| T10 | Gateway limita frecuencia, ráfaga y concurrencia de /auth antes de las APIs; XFF se sobrescribe y no define el bucket | 30 solicitudes concurrentes con XFF falsificado: respuestas 429, sin errores 5xx; cabecera Retry-After y JSON/CORS coherentes |

Las funciones DB de bloqueo de Permissions conservan las comprobaciones de rol/compañía y los locks de transacción. Solo bloquean/leen objetos fijos y tienen `search_path` fijo; no conceden UPDATE sobre identidades, compañías o sus asociaciones. No sustituyen la autorización de la API. PostgreSQL continúa siendo una instancia compartida.

## Pruebas y CI

- `tests/identity_security`: 135 pruebas tras T06; con 48 casos de roles, 183 pruebas. Incluye 121 T13/T15 preexistentes y 14 casos T06/auditoría. No sumar estas cifras solapadas.
- Regresión Excel: 86 casos. Dispatcher: 25 casos y cuatro subtests. JavaScript: 24 casos, ocho nuevos de orígenes de ventanas. Helpers: 28 controles negativos.
- `stride-lab` del espejo genera su propio entorno, ejecuta TLS/MFA/permisos/auditoría, cifra y restaura backup, valida carga y limpia solo su proyecto/volumen.
- El job importa su cobertura propia al análisis Sonar; el gate final exige este job en el espejo. El gateway no root tiene escaneo CRITICAL con Trivy. Master 61a1f7a aprobó CI 32/32 y Quality Gate Sonar; nueva 85,6 %/global 56,7 %, E32. Cada revisión posterior requiere checks propios.
- [E31 local / E32 validación master](../evidencias/2026-10-14/stride-hardening-lab/README.md). Los recibos CI posteriores identifican su SHA/run; no heredan checks de otra revisión.

## Reproducir el laboratorio

Python 3.14, Docker/Compose y dependencias del lock CI. Generar un entorno Python aislado: las wheels/hashes del lock de CI son para Linux; Windows usa las mismas versiones con hashes oficiales compatibles. No modificar los pins por ese motivo.

Desde la raíz del checkout, con puertos 8443-8446 libres:

```powershell
python scripts/validate_secure_lab.py --project iam-stride-manual --output reports/stride-secure-lab.json
```

Por defecto elimina solo contenedores, redes y volumen nuevos del proyecto elegido. Rechaza un proyecto/volumen preexistente, nombres ambiguos y puertos ocupados. No ejecuta Docker prune ni el Compose normal. La DB del laboratorio se llama `iam_secure`, pero vive en su contenedor/volumen nuevos; no es la base normal del PC.

`--keep` conserva el laboratorio para inspección explícita. La carpeta privada generada queda fuera de Git; contiene configuración y material que requieren custodia. Para una instalación interactiva usar el perfil seguro, provisionar roles y ejecutar bootstrap siguiendo las instrucciones siguientes; el validador prepara fixtures sintéticas, no copia usuarios reales.

## Instalación segura independiente

1. Crear una carpeta nueva con `python scripts/create_secure_lab_config.py .private/mi-laboratorio`. Nunca regenerar las claves MFA/runtime sobre un volumen existente: eso no es una rotación ni conserva las cuentas.
2. Configurar `IAM_LAB_PRIVATE_DIR` con su ruta absoluta y usar `docker compose --project-name iam-stride-manual --project-directory . --env-file .private/mi-laboratorio/runtime.env -f orquestacion/compose.secure-lab.json` para los comandos del perfil.
3. Construir las imágenes y levantar solo PostgreSQL. Aplicar `provision_runtime_roles.py` con `POSTGRES_PASSWORD` cargada privadamente del archivo generado, `--container` igual al nombre de ese PostgreSQL y `--roles-file .private/mi-laboratorio/roles.json`. El script no imprime la credencial ni la pone en argv. Las migraciones no contienen passwords.
4. Ejecutar `run --rm bootstrap-admin` del mismo Compose. La contraseña temporal ADMIN_TI está en el archivo privado generado; el bootstrap usa iam_identity, no postgres. Conservarla localmente y seguir cambio obligatorio/MFA.
5. Levantar los servicios del perfil y abrir **https://localhost:8443**. Grilla 8444, Identity 8445 y Permissions 8446. Los otros puertos no se publican.
6. La CA es de laboratorio. El validador la verifica explícitamente; no instala confianza global. Para el navegador, revisar y confiar en el certificado público de esa CA mediante el procedimiento del equipo. Nunca compartir server.key/server.pass, runtime.env, roles.json, MFA key o backup.key por Git/chat.

## Respaldo y restauración

`encrypted_backup.py` usa PostgreSQL custom dump, Fernet autenticado, límite 64 MiB y no guarda dumps en texto plano. La clave de respaldo está fuera de la carpeta del backup; no se pasa por argv ni al servicio de aplicación. `PGPASSWORD` se carga privadamente para el rol apropiado.

```powershell
python scripts/encrypted_backup.py backup --container iam-stride-manual-postgres-1 --database iam_secure --key-file .private/mi-laboratorio/backup.key --file .private/mi-laboratorio/backups/respaldo.dump.enc
```

Restaurar requiere un destino **vacío y separado `iam_restore_*`**, credencial administrativa cargada privadamente y la clave original. Verifica autenticidad antes de escribir, usa transacción y reaplica la política ACL. No restaura encima de la base normal. Custodiar también la clave MFA/configuración original: el dump contiene secretos MFA cifrados y el cifrado del backup no reemplaza esa clave.

## Límites y decisión residual

Los controles de TLS, rate limit y roles separados están activos **en el perfil seguro**. El Compose de desarrollo existente conserva su comportamiento HTTP/DB administrativo; no debe presentarse como endurecido por probar otro perfil. El reset atómico y las alertas sí son cambios del código común, y requieren reconstruir los servicios para actualizar un runtime existente.

El gateway TLS protege la frontera navegador/APIs. El tráfico interno Docker continúa en la red de confianza; no se acredita mTLS interno, producción, HA, SMTP real nuevo, recuperación externa/offsite o carga distribuida. El certificado local expira en 30 días; no equivale a certificado público. Los límites deben dimensionarse para otro entorno.

La decisión humana del 13 de octubre **no aceptó** el riesgo residual de T03/T04/T06/T07/T10/T14. Esta implementación aporta tratamiento y evidencia; **no cambia automáticamente esa aceptación ni los estados Open del modelo as-is**. La revisión residual posterior debe valorar el perfil y su adopción efectiva, conservar la separación académico/local y producción, y registrar la decisión del equipo.

Referencias técnicas: [transacciones SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/connections.html#connect-and-begin-once-from-the-engine), [privilegios PostgreSQL 17](https://www.postgresql.org/docs/17/sql-grant.html), [TLS Nginx](https://nginx.org/en/docs/http/configuring_https_servers.html), [limitación de solicitudes](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html).

## Activación interactiva conservada - E34

El 14 de octubre se dejó activo un [laboratorio nuevo en el PC local](../evidencias/2026-10-14/secure-demo/README.md), proyecto `iam-stride-demo-20261014`, desde bdedc77. Cuatro HTTPS 200, TLSv1.3, nueve servicios no root, seis logins mínimos, respaldo inicial cifrado y 30 solicitudes/24 respuestas 429/cero 5xx. Los 28 contenedores previos y datos/configuración normales se preservaron. La CA fue autorizada e instalada exclusivamente en CurrentUser/Root; Windows verificó HTTPS sin omitir certificados.

No es el validador con fixtures ni migra cuentas reales: bootstrap ADMIN_TI conservado para primer acceso, cambio de contraseña y MFA humanos. E34 contiene operación, custodia y retiro de confianza. No cambia la decisión residual de los seis riesgos. Cada integrante debe generar su propia instalación privada; Git no distribuye credenciales, confianza o contenedores.
