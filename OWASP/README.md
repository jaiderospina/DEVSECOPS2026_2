## ¿Qué es el proyecto OWASP?

**OWASP** significa **Open Worldwide Application Security Project**. Es una fundación y comunidad internacional sin ánimo de lucro dedicada a **mejorar la seguridad del software y las aplicaciones**.

Su filosofía principal es ofrecer conocimientos, estándares, metodologías y herramientas **abiertas y accesibles** para que desarrolladores, arquitectos, equipos DevOps y profesionales de ciberseguridad puedan construir y evaluar software más seguro. OWASP mantiene cientos de proyectos relacionados con seguridad de aplicaciones. ([OWASP Foundation][1])

Podemos entender su propósito así:

> **OWASP ayuda a responder qué vulnerabilidades existen, cómo prevenirlas, cómo detectarlas y cómo incorporar la seguridad durante todo el ciclo de vida del software.**

---

# 1. Principales aportes de OWASP

## 🔴 A. OWASP Top 10

Es probablemente el aporte más conocido de OWASP.

El **OWASP Top 10** identifica y divulga los riesgos más importantes relacionados con la seguridad de aplicaciones web. Su objetivo principal es crear conciencia y proporcionar una referencia inicial para desarrolladores y organizaciones.

El proyecto se ha convertido en uno de los referentes mundiales de **Application Security (AppSec)**. ([OWASP Foundation][1])

Por ejemplo, la edición 2021 incluía riesgos como:

* Broken Access Control.
* Cryptographic Failures.
* Injection.
* Insecure Design.
* Security Misconfiguration.
* Vulnerable and Outdated Components.
* Identification and Authentication Failures.
* Software and Data Integrity Failures.
* Security Logging and Monitoring Failures.
* Server-Side Request Forgery (SSRF).

OWASP ha publicado una edición **Top 10:2025**, que reemplaza la edición de 2021. ([GitHub][2])

### Ejemplo

Una aplicación permite que un usuario consulte:

```text
https://empresa.com/documento?id=100
```

Si el usuario cambia el identificador:

```text
https://empresa.com/documento?id=101
```

y puede acceder a información de otro usuario sin autorización, estamos ante un problema de **Broken Access Control**.

---

# 2. OWASP ASVS

El **Application Security Verification Standard (ASVS)** es uno de los aportes más importantes desde una perspectiva de arquitectura y desarrollo seguro.

Mientras el **OWASP Top 10** nos dice principalmente:

> «¿Cuáles son los riesgos importantes?»

El **ASVS** ayuda a responder:

> «¿Qué controles específicos debo implementar y verificar?»

ASVS proporciona requisitos de seguridad para diseñar, desarrollar y probar aplicaciones y servicios web modernos. ([OWASP Foundation][1])

Es especialmente útil para:

* Arquitectos de software.
* Equipos de desarrollo.
* Auditorías de seguridad.
* Revisiones de código.
* Pruebas de penetración.
* Definición de requisitos de seguridad.
* DevSecOps.

### Ejemplo conceptual

En lugar de decir simplemente:

> "La aplicación debe tener autenticación segura".

ASVS permite establecer requisitos verificables relacionados con:

* Gestión de sesiones.
* Contraseñas.
* Autenticación multifactor.
* Control de acceso.
* Protección criptográfica.
* Validación de entradas.
* Registro y monitoreo.

---

# 3. OWASP SAMM

**SAMM significa Software Assurance Maturity Model.**

Es un modelo para evaluar la **madurez de seguridad del proceso de desarrollo de software**.

Es especialmente útil para responder preguntas como:

> ¿Qué tan madura es nuestra organización en seguridad del software?

> ¿Cómo evolucionamos desde un desarrollo tradicional hacia un modelo DevSecOps?

SAMM permite evaluar y mejorar progresivamente la postura de seguridad de una organización. ([OWASP Foundation][1])

Una organización puede comenzar con:

```text
Nivel inicial
     ↓
Controles básicos
     ↓
Pruebas de seguridad
     ↓
Automatización
     ↓
DevSecOps
     ↓
Mejora continua
```

---

# 4. OWASP Web Security Testing Guide (WSTG)

