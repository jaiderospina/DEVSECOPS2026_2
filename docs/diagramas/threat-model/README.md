# Threat Dragon — DFD nivel 0 y nivel 1

Modelo vigente integrado en `master` mediante PR #3; referencias de evidencia revisadas el 14 de octubre de 2026. La rama `feat/bulk-users-excel-20261005` conserva la base histórica. Modelo as-is, versión Threat Dragon 2.6.2. La revisión histórica inicial del DFD se realizó sobre `f624196`; el estado de amenazas fue actualizado posteriormente con la decisión humana de riesgo residual del 13 de octubre de 2026.
Esquema oficial: https://www.threatdragon.com/docs/development/schema.html
Se conserva copia del esquema para validación reproducible.

## Alcance y límites

Nivel 0: usuario/administrador → proceso 0 IAM Secure → proveedor SMTP.
Nivel 1 descompone proceso 0 en panel React, permissions-grid, Identity, Permissions, Sync Worker, Audit Dispatcher, Audit Service y almacenes D1–D6.
D1–D6 son particiones lógicas de la misma instancia PostgreSQL, no bases físicamente aisladas.
Panel y grilla se ejecutan en el navegador, en orígenes :5173 y :5176 separados, y son servidos por Nginx. Sus límites se representan fuera del host Docker; el servidor estático se documenta como distribución, no como ejecución de React dentro de Docker.
El bootstrap es un proceso operativo puntual reutilizando Identity; no es una API permanente.
El conector Sync es simulado: no hay evidencia de sistema externo real.
Repositorios, runner CI, imágenes y dependencias constituyen la cadena de suministro descrita en T16.
Los servicios heredados autenticacion/backend/usuarios no participan en Compose actual; usuarios se incluye en build por tener Dockerfile.

HTTP en Compose actual y protocolo PostgreSQL no tienen TLS demostrado. SMTP usa STARTTLS en correo.py.
CSP y cabeceras están implementadas; no se supone TLS, separación de roles DB, alertas o backups cifrados ya instalados.
Credenciales y claves son activos; sus valores no se incluyen en el modelo.

## Abrir, revisar y conservar evidencia

1. En Threat Dragon 2.6.2, abrir modelo local y seleccionar `threat-dragon-model.json`.
2. Abrir ambos diagramas, revisar límites y rutas, ajustar disposición visual si hay cruces.
3. Revisar T01–T20 contra la matriz STRIDE y la arquitectura.
4. Guardar desde Threat Dragon; volver a ejecutar `python scripts/validate_threat_model.py`.
5. Exportar imágenes de ambos DFD y reporte. Registrar versión, fecha, revisor y commit.
6. No cerrar una amenaza sin prueba del control y decisión explícita de riesgo residual.

La validación del esquema y referencias no sustituye la comprobación visual de importación/exportación en Threat Dragon.
Estado: revisión visual, importación, guardado y exportación completados el **13 de octubre de 2026** en **Threat Dragon web 2.6.2-latest**, mediante sesión local. Revisión visual aprobada por el usuario. Posteriormente se registró la decisión humana de riesgo residual para el alcance académico/local: **T13 y T15 quedaron Mitigated y 18 amenazas permanecen Open**. La aceptación académica/local no equivale a aceptación productiva.
Ver [STRIDE](../../seguridad/stride-matrix.md).

## Alcance ampliado y evidencia

D5 representa permisos_usuario_compania; D6 cargas_usuarios/cargas_usuario_filas. Permissions consulta Identity por /auth/me y PostgreSQL por identidad/alcance/permisos, y escribe outbox. Identity concede permisos iniciales al aprovisionar líderes. Excel es un flujo dentro de Identity, con validación, confirmación y resultados persistidos; no es un servicio nuevo.

El canal panel↔grilla usa postMessage (no HTTP ni garantía de cifrado), ventana, origen exacto, nonce y expiresAt. La grilla conserva el token en memoria. HTTP y PostgreSQL permanecen sin TLS demostrado; SMTP usa STARTTLS.

