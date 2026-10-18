# Frontend IAM Secure — React/Vite

Actualizado: 7 de octubre de 2026. Panel por rol, entrada independiente de grilla de permisos y cierre por cinco minutos de inactividad. Código del último avance en el PR #3, en borrador y sin integrar.

## Funciones y roles

- ADMIN_TI: administración de soportes/compañías e Informe de auditoría.
- ADMIN_SOPORTE: identidades, carga masiva por compañía autorizada y grilla de permisos.
- Líderes: vistas de su área según permisos.

La visibilidad del menú complementa la autorización del backend; no sustituye sus controles.

## Informe de auditoría

ADMIN TI descarga XLSX con filtros de fechas UTC inclusivas, evento, servicio, resultado, usuario actor/objetivo y compañía. Hasta 31 días/5.000 eventos, sin descarga parcial. Dos hojas: Auditoria y Resumen. Conserva ID histórico y muestra nombre/correo actuales del actor. Cuenta, sesión, rol, credenciales y MFA se comprueban en Identity. Detalle sanitizado y texto sin fórmulas. El usuario confirmó la descarga y las columnas. [Manual](../../docs/manual/INFORME_AUDITORIA.md).

## Desarrollo y comprobaciones

```sh
npm ci
npm run dev
npm run lint
npm run build
```

Configuración pública: VITE_API_URL, VITE_PERMISSIONS_API_URL y VITE_SESSION_INACTIVITY_MINUTES. Son valores de compilación; cambios requieren reconstruir. Las credenciales del servidor se configuran fuera del frontend. Para ejecutar el sistema completo y configurar cuentas/MFA, consulte el [README principal](../../README.md#10-inicio-rápido).

## Estado y cierre

| Área | Completado | Pendiente |
|---|---|---|
| Funcionalidad local | Panel/grilla, carga, inactividad e informe aceptados en el PC | Lote de varias filas con correos reales sigue pausado |
| Pruebas | E15: 16 Node de su alcance, lint y build; E16: 86 backend incluyendo 35 auditoría | CI/Sonar integral del código vigente y cobertura medida |
| Distribución | Etapa 2 tiene frontend multietapa Nginx y publicación histórica 1.0.0; el PC usa su configuración local y código actualizado | Nueva versión publicada y despliegue simulado con auditoría; 1.0.0 no la incluye |
| Documentación | Manual y aceptación del Excel con actor registrados | Capturas administrativas de entrega y demostración final |

[E14](../../docs/evidencias/2026-10-07/SONAR_SECURITY_CI_20261007.json) · [E15](../../docs/evidencias/2026-10-07/AUDITORIA_EXCEL_20261007.json) · [E16](../../docs/evidencias/2026-10-07/AUDITORIA_ACTOR_20261007.json) · [Avance actual](../../docs/AVANCE_ACTUAL_2026-10-07.md).
