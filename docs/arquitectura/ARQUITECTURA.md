# Manual de Arquitectura — IAM Secure

## Corte vigente - 14 de octubre de 2026

[E29: cobertura CI y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites.

El [informe PDF](../informe/INFORME_TECNICO_IAM_SECURE_2026-10-14_CIERRE_SONAR.pdf) está generado y revisado (21 páginas, índice/autores/orden solicitado). [Avance vigente](../AVANCE_ACTUAL_2026-10-14.md) y [checkpoint de equipo](../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md) son el punto actual; los documentos fechados al 6/7 de octubre son históricos. Video/capturas finales, seis riesgos no aceptados, visibilidad y decisión de nueva release siguen pendientes.

Revisado: 14 de octubre de 2026. Proyecto académico - Grupo 1 - DEVSECOPS2026_2. Las evidencias conservan sus fechas de ejecución.

## 1. Alcance y versión

IAM Secure gobierna identidades, credenciales, roles, compañías, sesiones y permisos de vistas. React/FastAPI/PostgreSQL se complementan con dos workers independientes. La creación desde Excel reutiliza el aprovisionamiento de Identity; no agrega otro microservicio.

Carga Excel, inactividad, Nginx e informe de auditoría están integrados en master mediante el PR #3 (19b54ee). La publicación 1.0.0/latest desde ab44403 es histórica y no contiene todos los cambios posteriores; el Compose actual construye las fuentes vigentes.

Las tarjetas de Facturación, Logística y Gestión Humana son vistas académicas de referencia: no ejecutan procesos financieros, logísticos o de recursos humanos.

## 2. Componentes y responsabilidades

| Componente | Responsabilidad | Ejecución |
|---|---|---|
| Frontend React/Vite | Login, MFA, administración, carga y portal por rol | Compilación Node; runtime Nginx no root en 5173 |
| Permissions-grid | Grilla administrativa en otro origen | Mismo código e imagen frontend, puerto host 5176 |
| Identity / FastAPI | Identidades, contraseña, MFA, JWT, sesiones, compañías y carga Excel | API 8003 |
| Permissions / FastAPI | Catálogo cerrado de nueve vistas y concesiones por usuario/compañía | API 8005; consulta la sesión vigente en Identity |
| Sync Worker | Reclamar sync_jobs, reintentar y recuperar trabajos | Proceso Python sin puertos; conector de sincronización simulado |
| Audit Dispatcher | Entregar auditoria_outbox a Audit Service | Proceso Python sin puertos |
| Audit Service / FastAPI | Persistir eventos sanitizados append-only e idempotentes | API 8004; token interno dedicado |
| PostgreSQL 17 | Fuente autoritativa de identidad, alcance, sesiones, permisos y colas | Red interna, volumen persistente |
| identity-bootstrap | Aprovisionamiento académico puntual | Perfil bootstrap, reutiliza Identity |
| usuarios | Servicio histórico con imagen propia publicada | No forma parte de los servicios activos del Compose actual |

Los directorios históricos autenticacion y backend no equivalen a servicios adicionales desplegados. Los procesos activos se determinan por docker-compose.yml.

## 3. Decisiones y patrones

- **Separación por responsabilidad:** Identity conserva autenticación/aprovisionamiento; Permissions administra vistas sin copiar JWT_SECRET ni la clave MFA.
- **Autorización en servidor:** cada operación comprueba usuario, roles y compañía actuales. La visibilidad de un botón no concede acceso.
- **Sesiones persistentes revocables:** el JWT identifica una sesión comprobada en PostgreSQL; no basta con que su firma y expiración sean válidas.
- **Multitenancy:** ADMIN_SOPORTE actúa sobre compañías activas asignadas y líderes dentro de ese alcance. ADMIN_TI administra soportes y su asignación.
- **Outbox transaccional:** cambios administrativos y eventos pendientes se guardan junto a los datos de negocio; el dispatcher los entrega después.
- **Colas persistentes:** FOR UPDATE SKIP LOCKED permite reclamar trabajo concurrente; reintentos y recuperación evitan perder trabajos interrumpidos.
- **Idempotencia:** event_uuid evita duplicar auditoría; el bloqueo y el resultado persistido de una fila evitan recrear usuarios al retomar un lote.
- **Mínimo privilegio de contenedor:** siete imágenes propias verificadas con UID efectivo distinto de cero; workers sin puertos ni secretos ajenos.
- **Frontend multietapa:** herramientas de compilación fuera de la imagen final, CSP compartida y archivos estáticos en Nginx.

PostgreSQL es compartido por servicios y colas; esta arquitectura no acredita independencia completa de bases por microservicio. El conector Sync sigue simulado.

## 4. Persistencia

| Área | Tablas principales |
|---|---|
| Identidad y RBAC | usuarios_plataforma, credenciales, roles_plataforma, usuario_roles_plataforma |
| Organización | companias, usuario_companias_plataforma |
| Seguridad | sesiones y estructuras MFA/desafíos de las migraciones 06/07 |
| Trabajo asíncrono | sync_jobs, auditoria_outbox |
| Auditoría | auditoria_eventos |
| Vistas | permisos_usuario_compania, permisos_migraciones (migración 11) |
| Excel | cargas_usuarios, cargas_usuario_filas (migración 12) |

La migración 11 adopta una sola vez las vistas del alcance anterior y no reactiva excepciones al repetirse. La creación nueva, individual o por Excel, concede las tres vistas del rol dentro de su compañía en la transacción de aprovisionamiento. Duplicados no modifican cuentas ni reactivan permisos.

En un volumen nuevo, postgres-init se ejecuta al inicializar PostgreSQL. En un volumen existente, los scripts nuevos requieren aplicación explícita; reconstruir contenedores no migra el volumen.

## 5. Autenticación, sesión y permisos

POST /auth/login verifica primer factor y devuelve el desafío MFA correspondiente. Los endpoints de enrolamiento/activación obligatorios o verificación TOTP completan el segundo factor; una sesión con contraseña temporal mantiene las restricciones de cambio obligatorio.

Las contraseñas se almacenan como hash Argon2; el secreto TOTP se cifra y el desafío de login se conserva como hash, con expiración, uso único e intentos limitados. No se incluyen secretos en diagramas, logs de documentación o capturas.

El límite predeterminado de inactividad es cinco minutos, en Identity y frontend. El panel limpia su sesión sin esperar la respuesta de logout y comprueba vencimiento al recuperar foco. La grilla recibe sesión por mensajes comprobados por origen, ventana y nonce, la conserva solo en memoria y retira datos/controles al expirar. Las sondas automáticas no cuentan como actividad humana. La API mantiene su comprobación autoritativa.

Permissions consulta /auth/me en Identity y vuelve a comprobar alcance en PostgreSQL. Usa versión de permiso para detectar ediciones concurrentes (409); las consultas de vistas vuelven a autorizar el código solicitado. Faltante o deshabilitado significa denegación.

## 6. Carga masiva Excel

Solo ADMIN_SOPORTE vigente, con compañía activa asignada, puede crear y consultar sus lotes. Se admite una compañía por lote, hasta 500 filas y 2 MiB, exclusivamente XLSX sin fórmulas/macros/vínculos externos.

1. Descargar plantilla: id_externo, nombre, email, rol.
2. Validar: parser, duplicados, catálogo de rol y alcance; persistir vista previa sin crear usuarios ni enviar correo.
3. Confirmar explícitamente la creación y el envío.
4. Procesar filas secuenciales desde el navegador; cada fila se protege y confirma en la transacción de aprovisionamiento.
5. Consultar lote persistido, pausar/retomar y exportar resultados sin secretos.

La confirmación vence a los 30 minutos; el historial se conserva siete días y su eliminación es oportunista en la próxima validación. El archivo original no se guarda. El detalle de límites y retención está en [Carga masiva](../CARGA_MASIVA_EXCEL.md).

SMTP ocurre antes del COMMIT y no es transaccional. Un error de envío revierte la fila; un fallo de base posterior al envío puede dejar un correo sin cuenta confirmada. No se promete entrega exactamente una vez. Las filas con ERROR no se reintentan automáticamente.

## 7. Red, contenedores y configuración

El [diagrama de despliegue](../diagramas/uml/DESPLIEGUE.md) representa el Compose de desarrollo: frontend 5173, Identity 8003 y PostgreSQL 5433 publicados en host; grilla 5176, Permissions 8005 y Audit 8004 limitados a loopback. No hay puertos de host para workers.

La red iam_network comunica contenedores; postgres_data conserva datos. PostgreSQL dispone de healthcheck; depends_on no sustituye una comprobación de salud continua de la aplicación.

VITE_API_URL, VITE_PERMISSIONS_API_URL y el límite frontend se fijan al compilar; no son secretos ni cambian un bundle ya publicado mediante variables runtime. Nginx restringe hosts y emite CSP/cabeceras. Cambiar de dominio exige revisar server_name, CORS y orígenes de CSP.

Docker Hub 1.0.0 incluye siete imágenes; grilla reutiliza frontend y bootstrap reutiliza Identity. PostgreSQL usa la imagen oficial. [Guía y digests](../despliegue/IMAGENES_Y_DOCKERHUB.md).

## 8. Diagramas como código

- [Componentes](../diagramas/uml/COMPONENTES.md).
- [Despliegue](../diagramas/uml/DESPLIEGUE.md).
- [Secuencia de autenticación y expiración](../diagramas/uml/SECUENCIA_AUTENTICACION.md).
- [Casos de uso](../diagramas/uml/CASOS_USO.md) y [fuente PlantUML](../diagramas/uml/CASOS_USO.puml).
- [Threat Dragon / DFD](../diagramas/threat-model/README.md).
- [STRIDE](../seguridad/stride-matrix.md).

Los cuatro UML describen el alcance actual. Threat Dragon contiene DFD 0/1 y T01–T20, incluyendo Permissions/grilla/Excel; la revisión visual/exportación y la decisión humana de riesgo residual fueron completadas el 13 de octubre de 2026. El estado vigente es 18 amenazas Open y T13/T15 Mitigated; T03, T04, T06, T07, T10 y T14 conservan riesgo residual no aceptado y tratamiento pendiente. Mermaid UML no sustituye los DFD exigidos de Threat Dragon.

## 9. Evidencia y límites

[CI de contenedores](../evidencias/2026-10-06/CONTENEDORES_CI_9b6affc.json): 27 trabajos, 147 Pytest, 11 comprobaciones Chromium y seis pruebas Node aprobados; frontend 252806015 → 13069479 bytes sin comprimir, reducción 94,83 %.

[Publicación Docker Hub](../evidencias/2026-10-07/DOCKERHUB_1.0.0_37574847806.json): 29 trabajos y 14 tags push/pull verificados. No acredita descarga anónima ni despliegue integral desde esas imágenes.

[Validación funcional](../VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md): usuario confirmó creación, primer acceso, MFA/portal, excepción de permisos, duplicado/exportación e inactividad en grilla/carga. Las pruebas CI de navegador usan APIs simuladas y reloj controlado; las de Permissions/carga incluyen PostgreSQL real y correo simulado. Varias filas con correo real permanecen pausadas por petición del usuario.

IaC/Checkov/CD se acreditan por E10/E24 y la instalación limpia independiente por E21; son alcances separados. ZAP staging está automatizado, E26/E27. Este manual enlaza esas evidencias; no las sustituye.

## 10. Navegación

[README](../../README.md) · [Desarrollo](../desarrollo/DESARROLLO.md) · [Despliegue](../despliegue/DESPLIEGUE.md) · [Seguridad](../seguridad/SEGURIDAD.md) · [Usuario](../usuario/MANUAL_USUARIO.md) · [Matriz](../trazabilidad/MATRIZ_REQUISITOS.md).

## Correspondencia con el DFD actualizado en f624196

D1 identidad/sesiones/MFA/compañías, D2 sync_jobs, D3 auditoria_outbox, D4 auditoria_eventos, D5 permisos y D6 cargas/filas son particiones lógicas del mismo PostgreSQL. Permissions lee identidad/roles/alcance en D1, consulta/modifica D5 y escribe D3 en la transacción de cambio. Identity escribe D5 al aprovisionar líderes y D6 durante validación/confirmación/procesamiento Excel; reutiliza identidad, colas y SMTP existentes.

Panel y grilla están fuera del límite Docker, en orígenes separados del navegador, distribuidos por Nginx. postMessage transfiere sesión y expiración con validación de ventana/origen/nonce; las API siguen autorizando en servidor. El DFD representa solicitudes y respuestas de Permissions, /auth/me y Excel sin agregar un servicio de carga.

## Tratamiento STRIDE verificado - laboratorio local

[Perfil seguro](../seguridad/STRIDE_HARDENING_LAB.md) y [E32](../evidencias/2026-10-14/stride-hardening-lab/README.md): 61a1f7a, [CI 32/32](https://github.com/yeisonfblopez/DevSecOps-proyecto-Final-ci/actions/runs/38638956405), Sonar nueva 85,6 %/global 56,7 %, Quality Gate passed. TLS/roles/rate/backup se probaron en perfil independiente; reset MFA/outbox atómicos y alertas son código común. La migración 13 debe aplicarse a volúmenes existentes antes de reconstruir Permissions, conservando datos/.env. El Compose de desarrollo mantiene HTTP/DB administrativo. Seis riesgos siguen Open/no aceptación posterior; el equipo debe revisar adopción, límites y decisión residual. E29/E30 mantienen su corte histórico.
