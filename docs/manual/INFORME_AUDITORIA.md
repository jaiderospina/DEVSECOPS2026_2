# Informe de auditoría para ADMIN TI

Esta opción genera un Excel con accesos y acciones de usuarios registrados por Audit Service. Está implementada en la rama del PR #3, que permanece en borrador. Para que aparezca en un entorno instalado, debe ejecutarse el código actualizado de Identity y frontend; las imágenes 1.0.0 ya publicadas no contienen esta función.

**Estado local al 7 de octubre:** frontend/Identity actualizados y descarga aceptada por el usuario, incluido nombre/correo del actor. [Aceptación E17](../evidencias/2026-10-07/AVANCE_CONFIRMADO_20261007.json). Ese corte conservaba pendientes de CI/Sonar y release. E29 acredita posteriormente CI/Quality Gate de master; una nueva versión de imágenes y su despliegue mantienen decisión pendiente.

## Descargar el informe

1. Inicie sesión como ADMIN TI con MFA y contraseña definitiva.
2. Abra **Informe de auditoría** en el menú lateral.
3. Seleccione **Desde** y **Hasta**. Ambas fechas se incluyen completas en UTC; por defecto se proponen los últimos siete días.
4. Opcionalmente filtre por evento, servicio, resultado, ID de usuario o ID de compañía. Un ID de usuario incluye los eventos donde aparece como actor o como objetivo. Un filtro vacío incluye todos los valores; los filtros se combinan.
5. Pulse **Descargar Excel** y abra el archivo de su carpeta de descargas.

Ejemplos: evento LOGIN_FALLIDO, servicio identity, resultado EXITO. ADMIN TI tiene alcance global; ADMIN SOPORTE y los líderes no tienen esta opción y el backend rechaza su acceso directo.

## Contenido del Excel

**Auditoria** contiene ID/UUID del evento, fecha UTC, servicio, evento, resultado, ID del usuario actor, nombre del actor, usuario del actor (correo), ID del usuario objetivo, ID de compañía y detalle resumido. Nombre y correo se consultan en el directorio actual y se identifican como datos actuales: no son una copia de cómo estaban al ocurrir el evento. Se conserva el ID histórico y se identifica al actor, no al usuario objetivo ni al ADMIN TI que descarga. Los usuarios inactivos conservan su identificación. Si no hay actor se muestra «Sin usuario identificado»; si el ID ya no está en el directorio, «Usuario no disponible», conservando el ID y el evento. La hoja incluye filtros y encabezados fijos.

**Resumen** contiene período, filtros, fecha UTC de generación, ID del ADMIN TI y total de eventos. Un período sin eventos genera un Excel válido con encabezados y total cero.

Cada informe admite hasta **31 días y 5.000 eventos**. Si hay más, se solicita reducir las fechas o aplicar filtros: no se descarga un conjunto parcial. El detalle se sanitiza y se resume a 2.000 caracteres, marcando los resúmenes. Los valores se escriben como texto, sin fórmulas. No se consultan contraseñas, hashes, sesiones JWT ni secretos MFA para las columnas del informe.

## Registro y disponibilidad

La generación se registra como AUDITORIA_INFORME_GENERADO, con actor, período, filtros y cantidad de eventos. La descarga no confirma que el usuario haya abierto o guardado el archivo. El nuevo evento llega a Audit Service mediante la outbox y el dispatcher habituales.

Solo aparecen eventos ya persistidos en auditoria_eventos: los pendientes de entrega aún no están incluidos. Este informe no contiene stdout de contenedores ni trazas técnicas. No cambia la retención ni modifica o elimina eventos de auditoría.

Si la sesión expiró, vuelva a iniciar sesión. Si falta MFA vigente o el rol ADMIN TI fue retirado, no se permite generar el informe. Ante un error de base de datos se devuelve un mensaje general, sin configuración interna.

[Evidencia de autorización, filtros y seguridad del Excel](../evidencias/2026-10-07/AUDITORIA_EXCEL_20261007.json).
