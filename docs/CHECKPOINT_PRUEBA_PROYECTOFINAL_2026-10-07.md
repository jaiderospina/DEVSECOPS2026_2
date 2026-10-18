# Punto de continuidad — Prueba-ProyectoFinal / IAM Secure

Registrado: 7 de octubre de 2026, America/Bogota.

## Sincronización y continuidad — E18

La carpeta `C:\Prueba-ProyectoFinal` se actualizó desde ce561e3 a la base de GitHub 9df0694 por avance directo de feat/bulk-users-excel-20261005; HEAD local/remoto coincidieron y el árbol quedó limpio. Se preservaron los cambios previos en el stash 6b8b20d951564a9a1de86e2c1835c02d58c290df, sin reaplicarlos porque su contenido ya estaba incluido en la rama. Se conservaron .env, archivos locales ignorados y PostgreSQL; no se recrearon contenedores para esta sincronización. Esta revisión añade el registro documental del cierre. [E18](evidencias/2026-10-07/SINCRONIZACION_LOCAL_GITHUB_20261007.json).

Avance orientativo: **80 %** (75–85 %), sin ponderación oficial y distinto de cobertura. Para retomar: abrir esa carpeta, comprobar la rama y `git status`, consultar la tabla de avance y continuar con CI/Sonar y nueva versión/despliegue. El PR #3 permanece en borrador, sin integrar; las imágenes históricas 1.0.0 todavía requieren actualización. E17 describe el estado anterior a sincronizar.

## Estado vigente y aceptación — E17

El informe de auditoría está activado en el PC y **aceptado por el usuario**: confirmó el Excel y luego la identificación del actor con nombre/correo, aportando una captura donde se distingue del usuario objetivo. Código funcional 7c07661; PR #3 en borrador, sin integrar.

86 regresiones PostgreSQL aprobaron la última ampliación (51 carga, 35 auditoría). Frontend/Identity locales se actualizaron; PostgreSQL conserva sus datos. Las imágenes publicadas 1.0.0 no incluyen la función nueva. El job CI consultado de 7c07661 no arrancó por facturación/límite de gasto y no aparece check Sonar confirmado.

La [tabla de avance actual](AVANCE_ACTUAL_2026-10-07.md) relaciona **completado y pendiente de cada avance parcial**. [E17](evidencias/2026-10-07/AVANCE_CONFIRMADO_20261007.json) conserva la aceptación y las revisiones. Esta sección sustituye como estado actual las notas de “despliegue/descarga pendiente” anteriores; las pruebas siguientes siguen como historial de sus respectivos commits.

## Resultado verificado histórico

El [despliegue 37578596462](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37578596462) terminó aprobado: **29/29 trabajos** sobre ed00530990a494a616fe39770de65c2529915b96 en feat/bulk-users-excel-20261005. Ansible desplegó imágenes 1.0.0 publicadas, fijadas por digest, en un runner Linux aislado. La segunda ejecución registró **ok=12, changed=0, unreachable=0, failed=0**. PostgreSQL conservó un ADMIN_TI y las tablas de permisos/cargas después de recrearse; el informe final marca persistence_verified=true.

Checkov aprobó CKV_ANSIBLE_5/6 y rechazó una fixture insegura sin ejecutarla. El validador propio de Compose aprobó ocho casos negativos. Ocho contenedores ejecutaron con UID no root, read-only y capacidades retiradas; cinco sondas HTTP devolvieron 200 y tres rutas protegidas devolvieron 401 sin sesión. PostgreSQL no publicó puerto host.

[Resumen durable](evidencias/2026-10-07/ANSIBLE_CD_37578596462.json) y siete informes íntegros en evidencias/2026-10-07/despliegue-37578596462/. Los SHA-256 de los ZIP locales coinciden con GitHub; todos los informes coinciden con sus entradas originales. El código de aplicación y las imágenes no se modificaron al registrar este cierre.

## Estado de integración y requisitos

