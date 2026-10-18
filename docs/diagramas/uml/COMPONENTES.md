# Diagrama de Componentes — IAM Secure

Revisado: 14 de octubre de 2026. Alcance del código vigente integrado en master mediante PR #3.

~~~mermaid
flowchart LR
    U["Usuario / administrador"] --> FE["React: panel, portal y carga Excel"]
    U --> GW["React: permissions.html, grilla en otra pestaña"]
    NG["Nginx no root: bundle estático, CSP y hosts"] --> FE
    NG --> GW
    FE <-->|"postMessage: origen, ventana, nonce y vencimiento"| GW
    FE -->|"HTTP /auth, /usuarios, /companias"| ID
    GW -->|"HTTP /v1"| P["Permissions API"]
    FE -->|"HTTP /v1/me: permisos y vistas"| P
    P -->|"Consulta online /auth/me"| ID
    subgraph ID["Identity API"]
        AUTH["Autenticación, MFA y sesiones"]
        IAM["Identidades, roles y compañías"]
        XLSX["Parser y lotes Excel"]
        GRANT["Tres vistas iniciales por rol"]
        OUT["Outbox y sync_jobs"]
        XLSX --> IAM
        IAM --> GRANT
        IAM --> OUT
        IAM --> AUTH
    end
    ID --> DB[("PostgreSQL: datos, sesiones, permisos y colas")]
    P --> DB
    ID -->|"Credencial temporal, SMTP"| MAIL["Servidor SMTP externo"]
    DB -->|"sync_jobs"| SY["Sync Worker"]
    SY -->|"Estados / reintentos"| DB
    SY --> EXT["Conector de sincronización simulado"]
    DB -->|"auditoria_outbox"| AD["Audit Dispatcher"]
    AD -->|"HTTP con token interno"| A["Audit Service: sanitización, append-only e idempotencia"]
    A --> DB
~~~

## Responsabilidades y límites

- Identity es la autoridad de autenticación y aprovisionamiento; cargar Excel no agrega otra API/worker.
- Permissions comprueba la sesión en Identity, sin JWT_SECRET ni clave MFA propios, y aplica alcance y versión del permiso en PostgreSQL.
- Frontend y grilla reutilizan el mismo código/imagen; la transferencia de sesión es temporal y en memoria.
- La creación individual y Excel guardan las tres vistas iniciales en la transacción del usuario. Un duplicado/reintento no reactiva una excepción.
- Outbox permite entrega asíncrona de auditoría; SMTP está fuera de la transacción de base y no garantiza entrega exactamente una vez.
- Sync usa un conector simulado; las tarjetas del portal son referencias académicas.
- usuarios tiene imagen propia publicada, pero no se ejecuta en el Compose actual. Los directorios históricos autenticacion/backend tampoco se representan como servicios activos.

Este UML no sustituye DFD/STRIDE de Threat Dragon. [Arquitectura](../../arquitectura/ARQUITECTURA.md) · [Despliegue](DESPLIEGUE.md) · [Casos de uso](CASOS_USO.md) · [Secuencia](SECUENCIA_AUTENTICACION.md).
