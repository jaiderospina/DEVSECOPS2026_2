# Validación de carga masiva e inactividad — 6 de octubre de 2026

Las pruebas de esta sesión se realizaron en el proyecto original `C:\Prueba-ProyectoFinal`, sobre la rama `feat/bulk-users-excel-20261005`. **Carga masiva e inactividad están probadas y funcionan correctamente**, según las pruebas y la confirmación del usuario. Se conserva el historial anterior; este registro actualiza las referencias previas a activación local pendiente.

### Carga masiva Excel: activación y prueba funcional

ADMIN_SOPORTE dispone de descarga de plantilla `.xlsx`, selección de compañía asignada, validación y vista previa, confirmación de creación y resultados descargables. Los nuevos líderes reciben habilitadas las tres vistas de su área; la grilla permite administrar excepciones.

| Comprobación local | Resultado |
|---|---|
| Activación de la etapa 2 | Rama actualizada; Identity/frontend reconstruidos; existencia de `cargas_usuarios` y `cargas_usuario_filas` confirmada mediante PostgreSQL |
| Validación de rol | Se rechazó un rol escrito con espacios; al corregirlo a `LIDER_GESTION_HUMANA`, la fila quedó lista |
| Vista previa | Una fila válida pendiente, cero inválidas y cero creadas antes de confirmar |
| Importación autorizada | Una cuenta creada, cero pendientes y cero errores de creación |
| Identidad y compañía | Cuenta activa, con el rol y la compañía de destino previstos |
| Ingreso y vistas iniciales | Capturas de vinculación Authenticator y del panel autenticado de Gestión Humana con sus tres opciones visibles |
| Excepción en grilla | Funcionamiento confirmado por el usuario; al deshabilitar Vacaciones y permisos, permanecieron visibles Colaboradores y Novedades de personal |
| Validación de duplicado | El mismo Excel produjo una fila inválida, cero válidas pendientes y cero creadas; motivo de identificación o correo ya registrado |
| Conservación de excepción | Después de validar el duplicado, Vacaciones y permisos continuó deshabilitada |
| Exportación de resultados | Descarga correcta confirmada por el usuario; la tabla exportada coincide con el estado inválido y el motivo del duplicado |

La aplicación informó el envío de la contraseña temporal por su flujo de correo. La recepción en el buzón y el cambio de contraseña temporal no tuvieron una confirmación separada en esta sesión. Se acredita el ingreso al panel mediante las capturas aportadas, sin publicar nombres, identificaciones, correos, contraseñas, tokens o material MFA.

Documentación en la rama de etapa 2: [Carga masiva Excel](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/docs/CARGA_MASIVA_EXCEL.md) y [checkpoint anterior](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/docs/CHECKPOINT_CARGA_MASIVA_20261005.md).

### Cierre por cinco minutos de inactividad: corregido y confirmado localmente

Se identificó que el panel esperaba la respuesta de `/auth/logout` antes de limpiar la sesión. Una petición sin respuesta podía mantener visibles las pantallas. El ajuste local elimina inmediatamente la sesión y solicita después la revocación, con un plazo de red de cinco segundos.

El panel comprueba el vencimiento también al recuperar el foco o volver de suspensión. La grilla recibe el vencimiento por el canal entre ventanas y retira su sesión y controles al expirar. Sus mensajes de comprobación no renuevan la sesión del servidor ni cuentan como interacción humana. La carga masiva se desmonta al limpiar la sesión, utilizando su cancelación de peticiones y el progreso persistido del lote.

El usuario reconstruyó `identity`, `frontend` y `permissions-grid`, y confirmó que `SESSION_INACTIVITY_MINUTES` devuelve **5** dentro de Identity. Reportó que carga masiva se desloguea a los cinco minutos y, posteriormente, que **tanto grilla como carga masiva funcionan y muestran el mensaje de sesión expirada**. La captura de la grilla muestra el acceso bloqueado sin controles de permisos; su pestaña puede permanecer abierta con ese mensaje.

