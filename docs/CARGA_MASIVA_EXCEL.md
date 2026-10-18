# Etapa 2: carga masiva de usuarios desde Excel

Complemento de la etapa 1 de permisos; no sustituye los checkpoints anteriores.

**Política vigente:** las tres vistas del área se habilitan al crear cada líder. El párrafo de permisos denegados y su evidencia CI registran la primera versión; consultar el complemento al final de este documento.

## Uso previsto

Desde IAM en http://localhost:5173/, ADMIN_SOPORTE abre **Carga masiva**. Selecciona una compañía activa asignada, descarga **plantilla-usuarios.xlsx**, completa la hoja **Usuarios**, sube el archivo y pulsa **Validar Excel**. La pantalla muestra errores y duplicados por fila; todavía no crea cuentas ni envía correos. Después de revisar, marca la autorización de creación y envío de credenciales y pulsa **Importar filas válidas**.

| Columna | Regla |
| --- | --- |
| id_externo | Texto de 1 a 50 caracteres; conservar ceros iniciales como texto |
| nombre | Texto de 1 a 100 caracteres |
| email | Correo válido, máximo 150 caracteres, perteneciente al nuevo usuario |
| rol | LIDER_FACTURACION, LIDER_LOGISTICA o LIDER_GESTION_HUMANA |

Una compañía por lote, máximo 500 filas de datos y 2 MiB. Solo .xlsx; no fórmulas, macros, vínculos externos, contraseñas o columnas adicionales. Las identificaciones/correos repetidos quedan inválidos; las cuentas existentes no se modifican.

