# E34 - Laboratorio seguro interactivo activo

14 de octubre de 2026, America/Bogota. Instalación en el PC de Jean Carlos, checkout `C:/Prueba-ProyectoFinal`, código **bdedc774e86e8c7156999beadba5eface9e750a4**. Es una ejecución local posterior a E32; no sustituye los checks CI ni activa contenedores en el equipo de otro integrante al hacer pull.

## Resultado y procedencia

- Proyecto Compose nuevo: **iam-stride-demo-20261014**; volumen nuevo `iam-stride-demo-20261014_secure_lab_data`. No se importaron cuentas, claves ni datos reales.
- Portal [https://localhost:8443](https://localhost:8443); grilla [https://localhost:8444/permissions.html](https://localhost:8444/permissions.html); Identity 8445 y Permissions 8446. Cuatro HTTPS 200 y TLSv1.3; APIs/DB sin publicación directa.
- Nueve servicios no root, filesystem raíz de solo lectura. Seis logins PostgreSQL independientes, sin superusuario/creación de roles/bases/replicación/bypass RLS; cero membresías heredadas.
- Prueba de 30 intentos contra usuario inexistente con XFF falsificado: **24 respuestas 429, cero 5xx**, Retry-After y CORS comprobados. Es una medición de este runtime; E32 conserva su propia cifra 28/30.
- Respaldo inicial cifrado mediante iam_backup, sin dump plano. Esta activación no repite restauración: la restauración/ACL/MFA está acreditada por E32.
- **28 contenedores previos** conservan ID/fecha de arranque, incluidos PostgreSQL y otros proyectos. Se preservaron `.env` y los cuatro conteos agregados del desarrollo. No se eliminó/recreó su volumen.
- ADMIN_TI inicial creado mediante iam_identity, con cambio de contraseña obligatorio. **Primer acceso, cambio de contraseña y enrolamiento MFA humanos pendientes.** No se copió un usuario del entorno habitual.

[Recibo inicial de activación](ACTIVACION_DEMOSTRACION_SEGURA_2026-10-14.json) y [recibo posterior de confianza](CONFIANZA_CA_DEMOSTRACION_2026-10-14.json). El primer recibo observó rechazo de CA desconocida antes de instalarla; sus campos `system_trust_modified=false` describen ese instante. El segundo acredita la acción posterior autorizada por el usuario en `CurrentUser\Root`, nunca `LocalMachine`, y cuatro HTTPS verificados por Windows sin omitir validación.

Huella SHA-256 de la CA: `d369e7b45e2988b56f04117f95d1f2d2379ce33ebf51793d7aa0237c61ec9865`. Solo se importó certificado público. La clave privada de la CA no fue persistida por el generador. El certificado de servidor dura 30 días desde su emisión; custodiar su clave cifrada/contraseña y renovar antes de expirar.

## Acceso y operación en este PC

Usuario inicial: **CamiloCoordiTI@areati.demo**. La contraseña temporal está en la variable `BOOTSTRAP_ADMIN_TI_PASSWORD` de `C:/Prueba-ProyectoFinal/.private/demostracion-20261014/runtime.env`. No se incluye en Git, este recibo, PDF o chat. El material privado del laboratorio y el backup inicial quedan en esa carpeta con ACL del propietario; no copiarla al compañero ni regenerar claves sobre el volumen existente.

Desde PowerShell en este PC puede copiarse únicamente la contraseña temporal al portapapeles, sin imprimir el archivo completo:

```powershell
$linea = Get-Content -LiteralPath 'C:\Prueba-ProyectoFinal\.private\demostracion-20261014\runtime.env' | Where-Object { $_.StartsWith('BOOTSTRAP_ADMIN_TI_PASSWORD=') }
Set-Clipboard -Value $linea.Substring('BOOTSTRAP_ADMIN_TI_PASSWORD='.Length)
```

Abrir el portal, pegar la contraseña, completar cambio obligatorio y enrolar MFA con el autenticador del integrante. No usar la contraseña temporal como contraseña definitiva. Tras copiar/pegar, `Set-Clipboard -Value ''` permite vaciar el portapapeles. La instalación usa SMTP inválido deliberadamente: no acredita correos reales en este perfil.

```powershell
Set-Location C:\Prueba-ProyectoFinal
$env:IAM_LAB_PRIVATE_DIR = 'C:\Prueba-ProyectoFinal\.private\demostracion-20261014'
# Estado; sustituir 'ps' por 'stop' para detener conservando datos o por 'up -d' para iniciar.
docker compose --project-name iam-stride-demo-20261014 --project-directory . --env-file .private/demostracion-20261014/runtime.env -f orquestacion/compose.secure-lab.json ps
```

No usar `down -v` sobre esta instalación conservada ni recrear su configuración. La guía de [instalación independiente](../../../seguridad/STRIDE_HARDENING_LAB.md) permite reproducirla en otro PC con secretos y volumen propios. Instalar una CA distinta requiere revisión/confianza propia; no se distribuye confianza automáticamente mediante Git.

Para retirar la confianza de esta CA en este usuario, sin afectar el almacén de máquina ni otras CA:

```powershell
Remove-Item -LiteralPath 'Cert:\CurrentUser\Root\4705503524DC5A530665334408394E35160F96CD'
```

## Alcance pendiente

El laboratorio queda encendido para demostrar el perfil seguro. El Compose habitual sigue en HTTP/conexión administrativa y conserva sus datos. El tráfico interno Docker no usa mTLS; no hay despliegue productivo/HA, SMTP real nuevo ni custodia externa probada. Los seis riesgos T03/T04/T06/T07/T10/T14 continúan **Open/sin aceptación residual posterior**. Esta activación y la autorización de confianza de la CA no son aceptación de esos riesgos.

Siguiente paso: primer acceso humano, cambio de contraseña/MFA; revisar el perfil y registrar decisión residual del equipo; después capturas/historia funcional y video. [Checkpoint](../../../CHECKPOINT_PRUEBA_PROYECTOFINAL_2026-10-14.md).
