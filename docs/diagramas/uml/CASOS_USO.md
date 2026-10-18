# Diagrama de Casos de Uso — IAM Secure

Revisado: 14 de octubre de 2026. Roles, flujo Excel y permisos del código integrado en master.

~~~mermaid
flowchart LR
    TI["ADMIN_TI"]
    AS["ADMIN_SOPORTE"]
    L["Líder funcional"]
    U["Todos los usuarios"]
    subgraph SYS["IAM Secure"]
        LOGIN(["Autenticarse con contraseña y MFA"])
        PW(["Cambiar / recuperar contraseña"])
        SES(["Consultar / cerrar sesiones propias"])
        SUPPORT(["Administrar soportes y su acceso/MFA"])
        COMPANY(["Administrar compañías y asignaciones"])
        LEADER(["Administrar líderes del alcance"])
        BULK(["Validar, confirmar e importar XLSX"])
        RESULT(["Consultar lote y exportar resultados"])
        GRID(["Gestionar excepciones de vistas"])
        VIEWS(["Consultar / abrir vistas autorizadas"])
    end
    U --> LOGIN
    U --> PW
    U --> SES
    TI --> SUPPORT
    TI --> COMPANY
    AS --> LEADER
    AS --> BULK
    AS --> RESULT
    AS --> GRID
    L --> VIEWS
    BULK -.->|"Reutiliza creación de líderes"| LEADER
    GRID -.->|"Determina opciones visibles"| VIEWS
~~~

## Actores y autorización

| Actor | Alcance |
|---|---|
| ADMIN_TI | Soportes, compañías y asignaciones; acciones administrativas sobre soportes autorizados |
| ADMIN_SOPORTE | Líderes de compañías activas asignadas; creación/estado/rol/acceso/MFA, Excel y grilla |
| LIDER_FACTURACION | Tres vistas de Facturación según concesiones |
| LIDER_LOGISTICA | Tres vistas de Logística según concesiones |
| LIDER_GESTION_HUMANA | Tres vistas de Gestión Humana según concesiones |

La API del panel /auth/usuarios/{id}/mfa/restablecer permite ADMIN_TI sobre soportes y ADMIN_SOPORTE sobre líderes del alcance. El endpoint histórico en /usuarios está limitado a soporte. Se describe implementación, sin inventar una prueba manual adicional de ADMIN_TI.

Crear un líder habilita las tres vistas del rol en su compañía. La grilla gestiona excepciones; permisos faltantes o deshabilitados se deniegan. Las vistas son referencias académicas, no operaciones de negocio.

## Historia distinta de autenticación

Como ADMIN_SOPORTE quiero importar líderes de una compañía asignada y ajustar una excepción de vistas.

1. Descargar/completar plantilla; validar sin crear cuentas.
2. Autorizar importación y envío; crear las filas válidas.
3. Consultar resultado y exportar Excel.
4. Confirmar acceso del nuevo líder y opciones iniciales.
5. Deshabilitar una excepción desde la grilla; actualizar opciones del líder.
6. Revalidar el archivo: duplicado inválido sin modificar cuenta ni permisos.
7. Verificar cierre por cinco minutos de inactividad.

[Manual con capturas y aceptación](../../usuario/MANUAL_USUARIO.md). Recorrido probado en el PC para una cuenta; varias filas/correos y presentación final siguen pendientes. Pruebas negativas de API y correo simulado en CI no equivalen a una demostración manual de todas las variantes.

[PlantUML equivalente](CASOS_USO.puml) · [Componentes](COMPONENTES.md) · [Despliegue](DESPLIEGUE.md) · [Secuencia](SECUENCIA_AUTENTICACION.md).
