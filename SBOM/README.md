## Diseñando una estrategia DevsecOps
Entre los aspectos que demanda una estrategía de seguridad implica pasos como:   


## Conocer lo que se tiene para proteger lo que se quiere!!!!

# Lista de materiales de software (SBOM).

Un **SBOM** (**Software Bill of Materials** o **Lista de Materiales de Software**) es **un inventario detallado** que identifica **todos los componentes** que forman parte de un software.  
Es como la "lista de ingredientes" en un producto alimenticio, pero para un programa.

Incluye información como:
- **Nombre del componente** (por ejemplo, una librería o módulo).
- **Versión** que se usa.
- **Proveedor o autor** del componente.
- **Licencia** bajo la cual se distribuye.
- **Relaciones de dependencia** (qué depende de qué).

### ¿Para qué sirve un SBOM?
- **Ciberseguridad:** saber rápidamente si un software tiene componentes vulnerables.
- **Cumplimiento legal:** verificar licencias y evitar problemas legales.
- **Gestión de riesgos:** entender mejor el "ecosistema" de un programa.
- **Respuestas a incidentes:** identificar más rápido qué parte del software hay que corregir.

Hoy en día, los SBOM son muy importantes, sobre todo tras normativas como el **Executive Order 14028** de EE.UU. que exige su uso en ciertos contextos de ciberseguridad.

# Ejemplo No 1.

Un **SBOM** puede presentarse en varios formatos (como **CycloneDX**, **SPDX** o **SWID**), este ejemplo de manera sencilla ilustra un caso en formato **SPDX** (uno de los más comunes), que es básicamente un archivo de texto estructurado.

Imagina que tienes un proyecto llamado `MiAppWeb` que usa dos librerías: `React v18.2.0` y `Axios v1.5.0`.  
Un SBOM muy básico en formato SPDX podría verse así:

```
SPDXVersion: SPDX-2.2
DataLicense: CC0-1.0
SPDXID: SPDXRef-DOCUMENT
DocumentName: MiAppWeb-SBOM
DocumentNamespace: http://example.com/spdxdocs/miappweb-sbom-1234
Creator: Tool: SBOM-Generator 1.0
Created: 2025-04-26T12:00:00Z

##### Información sobre los componentes:

PackageName: react
SPDXID: SPDXRef-Package-react
PackageVersion: 18.2.0
PackageSupplier: Organization: Meta Platforms, Inc.
PackageDownloadLocation: https://www.npmjs.com/package/react
PackageLicenseDeclared: MIT

PackageName: axios
SPDXID: SPDXRef-Package-axios
PackageVersion: 1.5.0
PackageSupplier: Organization: Axios Project
PackageDownloadLocation: https://www.npmjs.com/package/axios
PackageLicenseDeclared: MIT
```

---

🔹 **¿Qué ves aquí?**
- Información del **documento** (quién lo creó, cuándo, etc.)
- Cada **paquete** (componente) tiene su nombre, versión, proveedor, sitio de descarga y licencia.
- Todo esto ayuda a saber **qué contiene tu software**.

---

También en empresas grandes, los SBOM son mucho más extensos e incluyen **cientos o miles de componentes**, con detalles adicionales como:
- Hashes de integridad (SHA-256)
- Relación padre-hijo (quién depende de quién)
- Información sobre vulnerabilidades conocidas

# Ejemplo No 2

Un **SBOM (Software Bill of Materials)** en **formato de tabla**, como podría verse en una herramienta de gestión o en una hoja de cálculo:

| **Nombre del Componente** | **Versión** | **Proveedor**           | **Licencia** | **Ubicación de Descarga**                          | **Hash (SHA-256)**                              |
|---------------------------|-------------|--------------------------|--------------|----------------------------------------------------|--------------------------------------------------|
| React                     | 18.2.0      | Meta Platforms, Inc.     | MIT          | https://www.npmjs.com/package/react                | `e3b0c44298fc1c149afbf4c8996fb924...`            |
| Axios                     | 1.5.0       | Axios Project            | MIT          | https://www.npmjs.com/package/axios                | `b6d81b360a5672d80c27430f39153e2c...`            |
| Lodash                    | 4.17.21     | OpenJS Foundation        | MIT          | https://www.npmjs.com/package/lodash               | `de9f2c7fd25e1b3afad3e85a0bd17d9b...`            |
| Express                   | 4.18.2      | OpenJS Foundation        | MIT          | https://www.npmjs.com/package/express              | `4f4adcbf8c6f66a8aa7d59b7f8dd6b44...`            |

### 🔍 Explicación rápida de cada columna:

- **Nombre del Componente**: la librería o módulo utilizado.
- **Versión**: versión exacta del componente.
- **Proveedor**: quién lo desarrolló o mantiene.
- **Licencia**: bajo qué términos legales se puede usar.
- **Ubicación de Descarga**: de dónde se obtiene el componente.
- **Hash (SHA-256)**: suma de verificación para asegurar que no ha sido alterado.

