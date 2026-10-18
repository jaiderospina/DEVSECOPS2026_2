# Validación del Sync Worker

## Estado

El Sync Worker de IAM Secure fue validado mediante pruebas funcionales,
pruebas de concurrencia real y pruebas automatizadas.

## Funcionalidades validadas

- Procesamiento asíncrono independiente.
- Persistencia de trabajos en PostgreSQL mediante sync_jobs.
- Operaciones PROVISIONAR, MODIFICAR, DESHABILITAR y REVOCAR.
- Reintentos automáticos.
- Estado FALLIDO al alcanzar el máximo de intentos.
- Recuperación de trabajos interrumpidos.
- Identificación de cada instancia mediante worker_id.
- Ejecución no-root en Docker.
- Integración con Identity Service.
- Integración con usuarios y compañías.
- Apagado controlado mediante SIGTERM y SIGINT.
- Reintento de conexión cuando PostgreSQL no está disponible.

## Prueba de concurrencia real

Se generaron ocho trabajos, jobs 16 a 23, y se ejecutaron dos instancias
independientes del Worker:

- sync-concurrency-a
- sync-concurrency-b

Resultado:

- Worker A procesó 6 trabajos.
- Worker B procesó 2 trabajos.
- Los 8 trabajos finalizaron en COMPLETADO.
- Todos registraron un solo intento.
- Ningún job fue procesado por ambos Workers.
- Hubo procesamiento simultáneo real.

La cola utiliza:

FOR UPDATE SKIP LOCKED

para impedir que dos Workers reclamen simultáneamente el mismo trabajo.

## Pruebas automatizadas

La suite se encuentra en:

tests/sync_worker/test_worker.py

Resultado obtenido:

Ran 23 tests
OK

Las pruebas cubren configuración, validación de objetivos, operaciones,
reclamación de trabajos, propiedad mediante worker_id, reintentos,
FALLIDO, recuperación, manejo seguro de errores, reconexión a PostgreSQL
y apagado controlado.

## Consideración actual

El conector implementado actualmente es simulado y demuestra la
arquitectura asíncrona requerida por el proyecto académico.

En una evolución posterior puede sustituirse por conectores hacia
directorios corporativos, aplicaciones empresariales o APIs externas.

## Prueba de reproducibilidad desde clon limpio

Se realizó una validación completa utilizando un clon nuevo del repositorio
desde GitHub.

Commit utilizado:

`dd8508d test: valida Sync Worker con concurrencia y pruebas automatizadas`

### Procedimiento validado

- Se clonó el repositorio en un directorio independiente.
- Git confirmó que el repositorio estaba limpio y sincronizado con `master`.
- Se creó un archivo `.env` exclusivamente local.
- Git confirmó que `.env` estaba correctamente ignorado.
- `docker compose config --quiet` finalizó sin errores.
- Las imágenes de Identity Service, Frontend y Sync Worker fueron construidas
  desde cero mediante `docker compose build --no-cache`.
- PostgreSQL inició en estado `healthy`.
- Identity Service inició correctamente.
- Frontend inició correctamente.
- Sync Worker estableció conexión con PostgreSQL y quedó listo para procesar
  trabajos.
- La tabla `sync_jobs` fue creada automáticamente por los scripts de
  inicialización.
- En la instalación limpia, `sync_jobs` inició con cero registros.
- El clon utilizó un volumen PostgreSQL independiente.

### Validación de aislamiento

Después de finalizar la prueba se eliminó el volumen PostgreSQL perteneciente
exclusivamente al clon limpio.

Posteriormente se restauró el entorno principal y se confirmó que su volumen
persistente permanecía intacto.

La base de datos original conservó:

- 23 trabajos en `sync_jobs`.
- Primer job: 1.
- Último job: 23.
- Los jobs 16 a 23 correspondientes a la prueba de concurrencia permanecieron
  en estado `COMPLETADO`.
- Todos los jobs 16 a 23 conservaron exactamente un intento.
- Los registros mantuvieron los identificadores de los Workers
  `sync-concurrency-a` y `sync-concurrency-b`.

### Resultado

La prueba confirma que IAM Secure y su Sync Worker pueden ser clonados,
configurados, construidos y ejecutados desde GitHub sin depender del estado
local del equipo original.

También confirma que los volúmenes Docker de diferentes instalaciones quedan
aislados entre sí.
