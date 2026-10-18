# Aceptación de riesgo residual — IAM Secure

**Fecha:** 13 de octubre de 2026
**Alcance:** académico/local
**Proyecto:** IAM Secure
**Rama evaluada:** `feat/bulk-users-excel-20261005`

## Decisión

Se realizó una revisión humana de las amenazas STRIDE T01–T20 y de los controles técnicos y evidencias disponibles.

La aceptación documentada en este archivo aplica únicamente al alcance académico/local del proyecto IAM Secure. **No constituye una aceptación de riesgo para un entorno productivo real.**

## Clasificación aprobada

### 1. Tratamiento técnico verificado y riesgo residual aceptado

- **T13 — Escalada entre roles o compañías**
  - Estado técnico: `Mitigated`.
  - Riesgo residual: **aceptado para el alcance académico/local**.
  - Sustento: controles backend y 92 pruebas específicas de RBAC/multitenancy, además de regresiones relacionadas.

- **T15 — Restablecimiento MFA fuera de jerarquía o compañía**
  - Estado técnico: `Mitigated`.
  - Riesgo residual: **aceptado para el alcance académico/local**.
  - Sustento: 29 pruebas específicas sobre jerarquía, compañías, autogestión, revocación de sesiones/desafíos y re-enrolamiento TOTP.

### 2. Controles implementados con riesgo residual aceptado para el alcance académico/local

Las siguientes amenazas mantienen limitaciones, pruebas complementarias o mejoras pendientes, pero su riesgo residual se acepta para la entrega académica/local:

- **T01** — Suplantación por robo de JWT.
- **T02** — Suplantación del dispatcher.
- **T05** — Borrado de auditoría por acceso privilegiado.
- **T08** — Contraseña temporal en buzón.
- **T09** — Robo de sesión por XSS.
- **T11** — Acumulación de outbox por caída de Audit.
- **T12** — Trabajos abandonados / concurrencia.
- **T16** — Dependencias o imágenes comprometidas.
- **T17** — Manipulación de permisos entre compañías/usuarios.
- **T18** — Suplantación del canal panel ↔ permissions-grid.
- **T19** — Manipulación de XLSX.
- **T20** — Abuso de carga masiva.

Estas amenazas **no se consideran libres de riesgo** y la aceptación no implica que los controles pendientes dejen de ser recomendables.

### 3. Riesgo no aceptado y tratamiento pendiente

Las siguientes amenazas conservan brechas estructurales relevantes y continúan abiertas:

- **T03** — Alteración del tráfico HTTP.
- **T04** — Manipulación de trabajos por acceso a base de datos.
- **T06** — Pérdida de trazabilidad de operaciones.
- **T07** — Exposición de secretos MFA y datos personales.
- **T10** — Agotamiento por login y MFA.
- **T14** — Privilegios excesivos de servicios de base de datos.

Para estas amenazas **no se acepta el riesgo residual en el estado actual**. Deben permanecer `Open` y conservar sus tratamientos pendientes.

## Criterio de cierre

La decisión distingue entre:

- **Mitigación técnica:** controles implementados y verificados.
- **Aceptación de riesgo residual:** decisión humana sobre el riesgo que permanece después de aplicar controles.
- **Riesgo pendiente:** amenaza cuyo nivel residual todavía no se considera aceptable.

La aprobación humana no sustituye pruebas, controles ni futuras mejoras técnicas.

## Aprobación

El responsable del proyecto aprueba explícitamente esta clasificación de riesgo residual para el alcance académico/local de IAM Secure.

**Aprobación registrada:** 13 de octubre de 2026.
