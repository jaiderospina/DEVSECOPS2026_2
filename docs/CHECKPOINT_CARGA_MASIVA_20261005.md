# Checkpoint de continuación — 5 de octubre de 2026

Guardado a solicitud del usuario para continuar posteriormente. Complementa los checkpoints anteriores.

## Proyecto y rama

- Proyecto original: C:\Prueba-ProyectoFinal.
- Repositorio: jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final.
- Rama de la etapa 2: feat/bulk-users-excel-20261005.
- [PR #3 en borrador](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/3); pendiente de activación/aceptación local e integración.
- Código del ajuste: `0b3ad04b2626d04724feb7b26f1258c90e52bdba`.
- Head verificado previo a este checkpoint: `14ceaec5eba8961e372689f7c3258179f685e71b`.
- Master observado: `244835d78376f7379307dc08d1cd020070a95371`; la etapa 1 de grilla está integrada allí, la etapa 2 permanece en su rama.
- Las copias de OneDrive/Documents son otros entornos; este trabajo corresponde al proyecto original.

## Avance guardado

La etapa 1 mantiene Identity (8003), Permissions (8005), panel (5173) y grilla independiente (5176). El usuario reportó que la grilla funciona con las cuentas de soporte probadas.

La etapa 2 agrega **Carga masiva** para ADMIN_SOPORTE: descarga de plantilla Excel .xlsx, selección de compañía asignada, validación/vista previa de errores y duplicados, confirmación explícita, importación por fila, pausa/reanudación y descarga de resultados Excel. Máximo 500 usuarios/2 MiB; solo los tres roles de líder. La vista previa no crea cuentas ni envía correos.

**Política vigente solicitada por el usuario:** cada nuevo líder recibe las tres opciones de su área **habilitadas**, tanto al crearlo individualmente como por Excel. ADMIN_SOPORTE utiliza la grilla para casos puntuales.

| Rol | Tres opciones iniciales |
| --- | --- |
| LIDER_FACTURACION | Facturas pendientes por aprobación; Facturas pendientes por pagar; Declaración de impuestos |
| LIDER_LOGISTICA | Despachos; Entregas; Inventario y movimientos |
| LIDER_GESTION_HUMANA | Colaboradores; Novedades de personal; Vacaciones y permisos |

La política anterior de denegación inicial de esta etapa se conserva como historial y fue actualizada por este ajuste. No tomarla como comportamiento vigente.

Las asignaciones iniciales quedan limitadas al rol y compañía del nuevo usuario y se guardan en la transacción de creación. Los reintentos y duplicados no reactivan opciones deshabilitadas previamente. Se conserva el flujo de contraseña temporal, cambio obligatorio, MFA y sync_job. Los eventos de creación incluyen los códigos de las vistas iniciales, sin secretos.

Los lotes son propios del soporte, requieren sesión/MFA/credencial y alcance vigentes, se confirman dentro de 30 minutos y pueden consultarse durante siete días. La limpieza física es oportunista al validar un nuevo lote. SMTP ocurre antes del COMMIT como en la creación individual; no se promete entrega exactamente una vez.

## Evidencia verificada

- [Pipeline del código del ajuste #37414395017](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37414395017): **27/27 jobs exitosos**, **147 pruebas Pytest** (51 de carga masiva, 32 de permisos y 64 existentes) y **seis comprobaciones Chromium**.
- [Pipeline del head de documentación anterior a este checkpoint #37414595910](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37414595910): **27/27 jobs exitosos**.
- [Evidencia del ajuste](evidencia-vistas-iniciales-ci.json); [evidencia inicial conservada](evidencia-carga-masiva-ci.json).
- PostgreSQL y sesiones JWT de pruebas; correo simulado y contratos API simulados en Chromium. No prueba entrega SMTP real, login/TOTP real de nuevas cuentas, aceptación local ni despliegue.
- Este checkpoint es una adición documental. No anticipa el resultado de un pipeline que GitHub ejecute para su propio commit.

## Al retomar

1. Revisar git status en C:\Prueba-ProyectoFinal y actualizar la rama feat/bulk-users-excel-20261005. Conservar cambios locales si existen.
2. Si la etapa 2 aún no está activada, aplicar **postgres-init/12-create-cargas-usuarios.sql** al volumen existente; no borrar volúmenes ni ejecutar bootstrap. La tabla de permisos de la migración 11 ya debe estar disponible por la etapa 1.
3. Reconstruir Identity y frontend con el Compose del proyecto original. Si ya se aplicó la migración 12, el ajuste de las tres vistas solo requiere actualizar/reconstruir esos servicios.
4. Entrar como ADMIN_SOPORTE, descargar la plantilla nueva, elegir compañía y validar un lote pequeño autorizado.
5. Revisar los datos antes de confirmar. Verificar SMTP local por un canal privado; no mostrar .env. Confirmar, revisar resultados y comprobar que cada líder tiene sus tres opciones habilitadas.
6. Validar primer ingreso, cambio de contraseña y MFA con el propio usuario. Deshabilitar una opción puntual en la grilla y comprobar su efecto al volver a entrar.
7. Registrar la evidencia manual y revisar el PR #3 antes de integrar esta etapa a master. No asumir que ya está integrada o instalada en el PC.

Instrucciones PowerShell y límites: [CARGA_MASIVA_EXCEL.md](CARGA_MASIVA_EXCEL.md). Mantener pendientes DFD/STRIDE del nuevo alcance, ZAP, IaC y despliegue sin marcarlos cumplidos por estas pruebas.

## Frase para continuar

> Continuemos IAM Secure desde docs/CHECKPOINT_CARGA_MASIVA_20261005.md, en la rama feat/bulk-users-excel-20261005. Primero revisemos y activemos la carga Excel en C:\Prueba-ProyectoFinal. Los nuevos líderes deben tener sus tres vistas habilitadas por defecto y conservar las excepciones administradas desde la grilla. No mostrar secretos ni modificar master sin integrar el PR expresamente.