La **WSTG** es una guía para realizar pruebas de seguridad en aplicaciones web.

Es muy útil para estructurar actividades como:

* Pentesting.
* Security Assessment.
* Vulnerability Assessment.
* Revisión de aplicaciones.

Incluye metodologías para probar aspectos como:

* Configuración.
* Autenticación.
* Gestión de sesiones.
* Autorización.
* Validación de entradas.
* Criptografía.
* Lógica de negocio.
* APIs.

OWASP considera la WSTG uno de sus recursos principales para la evaluación de seguridad de aplicaciones. ([OWASP Foundation][1])

---

# 5. Principales herramientas OWASP

## 🟢 OWASP ZAP — Zed Attack Proxy

Es una de las herramientas más conocidas de OWASP.

Se utiliza para analizar la seguridad de aplicaciones web.

Su funcionamiento básico puede representarse así:

```text
Usuario / Tester
       │
       ▼
   OWASP ZAP
       │
       ▼
Aplicación Web
```

ZAP puede actuar como un **proxy de interceptación**, permitiendo observar y analizar las comunicaciones HTTP/HTTPS.

Entre sus usos se encuentran:

* Análisis automatizado.
* Detección de vulnerabilidades.
* Pruebas de aplicaciones web.
* Integración en pipelines DevSecOps.
* Automatización de pruebas DAST.

---

## 🟢 OWASP Dependency-Check

Esta herramienta analiza las dependencias de un proyecto para identificar componentes con vulnerabilidades conocidas.

Por ejemplo:

```text
Aplicación
    │
    ├── Spring Library
    ├── Log4j
    ├── Apache Commons
    └── Otras dependencias
             │
             ▼
    OWASP Dependency-Check
             │
             ▼
 Identificación de CVE conocidas
```

Es una herramienta de **Software Composition Analysis (SCA)**.

Puede utilizarse desde:

* Línea de comandos.
* Maven.
* Gradle.
* Jenkins.
* Ant.

Su objetivo es identificar dependencias y verificar si existen vulnerabilidades conocidas asociadas a ellas. ([OWASP Developer Guide][3])

Esto es fundamental dentro de DevSecOps porque muchas vulnerabilidades modernas provienen de:

> **Componentes de terceros y dependencias vulnerables.**

---

## 🟢 OWASP Dependency-Track

Complementa la gestión de riesgos relacionados con componentes de software y la cadena de suministro.

Ayuda a organizaciones a:

* Identificar componentes.
* Analizar dependencias.
* Gestionar vulnerabilidades.
* Evaluar riesgos de la cadena de suministro.

Es especialmente relevante en arquitecturas modernas basadas en:

* Microservicios.
* Contenedores.
* Open Source.
* CI/CD.
* Cloud Computing.

([OWASP Foundation][1])

---

## 🟢 CycloneDX

CycloneDX es un estándar para crear un **SBOM — Software Bill of Materials**.

Un SBOM puede entenderse como:

> La lista detallada de componentes que conforman una aplicación.

Ejemplo:

```text
Sistema Bancario
│
├── Java 21
├── Spring Boot
├── PostgreSQL Driver
├── Log4j
├── Jackson
└── Librerías adicionales
```

Esto permite responder rápidamente:

> ¿Nuestra aplicación utiliza una biblioteca vulnerable?

CycloneDX está orientado a reducir riesgos en la **cadena de suministro de software**. ([OWASP Foundation][1])

---

# 6. OWASP Juice Shop

Es una aplicación deliberadamente vulnerable diseñada para:

* Entrenamiento.
* Laboratorios.
* CTF.
* Pruebas de herramientas.
* Formación en seguridad.

Permite practicar vulnerabilidades en un entorno controlado, siendo especialmente útil para cursos de:

* Ethical Hacking.
* Pentesting.
* DevSecOps.
* Seguridad de aplicaciones web.

OWASP la describe como una aplicación vulnerable moderna para entrenamiento y pruebas de herramientas y pipelines de seguridad. ([OWASP Foundation][1])

---

# 7. OWASP WebGoat

WebGoat es otra aplicación vulnerable diseñada para aprendizaje.

Su enfoque es pedagógico:

```text
Concepto
   ↓
Vulnerabilidad
   ↓
Ejercicio
   ↓
Ataque controlado
   ↓
Explicación
   ↓
Mitigación
```

Es muy útil para comprender de manera práctica problemas como:

* SQL Injection.
* XSS.
* Broken Authentication.
* Broken Access Control.
* CSRF.

---

# 8. OWASP Amass

OWASP Amass está orientado al **descubrimiento de activos y análisis de superficie de ataque**.

Puede utilizarse para identificar información como:

```text
Organización
     │
     ├── dominios
     ├── subdominios
     ├── infraestructura expuesta
     └── relaciones entre activos
```

OWASP lo describe como un framework open source para el descubrimiento de activos externos y el mapeo de superficies de ataque mediante técnicas de reconocimiento y fuentes abiertas. ([OWASP Foundation][1])

---

# 9. OWASP Threat Dragon

Es una herramienta para realizar **Threat Modeling**.

Permite analizar una arquitectura antes de que la aplicación sea desplegada.

Ejemplo:

```text
Usuario
   │
   ▼
Aplicación Web
   │
   ▼
API
   │
   ▼
Base de Datos
```

Sobre esta arquitectura podemos preguntarnos:

* ¿Dónde están los activos críticos?
* ¿Qué componentes están expuestos?
* ¿Qué amenazas existen?
* ¿Dónde puede ocurrir una escalación de privilegios?
* ¿Dónde pueden producirse ataques de spoofing?

Esto permite incorporar la seguridad desde las fases tempranas del desarrollo.

---

# 10. OWASP Cheat Sheet Series

Son guías prácticas y resumidas para desarrolladores y profesionales de seguridad.

Por ejemplo, existen recomendaciones relacionadas con:

* Authentication.
* Password Storage.
* SQL Injection Prevention.
* XSS Prevention.
* Logging.
* Session Management.
* Cryptographic Storage.

Es un recurso muy útil para convertir conceptos de seguridad en **prácticas concretas de desarrollo**. ([OWASP Foundation][1])

---

# 11. OWASP CRS — Core Rule Set

El **OWASP Core Rule Set** proporciona reglas para detectar ataques contra aplicaciones web.

Puede utilizarse con tecnologías compatibles con **ModSecurity** y otros WAF.

El objetivo es detectar ataques como:

```text
SQL Injection
XSS
Path Traversal
Command Injection
Protocol Attacks
```

OWASP indica que el CRS busca proteger aplicaciones frente a una amplia variedad de ataques, incluyendo categorías relacionadas con el OWASP Top 10. ([OWASP Foundation][1])

---

# 12. OWASP y DevSecOps

Uno de los mayores aportes actuales de OWASP es que sus proyectos pueden utilizarse durante prácticamente todo el ciclo de vida del software.

```text
PLANIFICACIÓN
     │
     ▼
DISEÑO
 Threat Modeling
     │
     ▼
DESARROLLO
 ASVS + Cheat Sheets
     │
     ▼
BUILD
 Dependency-Check
 CycloneDX
     │
     ▼
TEST
 ZAP + WSTG
     │
     ▼
DEPLOY
 CI/CD Security
     │
     ▼
OPERACIÓN
 WAF + Monitoring
```

Esto representa muy bien la filosofía:

# **Shift Left Security**

Es decir:

> Incorporar la seguridad desde las primeras etapas del desarrollo y no esperar hasta que la aplicación esté terminada.

---

# Resumen de las herramientas y aportes

| Proyecto/Herramienta   | Propósito                                              |
| ---------------------- | ------------------------------------------------------ |
| **OWASP Top 10**       | Identificación de los principales riesgos de seguridad |
| **ASVS**               | Requisitos verificables de seguridad                   |
| **SAMM**               | Evaluación de madurez de seguridad                     |
| **WSTG**               | Metodología para pruebas de seguridad                  |
| **ZAP**                | Pruebas dinámicas de aplicaciones web                  |
| **Dependency-Check**   | Detección de dependencias vulnerables                  |
| **Dependency-Track**   | Gestión de riesgos de componentes                      |
| **CycloneDX**          | Generación y gestión de SBOM                           |
| **Juice Shop**         | Entrenamiento práctico                                 |
| **WebGoat**            | Laboratorios de vulnerabilidades                       |
| **Amass**              | Descubrimiento de superficie de ataque                 |
| **Threat Dragon**      | Modelado de amenazas                                   |
| **Cheat Sheet Series** | Buenas prácticas para desarrollo seguro                |
| **CRS**                | Reglas de protección para aplicaciones web             |

