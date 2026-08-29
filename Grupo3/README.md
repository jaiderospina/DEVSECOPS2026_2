![OWASP](https://img.shields.io/badge/OWASP-Top%2010%20%3A%202025-000000?style=for-the-badge&logo=owasp&logoColor=white)
![Ciberseguridad](https://img.shields.io/badge/Ciberseguridad-AppSec-blue?style=for-the-badge)
![Uso](https://img.shields.io/badge/Uso-Educativo-success?style=for-the-badge)

# 🛡️ OWASP Top 10 : 2025 — Vulnerabilidades Críticas en Aplicaciones Web

> 📚 **Trabajo académico — Clase de Ciberseguridad**
> Investigación, análisis de explotación y estrategias de mitigación de las 10 vulnerabilidades más críticas en aplicaciones web según la edición **2025** del OWASP Top 10 (publicada oficialmente en enero de 2026 tras el anuncio en el OWASP Global AppSec Conference, Washington D.C., noviembre 2025).
>

---
## 📖 Índice

1. [¿Qué es el OWASP Top 10?](#-qué-es-el-owasp-top-10)
2. [Metodología y cambios respecto a 2021](#-metodología-y-cambios-respecto-a-2021)
3. [Resumen visual del Top 10 : 2025](#-resumen-visual-del-top-10--2025)
4. [A01 — Broken Access Control (Control de Acceso Roto)](#-a01--broken-access-control-control-de-acceso-roto)
5. [A02 — Security Misconfiguration (Configuración de Seguridad Incorrecta)](#-a02--security-misconfiguration-configuración-de-seguridad-incorrecta)
6. [A03 — Software Supply Chain Failures (Fallas en la Cadena de Suministro)](#-a03--software-supply-chain-failures-fallas-en-la-cadena-de-suministro)
7. [A04 — Cryptographic Failures (Fallas Criptográficas)](#-a04--cryptographic-failures-fallas-criptográficas)
8. [A05 — Injection (Inyección)](#-a05--injection-inyección)
9. [A06 — Insecure Design (Diseño Inseguro)](#-a06--insecure-design-diseño-inseguro)
10. [A07 — Authentication Failures (Fallas de Autenticación)](#-a07--authentication-failures-fallas-de-autenticación)
11. [A08 — Software or Data Integrity Failures (Fallas de Integridad)](#-a08--software-or-data-integrity-failures-fallas-de-integridad)
12. [A09 — Security Logging and Alerting Failures (Fallas de Registro y Alertas)](#-a09--security-logging-and-alerting-failures-fallas-de-registro-y-alertas)
13. [A10 — Mishandling of Exceptional Conditions (Mal Manejo de Condiciones Excepcionales)](#-a10--mishandling-of-exceptional-conditions-mal-manejo-de-condiciones-excepcionales)
14. [Tabla comparativa 2021 → 2025](#-tabla-comparativa-2021--2025)
15. [Conclusiones y guía para la exposición](#-conclusiones-y-guía-para-la-exposición)
16. [Fuentes](#-fuentes)

---

## 🔎 ¿Qué es el OWASP Top 10?

**OWASP** (*Open Worldwide Application Security Project*) es una fundación sin fines de lucro dedicada a mejorar la seguridad del software. El **OWASP Top 10** es su documento insignia: un ranking de concientización que identifica las **10 categorías de riesgo más críticas** en aplicaciones web, basado en:

- 📊 Análisis de **más de 175,000 CVEs** reales.
- 🧩 Mapeo de **248 CWEs** (*Common Weakness Enumerations*) distribuidos en las 10 categorías.
- 🗳️ Encuestas a **miles de organizaciones y profesionales de seguridad** de todo el mundo.

> 💡 **¿Para qué sirve?** No es una checklist técnica exhaustiva, sino una **guía de concientización** dirigida a desarrolladores, arquitectos de seguridad y equipos de gestión de riesgos, para priorizar dónde invertir esfuerzo en seguridad.

---

## 🔄 Metodología y cambios respecto a 2021

La edición **2025** (la primera actualización desde 2021) trae cambios importantes:

- 🆕 **2 categorías nuevas**: `A03 — Software Supply Chain Failures` y `A10 — Mishandling of Exceptional Conditions`.
- 🔀 **4 reordenamientos significativos** en el ranking.
- ✏️ **3 renombramientos** para mayor precisión (p. ej. *Identification and Authentication Failures* → *Authentication Failures*).
- 🔗 **SSRF** (*Server-Side Request Forgery*) fue absorbido dentro de `A01 — Broken Access Control`.
- 📈 `Security Misconfiguration` subió del puesto #5 (2021) al **#2** (2025) — la mala configuración es hoy más prevalente que nunca, en gran parte por la complejidad de la nube.

---

## 🎨 Resumen visual del Top 10 : 2025

| # | Categoría | Nivel de riesgo | CWEs asociados | Cambio vs 2021 |
|---|---|---|---|---|
| 🥇 A01 | **Broken Access Control** | ![critico](https://img.shields.io/badge/-CRÍTICO-red) | 40 | Se mantiene en #1, ahora incluye SSRF |
| 🥈 A02 | **Security Misconfiguration** | ![critico](https://img.shields.io/badge/-CRÍTICO-red) | 16 | Sube de #5 → #2 |
| 🥉 A03 | **Software Supply Chain Failures** | ![alto](https://img.shields.io/badge/-ALTO-orange) | 5 | 🆕 Nueva (expande A06:2021) |
| 4 | **Cryptographic Failures** | ![alto](https://img.shields.io/badge/-ALTO-orange) | 32 | Baja de #2 → #4 |
| 5 | **Injection** | ![alto](https://img.shields.io/badge/-ALTO-orange) | 38 | Baja de #3 → #5 |
| 6 | **Insecure Design** | ![medio](https://img.shields.io/badge/-MEDIO-yellow) | — | Baja de #4 → #6 |
| 7 | **Authentication Failures** | ![medio](https://img.shields.io/badge/-MEDIO-yellow) | 36 | Se mantiene en #7, renombrada |
| 8 | **Software or Data Integrity Failures** | ![medio](https://img.shields.io/badge/-MEDIO-yellow) | — | Se mantiene en #8 |
| 9 | **Security Logging and Alerting Failures** | ![medio](https://img.shields.io/badge/-MEDIO-yellow) | 5 | Se mantiene en #9, renombrada |
| 10 | **Mishandling of Exceptional Conditions** | ![bajo](https://img.shields.io/badge/-EMERGENTE-lightgrey) | 24 | 🆕 Nueva categoría |

```mermaid
flowchart LR
    A[🌐 Cliente / Atacante] -->|Petición HTTP| B(🖥️ Aplicación Web)
    B --> C{¿Controles de<br/>seguridad OK?}
    C -->|❌ Falla A01/A02/A05| D[💥 Explotación:<br/>acceso indebido, inyección,<br/>datos expuestos]
    C -->|✅ Correcto| E[🛡️ Petición procesada<br/>de forma segura]
    D --> F[📉 Impacto: robo de datos,<br/>toma de cuentas, RCE]
    style D fill:#ff4d4d,color:#fff
    style F fill:#b30000,color:#fff
    style E fill:#2e7d32,color:#fff
```

---





## 🥇 A01 — Broken Access Control (Control de Acceso Roto)

![Riesgo](https://img.shields.io/badge/Riesgo-CRÍTICO-red?style=flat-square) ![Prevalencia](https://img.shields.io/badge/Incidencia-3.73%25%20de%20apps-orange?style=flat-square)

### 📌 Descripción
El control de acceso aplica la política de que un usuario **no puede actuar fuera de sus permisos previstos**. Cuando falla, un atacante puede ver, modificar o eliminar contenido que no le corresponde, o ejecutar funciones fuera de su rol (por ejemplo, un usuario normal accediendo a funciones de administrador).

**Causas comunes:**
- Falta de verificación de permisos en cada endpoint/función (no solo en el menú/UI).
- **IDOR** (*Insecure Direct Object Reference*): manipular un ID en la URL o petición para acceder a recursos ajenos.
- Configuración CORS permisiva (`Access-Control-Allow-Origin: *` con credenciales).
- **SSRF**: el servidor es engañado para hacer peticiones a recursos internos (ahora integrado en esta categoría).
- Elevación de privilegios manipulando tokens/JWT.

**Impacto potencial:** exposición o alteración masiva de datos, toma de cuentas ajenas, acceso a redes internas (vía SSRF), pérdida de confianza y sanciones regulatorias.

### 💥 Métodos de explotación
- **IDOR**: cambiar `GET /api/facturas/1042` por `1043` y ver la factura de otro cliente.
- **Fuerza bruta de rutas ocultas** con `ffuf` / `gobuster` para encontrar paneles `/admin`, `/backup` sin protección.
- **SSRF** para consultar el servicio de metadatos de la nube (`http://169.254.169.254/`) y robar credenciales temporales.
- **Herramientas**: Burp Suite (Repeater/Intruder), extensión *Autorize* (prueba automatizada de fallos de autorización), OWASP ZAP.
- **Caso real**: la brecha de **Capital One (2019)** — una atacante explotó una mala configuración de firewall (WAF) para ejecutar un ataque **SSRF** contra el servicio de metadatos de AWS EC2, robando credenciales IAM y accediendo a datos de más de 100 millones de clientes.

### 🧪 Ejemplo técnico (del día a día)
```http
GET /api/v1/usuarios/1002/pedidos HTTP/1.1
Host: tienda.com
Authorization: Bearer <token-del-usuario-1001>
```
El backend nunca valida que el `1002` de la URL coincida con el dueño del token → el usuario 1001 puede leer/editar los pedidos del usuario 1002 con solo cambiar un número.

### 🎈 Ejemplo sencillo para exponer en clase
Imagina un **hotel donde la llave de tu habitación abre TODAS las habitaciones**, no solo la tuya. Nadie lo nota hasta que un huésped "curioso" prueba su llave en la puerta de al lado... y entra. Eso es exactamente lo que pasa cuando una app olvida verificar "¿este dato es realmente tuyo?".

### 🛡️ Prevención y mitigación
- ✅ **Denegar por defecto**: acceso explícitamente permitido, todo lo demás se rechaza.
- ✅ Validar permisos **en el servidor**, en cada petición — nunca confiar en la UI o el frontend.
- ✅ Usar un mecanismo **centralizado** de control de acceso (middleware/librería), no lógica dispersa.
- ✅ Aplicar el **principio de mínimo privilegio** por rol/recurso.
- ✅ Deshabilitar listados de directorios y metadatos de servidor.
- ✅ Mitigar SSRF con listas blancas de destinos y segmentación de red.
- ✅ Registrar y alertar fallos de control de acceso repetidos (posible ataque en curso).

---

## 🥈 A02 — Security Misconfiguration (Configuración de Seguridad Incorrecta)

![Riesgo](https://img.shields.io/badge/Riesgo-CRÍTICO-red?style=flat-square) ![Tendencia](https://img.shields.io/badge/Tendencia-⬆️%20de%20%235%20a%20%232-red?style=flat-square)

### 📌 Descripción
Ocurre cuando la aplicación, el servidor, el framework o la infraestructura en la nube se despliegan con configuraciones **inseguras, por defecto o incompletas**. Es la categoría que **más subió** en 2025, impulsada por la complejidad de entornos cloud/multi-servicio.

**Causas comunes:** credenciales/paneles por defecto sin cambiar, mensajes de error detallados en producción, funciones/puertos innecesarios habilitados, buckets de almacenamiento (S3, GCS) públicos, cabeceras de seguridad ausentes, permisos de nube excesivos (IAM demasiado permisivo).

**Impacto potencial:** compromiso total del sistema, filtración masiva de datos, acceso administrativo no autorizado.

### 💥 Métodos de explotación
- **Reconocimiento con Shodan/Censys** para hallar servicios expuestos a internet (bases de datos, dashboards, cámaras).
- **Dorking / fuzzing de directorios** (`gobuster`, `dirb`) para encontrar `.env`, `.git/`, `config.php.bak`.
- **Herramientas de auditoría cloud**: ScoutSuite, Prowler, para detectar buckets S3 públicos o IAM mal configurado.
- **Caso real**: decenas de filtraciones masivas por **buckets S3 públicos mal configurados** (empresas como Verizon, Accenture, Dow Jones han sufrido incidentes de este tipo, exponiendo millones de registros sin que fuera necesario "hackear" nada — el dato simplemente estaba abierto al público).

### 🧪 Ejemplo técnico (del día a día)
Un backend Django/Flask desplegado a producción con `DEBUG = True`: cualquier error muestra el **stack trace completo**, incluyendo rutas del servidor, variables de entorno y hasta la `SECRET_KEY`, visible para cualquier visitante que provoque un error 500.

### 🎈 Ejemplo sencillo para exponer en clase
Es como una **tienda que olvida cambiar la clave de la alarma** después de instalarla y sigue usando `0000`, o deja la puerta trasera sin candado "solo por hoy". Nadie forzó nada: la puerta ya estaba abierta.

### 🛡️ Prevención y mitigación
- ✅ Proceso de despliegue **repetible y automatizado** (Infraestructura como Código) para evitar configuraciones manuales inconsistentes.
- ✅ Plataforma mínima: eliminar features, puertos, servicios y cuentas que no se usan.
- ✅ Revisar y actualizar configuraciones de forma periódica (benchmarks CIS).
- ✅ Cabeceras de seguridad: `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`.
- ✅ Escaneo automatizado de configuración en el pipeline CI/CD.
- ✅ Nunca dejar credenciales/paneles por defecto.

---

## 🥉 A03 — Software Supply Chain Failures (Fallas en la Cadena de Suministro)

![Riesgo](https://img.shields.io/badge/Riesgo-ALTO-orange?style=flat-square) ![Nuevo](https://img.shields.io/badge/2025-🆕%20NUEVA%20CATEGORÍA-blueviolet?style=flat-square)

### 📌 Descripción
Es la categoría **con mayor incidencia promedio (5.19%)** en los datos de 2025 y la más votada como #1 en la encuesta a la comunidad. Expande a la antigua *"Vulnerable and Outdated Components"* (A06:2021): ya no se trata solo de usar una librería con una vulnerabilidad conocida, sino de **cualquier compromiso en el proceso de construir, distribuir o actualizar software** — dependencias, pipelines de CI/CD, registries de paquetes, proveedores externos.

**Causas comunes:** dependencias sin actualizar o abandonadas, paquetes descargados de fuentes no verificadas, ausencia de firma/verificación de integridad, pipelines de build sin control de acceso.

**Impacto potencial:** compromiso masivo y silencioso de miles de organizaciones a la vez (efecto dominó), backdoors persistentes, robo de secretos en CI/CD.

### 💥 Métodos de explotación
- **Typosquatting**: publicar un paquete malicioso con nombre parecido a uno legítimo (`reqeusts` en vez de `requests`) esperando que un desarrollador se equivoque al escribir `pip install`.
- **Compromiso de dependencias populares** inyectando código malicioso en una actualización legítima.
- **Herramientas del atacante**: scripts automatizados de exfiltración en *post-install hooks* de npm/pip.
- **Casos reales**:
  - 🔴 **XZ Utils (2024, CVE-2024-3094)**: un mantenedor "de confianza" (en realidad un actor malicioso tras años de ingeniería social) insertó una puerta trasera en una librería de compresión usada por millones de servidores Linux vía OpenSSH.
  - 🔴 **SolarWinds Orion (2020)**: atacantes comprometieron el pipeline de build e insertaron código malicioso (Sunburst) distribuido a ~18,000 clientes, incluyendo agencias gubernamentales de EE. UU.

### 🧪 Ejemplo técnico (del día a día)
Un pipeline de CI/CD ejecuta `npm install` sin lockfile ni verificación de checksums; una dependencia transitiva es secuestrada y su script `postinstall` exfiltra las variables de entorno (tokens, claves de API) del entorno de build.

### 🎈 Ejemplo sencillo para exponer en clase
Es como comprar un **producto "de marca" a un vendedor ambulante** en la calle: el empaque se ve idéntico al original, pero nadie garantiza qué hay realmente adentro. Confiaste en la etiqueta, no en la fuente.

### 🛡️ Prevención y mitigación
- ✅ **SBOM** (*Software Bill of Materials*) para tener visibilidad completa de cada componente usado.
- ✅ Herramientas de **SCA** (*Software Composition Analysis*): Dependabot, Snyk, OWASP Dependency-Check.
- ✅ Usar **lockfiles** y fijar versiones específicas; actualizar de forma deliberada, no automática.
- ✅ Descargar componentes solo de **fuentes oficiales**, preferir paquetes **firmados** (Sigstore/cosign).
- ✅ Monitorear CVEs de las dependencias usadas (NVD, OSV).
- ✅ Aislar y proteger el entorno de build/CI-CD con control de acceso estricto.

---

## A04 — Cryptographic Failures (Fallas Criptográficas)

![Riesgo](https://img.shields.io/badge/Riesgo-ALTO-orange?style=flat-square)

### 📌 Descripción
Antes llamada *"Sensitive Data Exposure"*, el nombre actual pone el foco en la **causa raíz**: uso ausente, débil o incorrecto de criptografía, que termina exponiendo datos sensibles (contraseñas, tarjetas, datos personales, salud).

**Causas comunes:** transmitir datos sensibles en texto plano (HTTP en vez de HTTPS), algoritmos obsoletos (MD5, SHA-1, DES), claves hardcodeadas en el código, certificados TLS mal validados, contraseñas sin *salt* o con hash débil.

**Impacto potencial:** robo masivo de credenciales y datos personales, incumplimiento de normativas (PCI-DSS, GDPR/LFPDPPP), secuestro de sesiones.

### 💥 Métodos de explotación
- **Sniffing de tráfico** en redes no cifradas con **Wireshark**.
- **Cracking de hashes débiles** con `hashcat` o `John the Ripper` cuando se filtra una base de datos con MD5 sin sal.
- **Auditoría de TLS** con `testssl.sh` / `sslyze` para detectar cifrados obsoletos.
- **Caso real**: la brecha de **Adobe (2013)** expuso ~153 millones de cuentas; las contraseñas estaban cifradas (no *hasheadas*) con **3DES en modo ECB**, que preserva patrones — permitiendo a los atacantes agrupar contraseñas idénticas y descifrar en masa sin fuerza bruta completa.

### 🧪 Ejemplo técnico (del día a día)
```python
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()  # ❌ sin sal, algoritmo roto
```
Frente a la forma correcta:
```python
from argon2 import PasswordHasher
ph = PasswordHasher()
password_hash = ph.hash(password)  # ✅ Argon2, con sal automática
```

### 🎈 Ejemplo sencillo para exponer en clase
Es como escribir tu diario secreto usando el **"cifrado César"** que aprendiste en primaria (correr cada letra una posición): a simple vista parece un código, pero cualquiera lo descifra en segundos. La "protección" es solo apariencia.

### 🛡️ Prevención y mitigación
- ✅ Cifrar **en tránsito** (TLS 1.2+/1.3 obligatorio, HSTS) y **en reposo** (AES-256).
- ✅ Usar algoritmos de hash para contraseñas diseñados para eso: **bcrypt, Argon2, scrypt** (nunca MD5/SHA1 solos).
- ✅ Gestión adecuada de llaves (KMS/HSM), nunca hardcodeadas en el repositorio.
- ✅ No almacenar datos sensibles que no sean estrictamente necesarios (minimización de datos).
- ✅ Deshabilitar cifrados y protocolos obsoletos en el servidor.