El [PR #3](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/pull/3) permanece **abierto, en borrador y sin integrar**. Al retomar, GitHub lo reportó mergeable=true. La documentación en master puede describir avance probado en la rama; no acredita que Ansible, Compose ni el nuevo código ya estén integrados. Los commits documentales de cierre pueden disparar CI independiente; no se les atribuyen las pruebas de despliegue de ed00530990a494a616fe39770de65c2529915b96.

Requisitos 3.3 y fase 5: Ansible, Checkov, Compose de producción simulada y CD están cumplidos para el alcance probado en etapa 2. La documentación completa, la visibilidad pública y la entrega académica mantienen pendientes específicos.

## Pendientes para continuar

1. Rehabilitar Actions y aprobar el CI integral de la revisión Trivy SCA. Implementación 73154a4: ocho manifiestos validados localmente y seis jobs Python aprobados en CI previo; ocho pruebas locales y fixture vulnerable rechazada. [E11](evidencias/2026-10-07/SCA_TRIVY_20261007.json).
2. Automatizar ZAP contra staging y cubrir Permissions, compañías y carga Excel.
3. Ampliar/revisar/exportar Threat Dragon, DFD 0/1 y STRIDE; cerrar amenaza-control-riesgo residual.
4. Medir cobertura y añadir badge; completar capturas administrativas del manual.
5. Validar instalación completa del nuevo alcance en otro PC. La prueba CI omitió instalar Docker y no validó SMTP real.
6. Mantener pausado el lote de varias filas con correos funcionales hasta disponer de esos correos, conforme a la decisión del usuario.
7. Revisar integración del PR #3 por separado; resolver visibilidad pública y preparar informe PDF/video de 10–15 minutos.

La producción simulada usa HTTP local/túneles y no configura TLS ni alta disponibilidad. Los datos y secretos del PC original no fueron utilizados. No ejecutar la limpieza efímera del runner sobre el entorno personal.

**Punto actual:** Trivy SCA implementado y validado por alcance, con CI integral final bloqueado por facturación/límite de GitHub. El [run 37631174925](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37631174925) no asignó runners. Habilitar Actions desde la facturación de la cuenta y repetir la revisión vigente; no cambiar permisos del repositorio, ya habilitados según captura del usuario. Después continuar con ZAP automatizado en staging. PR #3 permanece sin integrar.

La captura de facturación aportada por el usuario confirma 2.000/2.000 minutos incluidos consumidos, $0 facturable y reinicio en 25 días. Los $12 de consumo se compensan con $12 de descuentos. No se autorizó habilitar consumo de pago; para repetir CI se requiere cuota disponible o una decisión del usuario sobre facturación.

## Revisión de seguridad del PR #3

Se corrigieron los flujos señalados por ocho avisos de rutas/argumentos de SonarCloud sobre 3bfde80. Implementación ef41394: límites de archivos, informes JSON atómicos, configuración de CI exclusiva y privada, proyecto/IDs/operaciones Docker validados y salida Nginx fija. Validación local de Linux: 35 pruebas aprobadas, Nginx -t no root y configuración idéntica. El contrato del verificador de despliegue usa respuestas Docker/HTTP simuladas en sus regresiones; no acredita un nuevo despliegue real. Los informes E11 se revalidaron; no se ejecutó un nuevo escaneo de base de CVEs.

[E12: corrección y pruebas](evidencias/2026-10-07/SONAR_LOCAL_FIXES_20261007.json). Falta confirmar SonarCloud para el código corregido y aprobar CI completo cuando Actions disponga de cuota. No se desactivó el Quality Gate ni se marcaron hallazgos automáticamente como falsos positivos. PR #3 sigue en borrador y sin integrar.

Se excluye nginx.conf generado de Git y del contexto Docker. Una imagen de prueba regeneró la configuración desde un contexto que ya contenía ese archivo y Nginx -t aprobó como usuario no root. Esta prueba no construye el bundle npm completo. El intento CI 37638738429 sobre a1867e4 terminó sin iniciar sus 28 jobs por la restricción de facturación; SonarCloud todavía no reportó una comprobación para la revisión corregida.


## Seguimiento de SonarCloud — 7 de octubre

SonarCloud completó el check 112858031367 sobre 04633f0: Quality Gate fallido por Security Rating C (requiere A). La corrección anterior no cerró todas las alertas: siguen anotaciones de URL de carga y argumentos del verificador Docker. Se restringen las URL a la configuración de despliegue y rutas explícitas de plantilla, validación, compañía, UUID y filas 2–501; se reconstruyen vectores Docker independientes antes de ejecutar. El workflow incluye las nuevas pruebas de URL.

Validación local Linux: **41/41 pruebas**, sin fallos ni omisiones (21 automatización, 8 SCA y 12 Node); frontend completo con 25 archivos originales verificados por hash, lint sin avisos/errores y build Vite 8.2.2 aprobado (28 módulos). YAML válido. [E13: diagnóstico y seguimiento](evidencias/2026-10-07/SONAR_FOLLOWUP_20261007.json).

Pendiente: confirmación SonarCloud del siguiente commit y CI integral cuando haya cuota. Los sondeos de persistencia son regresiones con mocks; no se repitió el despliegue real ni el correo. La pestaña de autenticación redirigió a Google y su recarga fue bloqueada por revisión automática; los checks de GitHub sí fueron accesibles. PR en borrador, sin integrar.

## Corrección de las diez incidencias de seguridad restantes

El usuario aportó las diez incidencias Security/Medium de 149968d: cinco de pip (wheels/resolución), tres de credenciales PostgreSQL en el job de carga y dos de permisos Ansible. Se sustituyen las tres instalaciones pip por locks transitivos con hashes y wheels obligatorios, las credenciales literales por secretos aleatorios enmascarados y los permisos abiertos por Compose 0600/SQL 0640/directorios 0750 con grupo autorizado PostgreSQL. Checkov 3.2.506 elimina ecdsa/CVE-2024-23342 conservando los dos controles Ansible y su prueba negativa.

Validación local Linux: **95/95 regresiones** (21 automatización, 11 SCA, 12 Node y 51 carga con PostgreSQL real); tres YAML sin claves duplicadas; ambas instalaciones offline y pip check aprobados; hash alterado rechazado. Nueve tareas reales de preparación Ansible, segunda ejecución changed=0 y doce SQL inicializados por PostgreSQL UID 999/grupo 1000; UID 1001 sin lectura. Credencial generada aceptada y credencial incorrecta rechazada por la red aislada. Trivy cubre diez manifiestos, sin HIGH/CRITICAL y con tres MEDIUM registrados. [E14 e informes](evidencias/2026-10-07/SONAR_SECURITY_CI_20261007.json).

El siguiente paso es confirmar SonarCloud sobre el commit publicado y repetir CI integral cuando Actions disponga de cuota. El despliegue completo ed00530 conserva su evidencia histórica; estas pruebas no lo repiten ni validan SMTP real. El Quality Gate no cambió, no se aceptaron incidencias y el PR #3 permanece en borrador, sin integrar.

## Informe de auditoría Excel para ADMIN TI

Se añade Informe de auditoría al menú de ADMIN TI y GET /auditoria/informe.xlsx en Identity. Consulta los eventos persistidos por Audit Service con filtros combinables de fechas UTC inclusivas, evento, servicio, resultado, usuario actor/objetivo y compañía. Excel contiene Auditoria y Resumen; registra actor, filtros y total. El backend exige ADMIN_TI, sesión/credencial/rol y MFA vigentes, sanitiza detalle y escribe texto sin fórmulas. Máximo 31 días/5.000 eventos, con rechazo explícito si se supera el límite; el detalle resumido se marca a partir de 2.000 caracteres. Cada generación se registra por outbox como AUDITORIA_INFORME_GENERADO.

Validación local: **98/98 pruebas** (82 Pytest con PostgreSQL real, incluidas 31 de auditoría, y 16 Node, incluidas cuatro de rutas/fechas del informe). Lint sin errores/avisos y build Vite 8.2.2 aprobado (31 módulos). [Manual](manual/INFORME_AUDITORIA.md) y [E15/82 casos JUnit](evidencias/2026-10-07/AUDITORIA_EXCEL_20261007.json).

La función requiere desplegar Identity y frontend actualizados; las imágenes 1.0.0 publicadas no la incluyen. No se modificó el entorno personal ni se enviaron correos. CI integral y SonarCloud de la revisión nueva quedan pendientes. PR #3 en borrador, sin integrar. La revisión automática de permisos no pudo evaluar la creación opcional de un Excel de ejemplo por límite de uso de la cuenta; esa ejecución Docker no se realizó. Las pruebas aprobadas y el build habían finalizado antes de ese bloqueo.


### Usuario que ejecutó el evento — E16

El informe ahora conserva el ID histórico y añade el nombre y correo actuales del actor. Identifica al ejecutor del evento, no al objetivo ni al ADMIN TI que descarga. Se conserva todo evento aunque falte el actor o su usuario ya no exista; los nombres/correos siguen siendo texto sin fórmulas. La hoja Resumen y los encabezados aclaran que son datos del directorio actual.

86 regresiones PostgreSQL aprobadas (51 carga, 35 auditoría; 4 casos nuevos de actor). Identity local fue reconstruido y activado; una muestra de 10 eventos produjo un Excel en memoria con 12 columnas, 10 actores identificados y ninguna fórmula. Frontend y PostgreSQL conservan sus inicios anteriores. Después de la prueba técnica, el usuario volvió a descargar el Excel, confirmó que quedó correcto y aportó la captura de las columnas de nombre/correo del actor; esa aceptación se registra en E17. Se preservó la imagen anterior para reversión. Evidencia: docs/evidencias/2026-10-07/AUDITORIA_ACTOR_20261007.json. El PR continúa en borrador y no se integra; CI/Sonar y las imágenes publicadas de producción simulada siguen pendientes.