---

## Idea fundamental

El mayor aporte de OWASP no es solamente haber creado el **Top 10**.

Su verdadero valor está en haber construido un **ecosistema abierto de estándares, metodologías, guías, aplicaciones de entrenamiento y herramientas** que permiten integrar la seguridad en todo el ciclo de vida del software. ([OWASP Foundation][1])

En términos de una arquitectura moderna de ciberseguridad y DevSecOps, podría resumirse así:

> **OWASP proporciona el conocimiento para saber qué proteger, los estándares para definir cómo hacerlo, las herramientas para verificarlo y los laboratorios para aprender a hacerlo.**

[1]: https://owasp.org/projects/ "Projects | OWASP Foundation"
[2]: https://github.com/OWASP/Top10 "GitHub - OWASP/Top10: Official OWASP Top 10 Document Repository · GitHub"
[3]: https://devguide.owasp.org/en/05-implementation/02-dependencies/01-dependency-check/ "Dependency-Check - OWASP Developer Guide"

---

# TALLER EN GRUPOS.

### Enunciado del Trabajo: Investigación sobre el OWASP Top 10

Realizar  en grupo de trabajo existentes el trabajo enunciado a continuación.
Cada  grupo de trabajo debe crear una carpeta dentro de esta carpeta del repositorio, titulada con el número del grupo y que contenga un README.md con el desarrollo de tema de trabajo e integrantes del grupo.


# Desarrollo.

**Título:** Análisis de Vulnerabilidades en el OWASP Top 10: Métodos de Explotación y Prevención

**Enunciado:**

En la actualidad, la seguridad de las aplicaciones web se ha convertido en una de las principales preocupaciones para las organizaciones de todos los tamaños. Con el fin de mejorar la comprensión de las vulnerabilidades comunes y los riesgos asociados, este trabajo tiene como objetivo investigar y documentar las vulnerabilidades listadas en el **OWASP Top 10**. 

El OWASP Top 10 es una clasificación que identifica las vulnerabilidades más críticas en aplicaciones web, proporcionando una guía fundamental para desarrolladores, arquitectos de seguridad y equipos de gestión de riesgos. 

A lo largo de este trabajo, se explorarán las siguientes secciones:

1. **Descripción de cada vulnerabilidad**: Explicar cada una de las vulnerabilidades del OWASP Top 10, incluyendo su naturaleza, causas y el impacto potencial en las aplicaciones y sistemas.

2. **Métodos de explotación**: Para cada vulnerabilidad, investigar y documentar métodos específicos que los atacantes pueden utilizar para explotarlas. Incluir ejemplos de ataques reales, así como descripciones de herramientas y técnicas comúnmente utilizadas en la explotación de estas vulnerabilidades.


3. **Mejores prácticas de prevención y mitigación**: Proporcionar recomendaciones y mejores prácticas para mitigar cada vulnerabilidad. 

**Objetivos del Trabajo:**
- Investigar y analizar cada vulnerabilidad del OWASP Top 10.
- Documentar métodos de explotación asociados con cada vulnerabilidad.
- Proporcionar recomendaciones prácticas para prevenir y mitigar los riesgos asociados.

# Referencias de apoyo.

- https://owasp.org/Top10/es/
- https://www.checkpoint.com/es/cyber-hub/cloud-security/what-is-application-security-appsec/owasp-top-10-vulnerabilities/
- https://certera.com/blog/mitigating-the-owasp-top-10-vulnerabilities/
- https://owasp.org/www-project-top-ten/
- https://www.akamai.com/es/blog/security/owasp-top-10-api-security-risks-2023-edition
- https://cloudkul.com/blog/owasp-top-10-2021/
- https://unaaldia.hispasec.com/2017/11/owasp-publica-la-edicion-2017-de-su-top-10-web-application-security-risks.html
