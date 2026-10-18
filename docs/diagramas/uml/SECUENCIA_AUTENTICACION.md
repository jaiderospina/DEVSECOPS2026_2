# Diagrama de Secuencia — Autenticación de Usuario

> **Proyecto académico — Grupo 1 — DEVSECOPS2026_2**  
> **Revisado:** 14 de octubre de 2026

## Propósito

Este diagrama representa el flujo crítico de autenticación actualmente implementado en IAM Secure.

El proceso incluye:

- correo y contraseña;
- validación de estado;
- roles vigentes;
- MFA obligatorio;
- enrolamiento TOTP cuando no existe MFA;
- verificación TOTP cuando MFA ya está activo;
- emisión de sesión y JWT;
- sesión restringida cuando existe cambio obligatorio de contraseña.

## Endpoints principales

~~~text
POST /auth/login
POST /auth/mfa/enrolamiento-obligatorio
POST /auth/mfa/activar-obligatorio
POST /auth/mfa/verificar-login
PUT  /auth/password
~~~

## Diagrama

~~~mermaid
sequenceDiagram
    autonumber

    actor U as Usuario
    participant FE as Frontend
    participant ID as Identity Service
    participant DB as PostgreSQL
    participant MFA as MFA/TOTP
    participant SES as Sesiones/JWT

    U->>FE: Ingresa correo + contraseña
    FE->>ID: POST /auth/login

    ID->>DB: Consultar usuario y credencial
    DB-->>ID: Identidad + estado + credencial

    ID->>ID: Verificar Argon2

    alt Credenciales o estado inválidos
        ID-->>FE: 401/403
        FE-->>U: Acceso rechazado
    else Primer factor válido
        ID->>DB: Consultar roles activos
        DB-->>ID: Roles vigentes

        ID->>DB: Consultar estado MFA
        DB-->>ID: MFA activo / no activo

        ID->>DB: Crear desafío MFA temporal

        alt MFA no configurado
            ID-->>FE: mfa_enrolamiento_requerido = true
            FE->>ID: POST /auth/mfa/enrolamiento-obligatorio
            ID->>MFA: Generar secreto TOTP
            ID->>DB: Guardar secreto cifrado
            ID-->>FE: QR de enrolamiento

            U->>FE: Ingresa primer código TOTP
            FE->>ID: POST /auth/mfa/activar-obligatorio
            ID->>MFA: Validar TOTP

            alt TOTP inválido
                ID->>DB: Incrementar intentos del desafío
                ID-->>FE: 401/423
            else TOTP válido
                ID->>DB: Activar MFA + consumir desafío
                ID->>SES: Emitir sesión + JWT
                SES->>DB: Registrar sesión
                ID-->>FE: access_token + contexto
            end

        else MFA ya activo
            ID-->>FE: mfa_requerido = true
            U->>FE: Ingresa código TOTP
            FE->>ID: POST /auth/mfa/verificar-login
            ID->>MFA: Validar TOTP

            alt TOTP inválido
                ID->>DB: Incrementar intentos del desafío
                ID-->>FE: 401/423
            else TOTP válido
                ID->>DB: Consumir desafío
                ID->>SES: Emitir sesión + JWT
                SES->>DB: Registrar sesión
                ID-->>FE: access_token + contexto
            end
        end

        alt requiere_cambio_password = true
            FE-->>U: Solicitar cambio obligatorio
            U->>FE: Define nueva contraseña
            FE->>ID: PUT /auth/password
            ID->>DB: Actualizar hash Argon2 y expiración
            ID-->>FE: Cambio completado
        else contraseña definitiva vigente
            FE-->>U: Acceso al portal
        end
    end
~~~

## 1. Primer factor

El usuario presenta correo y contraseña en POST /auth/login.

Identity Service valida:

- existencia del usuario;
- estado de la identidad;
- estado de la credencial;
- bloqueo por intentos;
- contraseña;
- expiración de contraseña temporal;
- expiración de contraseña definitiva;
- roles activos.

La contraseña se verifica mediante Argon2.

## 2. MFA obligatorio

Una contraseña correcta no genera directamente una sesión definitiva.

Identity Service crea un desafío MFA temporal.

El desafío:

- es aleatorio;
- tiene expiración;
- es de un solo uso;
- se almacena en PostgreSQL únicamente como hash SHA-256;
- limita intentos.

## 3. Usuario sin MFA activo

Si el usuario todavía no tiene MFA activo:

~~~text
POST /auth/login
   |
   v
desafío MFA
   |
   v
POST /auth/mfa/enrolamiento-obligatorio
   |
   v
QR TOTP
   |
   v
POST /auth/mfa/activar-obligatorio
   |
   v
sesión + JWT
~~~

El secreto TOTP se almacena cifrado.

El QR se entrega como imagen y no se persiste en disco.

## 4. Usuario con MFA activo

Si MFA ya está activo:

~~~text
POST /auth/login
   |
   v
desafío MFA
   |
   v
POST /auth/mfa/verificar-login
   |
   v
validación TOTP
   |
   v
sesión + JWT
~~~

El código TOTP no se almacena ni se registra en auditoría.