---

Este formato es útil para:
- **Auditorías de seguridad**
- **Cumplimiento de licencias**
- **Detección rápida de vulnerabilidades** (cuando alguna versión tiene un CVE asociado)

Si estás trabajando en desarrollo seguro o ciberseguridad, puedes usar herramientas como:
- `Syft` (de Anchore)
- `CycloneDX CLI`
- `OWASP Dependency-Track`


# Tarea.

Investigar y documentar  cómo generar un SBOM automáticamente desde un proyecto Node.js, Python o similar.

---


<div align="center">
  <h1>Generación automática de un SBOM en proyectos Node.js y Python</h1>
</div>


## ¿Qué es un SBOM?

Un **SBOM (Software Bill of Materials)** es un inventario detallado de todos los componentes de software que conforman una aplicación. Este archivo estructurado enumera:

- Bibliotecas externas utilizadas.
- Dependencias directas e indirectas.
- Versiones específicas.
- Licencias de cada componente.
- Hashes para verificar integridad.
- Información de proveedor y origen.

Un SBOM puede generarse en formatos estándar como **CycloneDX**, **SPDX** o **SWID**.

## ¿Por qué es importante?

### 1. **Seguridad**
- Detecta vulnerabilidades conocidas (ej. Log4Shell).
- Mejora la respuesta a incidentes de seguridad.

### 2. **Cumplimiento de licencias**
- Ayuda a identificar licencias restrictivas o incompatibles.
- Asegura cumplimiento legal y normativo.

### 3. **Trazabilidad**
- Facilita auditorías y revisiones.
- Permite saber de dónde provienen los componentes.

### 4. **Integración en DevSecOps**
- Se puede automatizar en pipelines CI/CD.
- Apoya el desarrollo seguro desde la base.

## ¿Qué contiene un SBOM típico?

| Elemento       | Descripción                                                                 |
|----------------|-----------------------------------------------------------------------------|
| **Componentes**| Lista de bibliotecas, frameworks, binarios, contenedores, etc.              |
| **Versiones**  | Versiones específicas de cada componente.                                   |
| **Licencias**  | Tipo de licencia (MIT, GPL, Apache, etc.).                                  |
| **Origen**     | De dónde proviene cada componente (URL, repositorio, etc.).                 |
| **Hashes**     | Hash criptográfico SHA-256 o similar para verificar la integridad.          |
| **Relaciones** | Describe cómo los componentes se relacionan entre sí (dependencias, etc.). |

<div align="center">
  <h1>Herramientas comunes para generar un SBOM</h1>
</div>

<div align="center">
  <h2>1. Node.js</h2>
</div>

#### Opción A: Usando CycloneDX para Node.js

- **Instalación**:
  ```bash
  npm install -g @cyclonedx/bom
  ```

- **Generación del SBOM**:
  Ejecuta dentro del proyecto con `package-lock.json`:
  ```bash
  cyclonedx-bom -o bom.xml
  ```

- **Formato alternativo (JSON)**:
  ```bash
  cyclonedx-bom -o bom.json -j
  ```

#### Opción B: Usando Syft

- **Instalación (recomendado vía curl o brew)**:
  ```bash
  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
  ```

- **Generación del SBOM para proyectos Node.js**:
  ```bash
  syft dir:. --output cyclonedx-json
  ```

<div align="center">
  <h2>2. Python</h2>
</div>

#### Opción A: Usando CycloneDX Python

- **Instalación**:
  ```bash
  pip install cyclonedx-bom
  ```

- **Requisitos**:
  Tener un archivo `requirements.txt` o usar `pipenv`/`poetry`.

- **Generar SBOM desde requirements.txt**:
  ```bash
  cyclonedx-py -r requirements.txt -o sbom.xml
  ```

- **Con Poetry**:
  ```bash
  cyclonedx-py -p poetry -o sbom.xml
  ```

#### Opción B: Syft para Python

- **Uso directo desde la raíz del proyecto**:
  ```bash
  syft dir:. --output spdx-json
  ```

## Formatos comunes de SBOM

| Formato     | Características                                 |
|-------------|--------------------------------------------------|
| CycloneDX   | Enfocado en seguridad. Soporta XML y JSON.       |
| SPDX        | Estandarizado por Linux Foundation. Uso legal.   |
| SWID        | Más usado en entornos empresariales cerrados.    |


## Recomendaciones

- **Integrar en CI/CD**: Automatiza la generación de SBOMs en pipelines (GitHub Actions, GitLab CI, etc.).
- **Verifica vulnerabilidades**: Usa herramientas como `grype` o `trivy` junto con el SBOM.
- **Versiona el SBOM**: Sube el `sbom.json` o `sbom.xml` a tu repositorio para trazabilidad.

