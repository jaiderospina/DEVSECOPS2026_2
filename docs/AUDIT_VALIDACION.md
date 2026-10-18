# Validación de Audit Service y Audit Dispatcher

> **Actualizado:** 30 de septiembre de 2026  
> **Commit funcional de referencia:** `7237673`

## Arquitectura validada

```text
Identity Service
      |
      v
auditoria_outbox
      |
      v
Audit Dispatcher
      |
      v
Audit Service
      |
      v
auditoria_eventos
```

Identity Service no conoce el token interno de Audit Service. Su responsabilidad de entrega termina al persistir el evento sanitizado en la Outbox; Audit Dispatcher utiliza el token para la comunicación HTTP interna.

## Audit Service

- contenedor independiente;
- usuario no-root `audituser`;
- `GET /health`;
- `POST /eventos`;
- token interno dedicado;
- comparación segura del token;
- segunda sanitización de `detalle`;
- límite de tamaño;
- validación estricta mediante Pydantic;
- timestamps con zona horaria;
- idempotencia mediante `evento_uuid`;
- sin endpoints `UPDATE`, `PATCH` o `DELETE`.

## Persistencia append-only

La tabla `auditoria_eventos` fue validada como inmutable:

- INSERT permitido;
- UPDATE bloqueado por trigger;
- DELETE bloqueado por trigger.

Los identificadores históricos de usuario y compañía no utilizan claves foráneas deliberadamente para conservar la referencia histórica.

## Sanitización

Se verificó la redacción de campos sensibles, incluyendo:

```text
password       -> [REDACTED]
access_token   -> [REDACTED]
totp_secret    -> [REDACTED]
```

Los objetos no soportados se convierten en `[UNSUPPORTED_TYPE]` sin invocar su representación potencialmente sensible.

## Outbox

`auditoria_outbox` soporta:

- `PENDIENTE`;
- `PROCESANDO`;
- `COMPLETADO`;
- `FALLIDO`;
- contador de intentos;
- `disponible_desde`;
- `worker_id`;
- recuperación de eventos interrumpidos.

Es una cola persistente operacional. No se documenta como una transacción distribuida entre la operación de negocio y Audit Service.

## Resiliencia

Con Audit Service detenido se comprobó que el evento permanecía en `auditoria_outbox` y podía entregarse después de recuperar el servicio.

## Reintentos y FALLIDO

Se validaron:

- múltiples intentos;
- código seguro `AUDIT_SERVICE_NO_DISPONIBLE`;
- transición a `FALLIDO`;
- reencolado administrativo;
- entrega posterior exitosa;
- limpieza de `ultimo_error` después del éxito.

## Idempotencia

Se reentregó un evento ya persistido.

Audit Service respondió con `creado=False` y `auditoria_eventos` mantuvo una sola fila para el mismo `evento_uuid`.

## Concurrencia real

Dos Audit Dispatchers iniciaron mediante una barrera compartida y procesaron 30 eventos.

Resultado:

```text
Eventos totales:        30
Completados:            30
Un solo intento:        30
UUID únicos:            30
Workers utilizados:      2

Worker A:               16
Worker B:               14
```

Esto valida `FOR UPDATE SKIP LOCKED` en ejecución concurrente real.

## Pruebas automatizadas

### Audit Service

```text
Ran 13 tests
OK
```

### Audit Dispatcher

```text
Ran 19 tests
OK
```

### Total

```text
32 pruebas automatizadas aprobadas.
```

Las suites se ejecutaron con `--network none` y dobles de SQL/HTTP, por lo que no modifican PostgreSQL real.

## Cobertura administrativa incorporada

### Usuarios

```text
USUARIO_CREADO
USUARIO_MODIFICADO
USUARIO_ESTADO_MODIFICADO
USUARIO_ROL_MODIFICADO
MFA_RESTABLECIDO_ADMIN
```

### Compañías

```text
COMPANIA_CREADA
COMPANIA_MODIFICADA
COMPANIA_ASIGNADA
COMPANIA_REASIGNADA
COMPANIA_DESASIGNADA
COMPANIA_ESTADO_MODIFICADO
```

Los eventos se registran después de completar exitosamente las mutaciones correspondientes para evitar documentar como exitosas operaciones que hayan fallado.

## Prueba funcional final

Se generó un evento administrativo sintético `COMPANIA_MODIFICADA`.

Resultado:

- Outbox: `COMPLETADO`;
- intentos: `1`;
- `ultimo_error`: vacío;
- Audit Service persistió `resultado=EXITO`;
- el mismo `evento_uuid` fue observado en `auditoria_outbox` y `auditoria_eventos`.

Esto confirma el recorrido:

```text
Identity
  -> auditoria_outbox
  -> Audit Dispatcher
  -> Audit Service
  -> auditoria_eventos
```

## Próximo hito

Ejecutar la arquitectura completa desde GitHub en un segundo PC físico, con secretos nuevos y sin reutilizar volúmenes o archivos locales del entorno principal.

Ver [Avance del proyecto](AVANCE_2026-09-30.md).