### Evidencia automatizada y límites

- La implementación de carga masiva y vistas iniciales conserva el [CI del código `0b3ad04b2626d04724feb7b26f1258c90e52bdba`](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37414395017): **27/27 jobs, 147 pruebas Pytest y seis comprobaciones Chromium aprobados**. Correo simulado y contratos API simulados de navegador; [registro en su rama](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/blob/feat/bulk-users-excel-20261005/docs/evidencia-vistas-iniciales-ci.json).
- Para el ajuste local de inactividad aprobaron la compilación Vite y **cinco comprobaciones Playwright en Edge** con API simulada y reloj controlado: cierre de carga masiva con logout sin respuesta; actividad real de grilla y expiración sin renovación por mensajes; vencimiento independiente en grilla; cierre manual sin esperar la red; y rechazo de interacción después de suspensión.
- También aprobaron las **seis comprobaciones existentes de grilla y carga masiva**, con la SPA compilada y contratos simulados. Las cinco comprobaciones de inactividad se repitieron satisfactoriamente contra las páginas servidas por los contenedores reconstruidos.
- El lint local se intentó, pero Windows bloqueó la carga de la dependencia nativa de oxlint mediante Control de aplicaciones. Ese intento no se registra como aprobado.
- Las pruebas locales y las confirmaciones del usuario complementan la evidencia anterior. No acreditan un nuevo escaneo ZAP, auditoría local, pruebas de volumen o despliegue en otro PC.

### Estado en GitHub y siguiente paso

La etapa 1 quedó integrada en `master` mediante el PR #2. La etapa 2 permanece en `feat/bulk-users-excel-20261005`, con el [PR #3 abierto en borrador](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/3), todavía sin integrar. El ajuste de inactividad y su nueva prueba `tests/session_idle/check.mjs` están publicados en el [commit `624ab1d`](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/commit/624ab1dc83e469c1b65b0e6fdd94c0524e4d3830). Su [CI remoto, run 37570583715](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37570583715), terminó aprobado: **27/27 trabajos, 147 pruebas Pytest y 11 comprobaciones Chromium**, incluidas las cinco de inactividad. El lint de frontend también aprobó en CI. [Registro duradero de jobs, conteos y alcance](evidencias/2026-10-06/INACTIVIDAD_CI_624ab1d.json).

Los controles de navegador usan API simulada y reloj controlado; la integración backend utiliza PostgreSQL de pruebas. No se enviaron nuevos correos reales durante estas verificaciones. La carga Excel y el ajuste de inactividad continúan sin integrar en master; publicar este registro y los manuales en master no integra su código.

**Pendiente a solicitud del usuario:** conseguir correos funcionales para importar un lote con varias filas, incluyendo `LIDER_FACTURACION` y `LIDER_LOGISTICA`, y comprobar sus tres vistas iniciales, recepción de correo, cambio de contraseña y MFA. La prueba realizada hasta ahora corresponde a una cuenta de Gestión Humana y queda validada en ese alcance. Estas pruebas adicionales amplían la cobertura; no cambian la confirmación de funcionamiento de carga masiva e inactividad. También quedan por ampliar las pruebas manuales de pausa/reanudación, reactivación e aislamiento entre compañías/soportes.

Para retomar: continuar sobre la rama de etapa 2 y conservar los cambios locales antes de actualizar el clon original; el ajuste ya está publicado y su CI aprobó. Completar las pruebas adicionales cuando haya correos funcionales y revisar el PR #3 para una eventual integración autorizada. DFD/STRIDE del nuevo alcance, ZAP automatizado contra staging y cobertura específica de grilla/carga, IaC y los entregables académicos mantienen sus pendientes. Los baselines y el retest pasivo autenticado ZAP del 30 de septiembre ya están realizados y documentados.

[Estado actual en el README](../README.md#7-estado-actual-de-implementación).