## 5. Sesión y JWT

La sesión definitiva se emite solamente después de completar MFA.

El JWT incluye un jti asociado a una fila persistente en sesiones.

Esto permite revocar una sesión antes de la expiración criptográfica del token.

## 6. Cambio obligatorio de contraseña

Cuando la credencial exige cambio obligatorio, la sesión emitida queda restringida.

El usuario puede utilizar el endpoint de cambio de contraseña, pero no acceder a las funciones normales hasta completar el cambio.

El flujo usa:

~~~text
PUT /auth/password
~~~

Después del cambio:

- se genera un nuevo hash Argon2;
- se elimina la condición de contraseña temporal;
- se establece expiración de contraseña definitiva;
- el usuario recupera el contexto normal de acceso.

## 7. Contraseña definitiva expirada

Cuando una contraseña definitiva válida alcanzó su fecha de expiración, Identity Service marca la credencial para cambio obligatorio.

La autenticación puede continuar hasta una sesión restringida para permitir el cambio seguro.

## 8. Roles

Los roles activos se consultan desde PostgreSQL.

Aunque el JWT contiene contexto de rol, las decisiones sensibles no dependen exclusivamente de información almacenada previamente en el token.

## 9. Auditoría

Durante el proceso se generan eventos de seguridad, entre ellos:

- login exitoso;
- login fallido;
- enrolamiento MFA;
- activación MFA;
- MFA login exitoso;
- MFA login fallido;
- cambio/recuperación de contraseña cuando corresponde.

Los eventos se sanitizan antes de persistirse.

## 10. Controles de seguridad representados

~~~text
Argon2
+ estado de identidad
+ estado de credencial
+ bloqueo por intentos
+ expiración de password
+ MFA obligatorio
+ desafío temporal
+ anti-replay TOTP
+ JWT firmado
+ jti
+ sesión persistente
+ RBAC
+ multitenancy
~~~

## 11. Flujos alternativos

| Condición | Resultado |
|---|---|
| Usuario inexistente | Autenticación rechazada |
| Usuario inactivo | Acceso rechazado |
| Credencial inactiva | Acceso rechazado |
| Credencial bloqueada | Acceso rechazado |
| Contraseña incorrecta | Autenticación rechazada |
| Contraseña temporal expirada | Autenticación rechazada |
| Sin rol activo | 403 |
| Desafío MFA expirado | 401 |
| Máximo de intentos MFA | 423 |
| TOTP inválido | 401 |
| Sesión revocada | Token rechazado |
| Cambio de contraseña pendiente | Acceso funcional restringido |

## 12. Relación con otros diagramas

- [Componentes](./COMPONENTES.md)
- [Despliegue](./DESPLIEGUE.md)
- [Casos de Uso](./CASOS_USO.md)
- [Manual de Arquitectura](../../arquitectura/ARQUITECTURA.md)
- [Manual de Seguridad](../../seguridad/SEGURIDAD.md)

## Navegación

[⬅ Volver al Manual de Arquitectura](../../arquitectura/ARQUITECTURA.md)

## Sesión compartida con grilla y vencimiento

Este complemento describe el código de etapa 2. El límite predeterminado es cinco minutos; las pruebas de reloj controlado complementan la confirmación manual del usuario.

~~~mermaid
sequenceDiagram
    actor U as ADMIN_SOPORTE
    participant P as Panel
    participant G as Grilla en otra pestaña
    participant API as Permissions API
    participant IAM as Identity
    participant DB as PostgreSQL
    U->>P: Abrir Grilla de permisos
    G->>P: Solicitar sesión por canal comprobado
    P->>P: Comprobar origen, ventana, nonce y fecha límite
    P-->>G: Token y vencimiento; memoria de pestaña
    G->>API: Consultar compañía y permisos
    API->>IAM: GET /auth/me con token
    IAM->>DB: Validar sesión, roles, estado e inactividad
    IAM-->>API: Contexto vigente o rechazo
    API->>DB: Comprobar compañía asignada y permisos
    API-->>G: Resultado autorizado
    Note over P,G: Sondas automáticas no renuevan actividad humana
    alt Cinco minutos sin actividad o vencimiento tras recuperar foco
        P->>P: Limpiar sesión inmediatamente
        P-->>G: Notificar vencimiento si existe canal
        G->>G: Retirar token, datos y controles por su límite
        P->>IAM: POST /auth/logout; espera acotada
        IAM->>DB: Revocar sesión
        G-->>U: Sesión expirada; volver al panel
    else Actividad admitida con sesión vigente
        P->>P: Actualizar fecha límite de actividad
        P-->>G: Comunicar vencimiento actualizado
    end
~~~

El backend conserva la comprobación autoritativa aun si la pestaña se suspende. No se promete sincronización permanente entre todas las pestañas ni continuidad de una carga después del cierre: al volver, se consulta el lote persistido.

[Prueba de inactividad](../../evidencias/2026-10-06/INACTIVIDAD_CI_624ab1d.json) · [Validación local](../../VALIDACION_CARGA_E_INACTIVIDAD_2026-10-06.md).