T13 y T15 cuentan con tratamiento técnico verificado y estado `Mitigated`. Su riesgo residual fue aceptado explícitamente para el alcance académico/local. Sus controles cuentan con evidencia local: 92 pruebas T13 y 29 T15, más 124 regresiones, 245 aprobadas en total. [Alcance y limitaciones](../../evidencias/2026-10-13/T13_T15_VALIDACION.md) · [Aceptación de riesgo residual](../../evidencias/2026-10-13/ACEPTACION_RIESGO_RESIDUAL.md). El tratamiento se actualiza sin cambios en elementos ni flujos del DFD.

DAST activo archivado en f624196: laboratorio aislado, GET controlado, 39 combinaciones API/rol, 7 scans, 1.947 requests, 0 alertas en ese alcance. docs/evidencias/2026-10-11/dast-active-readonly/SUMMARY.md. No es active scan completo de toda la aplicación ni cubre mutaciones, login/MFA o canal entre ventanas. La evidencia está [archivada](../../evidencias/2026-10-11/dast-active-readonly/SUMMARY.md) en f624196; la base ejecutada del laboratorio fue 2b0abd4. Cinco reglas a intensidad LOW, sin spider/AJAX spider y con sesiones sintéticas. No acredita XSS frontend, carga XLSX ni resets MFA.

## Evidencias de revisión visual — 13 de octubre de 2026

Base histórica de esa revisión visual: `f624196`, rama `feat/bulk-users-excel-20261005`, con los cambios del modelo todavía sin commit en ese momento. Se revisaron ambos DFD, los límites navegador/Docker, Permissions/grilla, los almacenes lógicos D1–D6, los flujos y las asociaciones T01–T20. Se ajustó únicamente la presentación gráfica, sin modificar arquitectura ni amenazas. En esa validación previa el reporte mostró 20 amenazas abiertas. Posteriormente, tras la revisión humana de riesgo residual, el estado vigente pasó a **18 Open y 2 Mitigated (T13/T15)**. El guardado en copia separada y las exportaciones se comprobaron; la copia guardada también pasó el validador y no se incorpora al repositorio.

Exportaciones definitivas conservadas sin regeneración:

- [DFD nivel 0 — PNG](../../evidencias/2026-10-13/threat-model/dfd-nivel-0.png).
- [DFD nivel 1 — SVG ampliable](../../evidencias/2026-10-13/threat-model/dfd-nivel-1.svg).
- [DFD nivel 1 — PNG](../../evidencias/2026-10-13/threat-model/dfd-nivel-1.png).

El nivel 1 conserva cruces de líneas por su densidad; el SVG permite ampliar y seguir las rutas identificadas. La aprobación visual no cierra amenazas ni implica aceptación del riesgo residual.


## Corte histórico CI/DAST d6c3440 - 14 de octubre de 2026

[E27](../../evidencias/2026-10-14/CI_SONAR_ZAP_D6C3440.json): CI 30/30, ZAP staging GET-only aprobado y Sonar failed solo por cobertura nueva. Se actualizó únicamente texto de referencias en T09/T16/T17 y summary; elementos, flujos, límites, estados y decisiones residuales permanecen iguales a la base validada. Los exports DFD del 13 conservan su fecha y disposición. [Checkpoint actual](../../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md).

## Cierre histórico de cobertura CI f87243e

[E29](../../evidencias/2026-10-14/sonar-cobertura-ci/README.md): f87243e, CI 31/31 y Quality Gate aprobado, 88,1 % de cobertura nueva. Se ejecutaron las 121 pruebas T13/T15 en CI. La mejora de cobertura no cambia elementos, flujos, estados, severidades ni decisiones humanas del modelo: T03/T04/T06/T07/T10/T14 mantenían tratamiento pendiente en ese corte. E27 y los exports DFD conservan sus cortes históricos.

## Tratamiento STRIDE verificado - laboratorio local

[Perfil seguro](../../seguridad/STRIDE_HARDENING_LAB.md) y [E32](../../evidencias/2026-10-14/stride-hardening-lab/README.md): 61a1f7a, [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Sonar nueva 85,6 %/global 56,7 %, Quality Gate passed. TLS/roles/rate/backup se probaron en perfil independiente; reset MFA/outbox atómicos y alertas son código común. La migración 13 debe aplicarse a volúmenes existentes antes de reconstruir Permissions, conservando datos/.env. El Compose de desarrollo mantiene HTTP/DB administrativo. Seis riesgos siguen Open/no aceptación posterior; el equipo debe revisar adopción, límites y decisión residual. E29/E30 mantienen su corte histórico.
