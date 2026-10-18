# Punto de continuidad — 17 de octubre de 2026

## Entrega preparada

[Manual Windows/Linux](usuario/MANUAL_EJECUCION_WINDOWS_LINUX.md) · [PDF de 23 páginas](usuario/MANUAL_EJECUCION_WINDOWS_LINUX.pdf) · [E35 y QA](evidencias/2026-10-17/manual-ejecucion/README.md). El README lo enlaza en el índice, Inicio Rápido, Documentación Técnica y estado de implementación. Incluye claves propias, SMTP STARTTLS, bootstrap, primer acceso/MFA, soporte/compañía, Excel, permisos, auditoría, persistencia y solución de errores. HTTP con SMTP es el recorrido principal; HTTPS es una alternativa independiente.

El usuario confirmó cambio de contraseña temporal, activación de MFA y reingreso en otro PC. Es evidencia humana; no se atribuye sistema operativo ni prueba automatizada. No cambia la aceptación residual STRIDE ni el estado del MFA de la cuenta del laboratorio HTTPS de este PC.

## Código, CI y sincronización

Base previa a esta edición documental: `6293194c646b6bf88c4dfe2077b38b7e0e692d12`, mismo código de aplicación que E32/61a1f7a. [CI 32/32 y Sonar aprobados de 6293194](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38651606655). Nueva 85,6 %, global 56,7 % en ese corte; no se heredan a un nuevo HEAD. El espejo ejecuta CI por el bloqueo de facturación del principal. Para esta edición consulte los checks de su SHA en GitHub.

Repositorios: [principal](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final), [espejo](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci). Carpeta de trabajo: `C:/Prueba-ProyectoFinal`. Compare los tres HEAD antes de continuar; use fetch/merge --ff-only con árbol limpio y conserve cambios de colaboradores.

## Entorno y límites

El desarrollo principal conserva HTTP, cuentas, `.env` y volumen existentes. El laboratorio independiente `iam-stride-demo-20261014` usa 8443–8446 y su propia carpeta privada/volumen; no mezcle sus comandos. No regenere claves ni use `down -v` sobre datos existentes. No se requiere reconstruir servicios por esta edición documental.

El [informe técnico E33](informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_STRIDE_LAB.pdf) conserva 23 páginas y su corte histórico; el nuevo PDF de usuario es independiente. [Checkpoint técnico anterior](CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) preserva comandos y recibos E32–E34.

## Siguiente paso

1. Revisar con el equipo los límites de T03/T04/T06/T07/T10/T14 y registrar su decisión humana; siguen Open/no aceptación. T13/T15 y las otras 12 decisiones académicas no cambian.
2. Completar, si se requiere demostrar en este PC, el primer acceso/MFA del laboratorio HTTPS; la prueba del otro PC ya fue confirmada.
3. Seleccionar/completar capturas administrativas, presentar una historia Excel/permisos y grabar el video de 10–15 minutos.
4. Resolver el acceso de evaluación al repositorio privado y decidir si hace falta una nueva release Docker (1.0.0 es histórica).
5. Mantener los checks por revisión; cobertura React/global y DAST fuera de GET-only conservan sus alcances pendientes.

No se registró una nueva aceptación STRIDE, una release, un cambio de visibilidad ni una instalación Linux automatizada al redactar este manual.

## Organización del README

Por solicitud del usuario, AUTORES aparece al inicio. El resumen de avances se distribuye dentro del índice: implementación/continuidad en 7, STRIDE en 8, instalación en 10, manuales/informe/sustentación en 11, CI/cobertura/imágenes en 12 y cumplimiento/acceso de evaluación en 13. Se eliminó el apartado separado Entregables Pendientes conservando su información; Licencia pasa a 14.
