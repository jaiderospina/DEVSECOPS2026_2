# E35 — Manual de ejecución Windows/Linux

17 de octubre de 2026, America/Bogota. Actualización documental basada en la aplicación `6293194c646b6bf88c4dfe2077b38b7e0e692d12`.

[Manual editable](../../../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.md) · [PDF](../../../usuario/MANUAL_EJECUCION_WINDOWS_LINUX.pdf) · [Metadatos](../../../usuario/MANUAL_EJECUCION_WINDOWS_LINUX_METADATA.json).

El manual amplía la guía de once páginas aportada por el usuario. Tiene 23 apartados, 23 páginas, índice PDF enlazado, 32 bloques de comandos, 8 tablas y 4 capturas existentes. Se revisaron visualmente todas las páginas y se contrastaron los procedimientos con Compose, scripts y frontend. La sintaxis PowerShell/Bash se validó sin ejecutar instalaciones, SMTP ni operaciones de cuentas. [Recibo de sintaxis](COMMAND_SYNTAX.json).

La ruta principal utiliza Compose de desarrollo, HTTP y SMTP propio compatible con STARTTLS (no SMTP_SSL implícito en 465). La alternativa HTTPS usa otra configuración privada y otro volumen; no acredita correo real. Una guía Linux no equivale a haber ejecutado todas las distribuciones. Los checks de publicación se consultan por SHA en GitHub, sin heredarlos de 6293194.

## Confirmación humana de otro PC

El usuario respondió «Sí, completé todo ese recorrido» a la pregunta de si había cambiado la contraseña temporal, activado MFA y vuelto a iniciar con el autenticador. [Registro](CONFIRMACION_HUMANA.json). No se atribuye sistema operativo, recibo automatizado, nueva captura ni aceptación de riesgo a esa respuesta. El MFA del laboratorio HTTPS de este PC y la revisión de los seis riesgos STRIDE conservan su seguimiento separado.

El informe técnico E33 de 23 páginas conserva su corte E32/61a1f7a y su hash; este manual es un entregable separado. Capturas administrativas finales, video y revisión residual permanecen pendientes. [Checkpoint vigente](../../../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-17.md).
