# Avance actual - IAM Secure

Revisado: 14 de octubre de 2026 (America/Bogota). Sustituye el snapshot del 7 de octubre, que se conserva como histórico.

## Corte y evidencia

- Código **61a1f7acab2c76ef8e3669ae8f6ddc7fc7172df4**: [E32](evidencias/2026-10-14/stride-hardening-lab/README.md), [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Quality Gate Sonar passed; nueva **85,6 % ≥ 80 %**, global **56,7 %**. Check: 42 issues nuevos, cero aceptados. Métricas, XML/LCOV, laboratorio y ZAP del mismo run con recibo/hashes. No atribuir estos checks a otros commits.
- **T03/T04/T06/T07/T10/T14 tratados y verificados en laboratorio**: TLS, roles DB mínimos, reset MFA/outbox atómicos, archivos privados/backup cifrado restaurado y rate limit. 183 pruebas seguridad, 86 Excel, 28 helpers, dispatcher 25 + cuatro subtests y Node 24. Laboratorio: 11 controles, MFA/auditoría reales, 30 requests/28 429/cero 5xx y limpieza confirmada.
- TLS/rate/logins separados pertenecen al perfil seguro alternativo; desarrollo conserva HTTP/postgres. La migración 13 y la reconstrucción de servicios comunes actualizan el runtime existente conservando datos/configuración. [Uso y límites](seguridad/STRIDE_HARDENING_LAB.md).
- Los seis riesgos siguen Open/no aceptación residual posterior. T13/T15 Mitigated y 12 Open aceptadas solo para el alcance académico/local; E23 no se modifica automáticamente.
- [E33 / PDF técnico actualizado](informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_STRIDE_LAB.pdf): **23 páginas**, portada, índice enlazado, autores y capítulos en el orden solicitado; [hash/QA](informe/INFORME_TECNICO_STRIDE_LAB_METADATA.json). E28/E30 preservados.

## Estado por área

| Área | Estado vigente | Cierre restante o límite |
|---|---|---|
| Identidad, MFA, RBAC y compañías | Implementados; reset MFA atómico nuevo | No afirmar E2E/productivo universal |
| Grilla, Excel, inactividad e informe XLSX | Integrados; regresiones CI aprobadas | Capturas/historia final; correos adicionales opcionales |
| CI/SAST/SCA/build/Trivy | 32/32 aprobados en 61a1f7a, espejo | Principal sigue limitado por facturación; futuros HEAD requieren checks propios |
| SonarCloud | Quality Gate passed, nueva 85,6 %, global 56,7 % | 42 issues nuevos; ampliar React/global |
| ZAP | GET-only 7 scans/39 API-rol, 1.947 requests sin alertas | Login/MFA/XLSX/mutaciones/frontend fuera de ZAP |
| STRIDE técnico | E32 probado; E34 laboratorio interactivo activo/CA autorizada para usuario Windows | Primer acceso/cambio de contraseña/MFA, custodia y decisión humana residual posterior |
| Estado STRIDE | 18 Open: 12 aceptadas localmente, seis no aceptadas | Tráfico interno/operación y límites documentados; no aceptación productiva |
| Instalación limpia | E21: iMac independiente 6d7e51c y SMTP real | Corte histórico, no sustituido por fixture sintética |
| Docker Hub/CD | Release histórica 1.0.0, siete imágenes/14 tags | CI construye código vigente pero CD por digest sigue imágenes históricas |
| Cobertura local anterior | E22: cinco servicios Python 68,59 % (badge 69 %) | No es cobertura actual/global/Sonar |
| PDF/documentación | E33 actualizado/revisado, README/matriz/checkpoint alineados | Capturas/video de 10–15 minutos |
| Acceso de evaluación | Repositorios privados | Resolver acceso/visibilidad según requisito |
| Observabilidad | Opcional | Prometheus/Grafana, Loki/ELK, Falco |

[README](../README.md) · [Checkpoint de equipo](CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) · [Matriz](trazabilidad/MATRIZ_REQUISITOS.md). E29 mantiene f87243e/88,1 %/54,5 % y E30 su PDF. No sumar suites/revisiones solapadas ni confundir perfil probado con runtime de desarrollo.

## Activación local posterior - E34

[Laboratorio interactivo](evidencias/2026-10-14/secure-demo/README.md) activo desde bdedc77: cuatro HTTPS 200/TLSv1.3, nueve servicios no root, seis logins mínimos, respaldo inicial cifrado y 30 solicitudes/24 respuestas 429/cero 5xx. Preservados 28 contenedores previos, .env y conteos de desarrollo. CA autorizada solo para CurrentUser/Root y HTTPS validado por Windows. Primer acceso humano/cambio de contraseña/MFA y revisión residual pendientes. No activa el laboratorio en otro PC por hacer pull; no migra cuentas reales ni cambia la aceptación STRIDE.


## Actualización documental — 17 de octubre de 2026

[Manual detallado Windows/Linux](usuario/MANUAL_EJECUCION_WINDOWS_LINUX.md) y [PDF de 23 páginas](usuario/MANUAL_EJECUCION_WINDOWS_LINUX.pdf) publicados como E35, enlazados en el índice README. El usuario confirmó contraseña definitiva, activación MFA y reingreso en otro PC. Esa respuesta no acepta riesgos residuales ni cambia el estado del laboratorio HTTPS de este PC. [Checkpoint vigente del 17 de octubre](CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-17.md). E33 y los recibos técnicos anteriores conservan su corte y hash.