Cada fila válida utiliza el aprovisionamiento actual: contraseña temporal aleatoria, hash Argon2, cambio obligatorio, asignación de rol y compañía, sync_job y envío por SMTP. El nuevo usuario debe configurar su propio MFA. **La política vigente habilita las tres vistas del rol al crear cada líder.** ADMIN_SOPORTE ajusta excepciones desde la grilla de la etapa 1 (http://localhost:5176/permissions.html, abierta desde el panel).

## Arquitectura y persistencia

Identity conserva la creación de usuarios en su API existente (8003). Permissions (8005) continúa siendo la autoridad de permisos de vistas. La carga masiva no necesita otro puerto ni otro worker.

- GET /usuarios/cargas/plantilla: plantilla Excel.
- POST /usuarios/cargas/validar: multipart con compania_id y archivo; guarda vista previa.
- GET /usuarios/cargas?compania_id=...: hasta diez lotes propios recientes.
- GET /usuarios/cargas/{uuid}: vista previa/progreso.
- POST /usuarios/cargas/{uuid}/confirmar: confirmar=true explícito.
- POST /usuarios/cargas/{uuid}/filas/{fila}: procesa una fila.
- GET /usuarios/cargas/{uuid}/resultado: resultados Excel con celdas de texto.

Cada solicitud exige sesión vigente, contraseña definitiva, MFA activo, rol exacto ADMIN_SOPORTE y alcance de compañía comprobados en PostgreSQL. Los lotes solo son accesibles por el soporte que los creó. Ningún dato del Excel concede roles administrativos o altera la compañía seleccionada.

El estado de la fila se confirma en la misma transacción que la identidad, sus relaciones, credencial, cola de sincronización y evento de auditoría. El bloqueo de fila impide recrear la cuenta cuando se reintenta o concurren solicitudes. Los resultados no incluyen secretos ni excepciones originales.

Los lotes validados deben confirmarse en 30 minutos. El historial queda accesible durante siete días; su eliminación física es **oportunista en la próxima validación**, no una tarea programada. Límite de diez validaciones por soporte cada diez minutos. El archivo original no se conserva; sí se conservan sus datos normalizados por fila mientras el lote existe.

## Pausa, errores y correo

El navegador procesa las filas secuencialmente y permite pausar. Una solicitud ya enviada puede terminar aunque se cierre o pause la página; abrir el lote consulta el resultado persistido. Al iniciar otra sesión, ADMIN_SOPORTE puede retomar las filas pendientes desde **Lotes recientes**. La política de inactividad del panel sigue vigente; no se mantiene la sesión viva artificialmente.

Los errores de fila no detienen las demás filas. Las filas ERROR no se reintentan automáticamente: revisar configuración/datos y validar nuevamente un Excel con las cuentas todavía no creadas. Si el servidor confirmó una fila pero se perdió la respuesta, retomar el mismo lote evita duplicarla.

Se exige configuración SMTP antes de confirmar. Esto no demuestra que el correo pueda entregarse. Si el envío produce una excepción, se revierte la creación de esa fila. Como en la creación individual existente, SMTP ocurre antes del COMMIT y **no es transaccional**: un fallo de base de datos posterior al envío puede dejar un correo correspondiente a una cuenta no confirmada. No se promete entrega de correo exactamente una vez.

## Activación local en C:\Prueba-ProyectoFinal

Aplicar sobre la rama de esta etapa tras revisar su estado; no ejecutar bootstrap ni borrar volúmenes.

```powershell
Set-Location -LiteralPath 'C:\Prueba-ProyectoFinal'
git status --short --branch
git fetch origin
git switch feat/bulk-users-excel-20261005
git pull --ff-only origin feat/bulk-users-excel-20261005

Get-Content -LiteralPath .\postgres-init\12-create-cargas-usuarios.sql -Raw -Encoding utf8 |
    docker compose exec -T postgres psql -U postgres -d iam_secure -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw 'No se aplicó la migración de carga masiva.' }

docker compose up -d --build --no-deps identity frontend
docker compose ps
curl.exe -s -o NUL -w "Frontend: %{http_code}\n" http://localhost:5173/
curl.exe -s -o NUL -w "Identity: %{http_code}\n" http://localhost:8003/
```

La migración 12 solo agrega tablas de lotes. Volúmenes existentes no ejecutan automáticamente nuevos scripts de postgres-init. No imprimir .env, claves, contraseñas, tokens o QR MFA. Configurar SMTP por el canal local privado que ya usa el proyecto.

## Evidencia y pendientes

Implementación en rama feat/bulk-users-excel-20261005. Las pruebas nuevas ejercitan PostgreSQL real, JWT/sesión, alcance, confirmación, idempotencia, concurrencia, rollback de fila y parser XLSX. El correo se simula: CI no envía correos reales ni prueba login/TOTP de las nuevas cuentas. La verificación Chromium usa contratos API simulados.

**Evidencia automatizada:** commit de código `9e5a360d13541e402565f30fb12a4f91278b738d`, [DevSecOps #37413477933](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37413477933): **27/27 jobs exitosos**, **140 pruebas Pytest** (44 nuevas de carga masiva, 32 de permisos y 64 existentes) y **6 comprobaciones Chromium** con contratos simulados. Gitleaks, Semgrep, Bandit, SCA, Docker build y Trivy conservaron sus gates. [Registro por job](evidencia-carga-masiva-ci.json).

**Aceptación local actualizada:** el usuario confirmó migración, importación de una cuenta, acceso/MFA/portal, excepción desde la grilla, duplicado/exportación e inactividad. [Registro](VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md) y [capturas incorporadas](usuario/capturas/README.md). No se acredita despliegue nuevo en otro PC.

## Complemento vigente — vistas habilitadas al crear líderes (5 de octubre de 2026)

El usuario solicitó evitar habilitar cuentas una por una. Este complemento actualiza la política inicial de esta etapa, que dejaba las nuevas vistas denegadas. **Desde este ajuste, las tres opciones del área del líder se crean habilitadas**, tanto por Excel como por creación individual.

| Rol | Opciones iniciales habilitadas |
| --- | --- |
| LIDER_FACTURACION | Facturas pendientes por aprobación; Facturas pendientes por pagar; Declaración de impuestos |
| LIDER_LOGISTICA | Despachos; Entregas; Inventario y movimientos |
| LIDER_GESTION_HUMANA | Colaboradores; Novedades de personal; Vacaciones y permisos |

ADMIN_SOPORTE usa la grilla para deshabilitar o volver a habilitar casos puntuales. La asignación se limita a la compañía del nuevo usuario y a los tres códigos de su rol; no concede vistas de otras áreas. Los permisos iniciales se guardan en la misma transacción que la cuenta y se revierten si falla su creación. El evento USUARIO_CREADO incluye los códigos iniciales habilitados.

Solo se ejecuta durante la creación. Un reintento de lote o un archivo con una cuenta existente no reactiva permisos que soporte haya deshabilitado. Las cuentas existentes conservan su configuración; no hay un script que reactive todas las cuentas. Las consultas de Permissions siguen denegando códigos ausentes o deshabilitados. No cambia el flujo de contraseña temporal ni MFA.

**Activación del ajuste:** actualizar la misma rama y reconstruir Identity/frontend. Este cambio reutiliza la tabla de permisos de la migración 11; no agrega otra migración. Para una instalación que aún no ha activado la carga masiva, seguir aplicando primero la migración 12 indicada arriba.

**Evidencia del ajuste:** código `0b3ad04b2626d04724feb7b26f1258c90e52bdba`, [DevSecOps #37414395017](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37414395017), **27/27 jobs exitosos, 147 pruebas Pytest (51 de carga masiva) y 6 comprobaciones Chromium con contratos simulados**. [Registro por job](evidencia-vistas-iniciales-ci.json). Incluye las tres áreas, creación individual, catálogo de Permissions, rollback de vistas ante error SMTP y preservación de excepciones en reintentos/duplicados.

La evidencia de 140 pruebas registrada anteriormente se conserva como historial de la política inicial. **Pendientes actuales:** varias filas con correos funcionales, pausadas por petición del usuario, y demostración final. La aceptación de una cuenta y de grilla/inactividad ya fue confirmada por el usuario; se conserva separada de la evidencia CI simulada.
