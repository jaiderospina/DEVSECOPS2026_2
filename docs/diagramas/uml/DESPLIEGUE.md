# Diagrama de Despliegue — IAM Secure

Revisado: 14 de octubre de 2026. Topología efectiva de docker-compose.yml de desarrollo; no representa producción simulada ni IaC.

~~~mermaid
flowchart TB
    B["Navegador: panel 5173 y grilla 5176"]
    HUB["Docker Hub: ocho imágenes 1.0.0 / latest"]
    SMTP["SMTP externo"]
    subgraph HOST["Host con Docker Compose"]
        subgraph NET["Red bridge iam_network"]
            FE["frontend / Nginx: 5173"]
            GRID["permissions-grid / mismo frontend: 5173"]
            ID["identity / FastAPI: 8003"]
            PER["permissions / FastAPI: 8005"]
            PG[("postgres:17 / 5432; healthcheck")]
            SY["sync-worker / sin puerto"]
            AUD["audit-service / FastAPI: 8004"]
            DIS["audit-dispatcher / sin puerto"]
            BOOT["identity-bootstrap / perfil puntual"]
        end
        VOL[("postgres_data: almacenamiento persistente")]
        SQL["postgres-init: migraciones 01 a 12"]
        PG --- VOL
        SQL -->|"Solo volumen nuevo"| PG
        ID --> PG
        PER --> PG
        PER -->|"Sesión /auth/me"| ID
        SY --> PG
        DIS --> PG
        DIS --> AUD
        AUD --> PG
        BOOT --> PG
    end
    B -->|"host 5173"| FE
    B -->|"loopback 5176"| GRID
    B -->|"host 8003"| ID
    B -->|"loopback 8005"| PER
    ID --> SMTP
    BOOT --> SMTP
    HUB -.->|"Publicadas; Compose actual construye localmente"| HOST
~~~

## Mapeos reales

| Servicio | Puerto contenedor | Publicación host |
|---|---|---|
| frontend | 5173 | 5173, todas las interfaces |
| permissions-grid | 5173 | 127.0.0.1:5176 |
| identity | 8003 | 8003, todas las interfaces |
| permissions | 8005 | 127.0.0.1:8005 |
| audit-service | 8004 | 127.0.0.1:8004 |
| postgres | 5432 | 5433, todas las interfaces |
| sync-worker / audit-dispatcher | Ninguno | Ninguna |
| identity-bootstrap | Proceso puntual | Ninguna |

La exposición de desarrollo no equivale a una política de producción. Nginx restringe hosts/CSP, pero Compose no configura TLS. Abrir la grilla desde el panel permite la transferencia de sesión; acceder a la URL no crea autenticación.

## Imágenes y datos

Siete imágenes propias verificadas como no root: Identity, Sync, Audit, Dispatcher, frontend, usuarios y Permissions. Grilla reutiliza frontend; bootstrap reutiliza Identity. PostgreSQL usa imagen oficial y volumen; el servicio usuarios no está en la topología activa.

El runtime Nginx no contiene Node/npm/node_modules. Variables VITE_* son públicas y se fijan al compilar. El CI prueba el proceso frontend y su HTTP; las sondas id -u de backends no sustituyen el despliegue integral.

El healthcheck de PostgreSQL permite iniciar dependientes; no se representa un healthcheck inexistente en cada servicio. Worker/dispatcher tienen init, reintentos y gestión de señales. Auditar logs no requiere exponer secretos.

Un clon en otro PC crea una base independiente; Git no transporta cuentas/volúmenes. Scripts nuevos deben aplicarse explícitamente sobre volúmenes existentes.

[Manual de despliegue](../../despliegue/DESPLIEGUE.md) · [Imágenes/digests](../../despliegue/IMAGENES_Y_DOCKERHUB.md) · [Componentes](COMPONENTES.md).
