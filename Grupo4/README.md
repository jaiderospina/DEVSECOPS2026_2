![BANER](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/Banner_OWASP-TOP10.jpg?raw=true)

# OWASP Top 10:2025

## 👥 Integrantes

<p align="left">
  <img src="https://img.shields.io/badge/Integrante_1-Daniel_Steven_Molina_Lancheros-blue?style=for-the-badge&logo=git&logoColor=white" alt="Daniel" />
  <br>
  <img src="https://img.shields.io/badge/Integrante_2-Jennifer_Dayan_Ruiz_Camelo-purple?style=for-the-badge&logo=github&logoColor=white" alt="Jennifer" />
  <br>
  <img src="https://img.shields.io/badge/Integrante_3-Alexander_Díaz_Molano-green?style=for-the-badge&logo=github&logoColor=white" alt="Alexander" />
  <br>
  <img src="https://img.shields.io/badge/Integrante_4-Hilary_Michelle_Muñoz_Rey-orange?style=for-the-badge&logo=letsencrypt&logoColor=white" alt="Hilary" />
  <br>
  <img src="https://img.shields.io/badge/Integrante_5-Eduar_Torres-red?style=for-the-badge&logo=codeforces&logoColor=white" alt="Eduar" />
</p>

---

## 📊 Comparativa OWASP Top 10 (2021 vs 2025)

| Pos. | OWASP Top 10 (2021) | OWASP Top 10 (2025) | Cambio / Comportamiento | Descripción breve |
| :---: | :--- | :--- | :---: | :--- |
| **#1** | Control de acceso averiado | Control de acceso defectuoso | 🟰 **Sin cambio** | Sigue liderando la lista; absorbe vulnerabilidades como SSRF. |
| **#2** | Fallos criptográficos | Configuración de seguridad incorrecta | ⬆️ **Subió 3 puestos** | Aumentó por errores en nubes, contenedores y entornos. |
| **#3** | Inyección | Fallos en la cadena de suministro de software | 🆕 **Nuevo ingreso** | Enfocado en dependencias, compilaciones y código de terceros. |
| **#4** | Diseño inseguro | Fallos criptográficos | ⬇️ **Bajó 2 puestos** | Baja de posición por mejoras globales en el uso de cifrado TLS. |
| **#5** | Configuración de seguridad incorrecta | Inyección | ⬇️ **Bajó 2 puestos** | Desciende gracias al uso generalizado de consultas parametrizadas. |
| **#6** | Componentes vulnerables y obsoletos | Diseño inseguro | ⬇️ **Bajó 2 puestos** | Refleja mayor esfuerzo en la fase de modelado de amenazas. |
| **#7** | Fallos de identificación y autenticación | Fallos de autenticación | 🟰 **Sin cambio** | Simplifica su nombre; persisten problemas de gestión de sesiones. |
| **#8** | Fallos en la integridad del software y los datos | Fallos en la integridad del software o de los datos | 🟰 **Sin cambio** | Verifica que actualizaciones y datos no sean alterados. |
| **#9** | Fallos en el registro y la monitorización de seguridad | Fallos en el registro y las alertas de seguridad | 🟰 **Sin cambio** | Enfatiza que registrar no sirve sin alertas activas. |
| **#10** | Falsificación de solicitud del lado del servidor (SSRF) | Mala gestión de situaciones excepcionales | 🆕 **Nuevo ingreso** | Creada para errores de lógica en tiempo de ejecución. |


---
## A01:2025 - Control de acceso defectuoso
###  🛡️ ¿Qué es?
Es una falla donde la aplicación no restringe correctamente lo que los usuarios autenticados pueden hacer. Esto permite que un atacante robe información, destruya datos o ejecute funciones sin permiso.
### 🚨 Formas comunes en que ocurre:
- Principio roto: Dar acceso general a algo que debería estar restringido por defecto.
- Manipulación de URLs o APIs: Cambiar parámetros, URLs o solicitudes para ver datos de otros (como cambiar un número de cuenta o usar herramientas como curl).
- IDOR: Ver o editar la cuenta de otra persona alterando su identificador único.
- Elevación de privilegios: Actuar como administrador sin serlo o manipular tokens (como JWT) o cookies para ganar más permisos.
- Navegación forzada: Entrar a páginas protegidas o de administración escribiendo la ruta directamente sin tener el rol adecuado.
### 🛠️ ¿Cómo prevenirlo?
- Denegar por defecto: Todo debe estar bloqueado a menos que sea un recurso público.
- Validación en el servidor: Nunca confíes solo en la interfaz de usuario o JavaScript; la seguridad debe validarse en el servidor.
- Lógica segura: Asegúrate de que los usuarios solo puedan acceder a sus propios registros y no a los de los demás.
- Control de tokens: Haz que los tokens (JWT) tengan poca duración y asegúrate de cerrar sesiones correctamente.
- Pruebas: Incluye pruebas unitarias y de integración enfocadas en verificar los permisos.
  
### 📝 Ejemplos de escenarios de ataque
Escenario n.° 1: La aplicación utiliza datos no verificados en una llamada SQL que accede a información de la cuenta:

```java
pstmt.setString(1, request.getParameter("acct"));
ResultSet results = pstmt.executeQuery( );
```
Un atacante puede modificar fácilmente el parámetro 'acct' del navegador para enviar cualquier número de cuenta deseado. Si no se verifica correctamente, el atacante puede acceder a la cuenta de cualquier usuario.
```java
https://example.com/app/accountInfo?acct=notmyacct
```
![Infografía A01 - Fallos en registro y alertas](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/OWASPTOP10-A01-2025.jpg?raw=true)

---

## A02:2025 - Configuración de seguridad incorrecta
### 🛡️ ¿Qué es?
Ocurre cuando un sistema, aplicación o servicio en la nube se configura incorrectamente desde el punto de vista de la seguridad, creando vulnerabilidades. Aparece debido al uso de software altamente configurable y afecta a una gran cantidad de aplicaciones si no se implementa un proceso seguro.

### 🚨 Formas comunes en que ocurre:
- Falta de seguridad o permisos incorrectos: Carencia de medidas adecuadas en la pila de aplicaciones o permisos mal configurados en servicios de la nube.
- Funciones innecesarias: Mantener instaladas o habilitadas funciones, puertos, servicios, páginas, marcos de prueba o privilegios que no se utilizan.
- Credenciales por defecto: Cuentas predeterminadas y sus contraseñas originales siguen habilitadas y sin cambios.
- Errores excesivos: Falta de configuración centralizada para interceptar fallos, mostrando rastreos de pila u otros mensajes demasiado informativos a los usuarios.
- Inseguridad predeterminada: Funciones de seguridad recientes desactivadas, priorización excesiva de compatibilidad con versiones anteriores, o servidores que no envían encabezados y directivas de seguridad seguras.
  
### 🛠️ ¿Cómo prevenirlo?
- Proceso de endurecimiento automatizado (Hardening): Implementar un proceso repetible y automatizado para configurar entornos (desarrollo, pruebas y producción) de forma idéntica pero con credenciales diferentes.
- Plataforma minimalista: Eliminar o no instalar funciones, componentes, documentación ni marcos de trabajo innecesarios.
- Actualización y revisión: Revisar configuraciones, parches y permisos de almacenamiento en la nube (como buckets de S3). 
- Arquitectura segmentada: Proveer separación segura entre componentes mediante segmentación, contenerización o grupos de seguridad en la nube (ACL).
- Control de errores y encabezados: Enviar directivas de seguridad a los clientes y configurar una intercepción centralizada para los mensajes de error excesivos.
- Gestión segura de credenciales: Evitar claves estáticas en el código y utilizar credenciales de corta duración, federación de identidades o accesos basados en roles.

### 📝 Ejemplos de escenarios de ataque
Escenario n.° 1 (Aplicaciones de ejemplo y credenciales por defecto): El servidor de producción incluye aplicaciones de ejemplo no eliminadas (como una consola de administración) con sus contraseñas predeterminadas intactas, permitiendo que un atacante inicie sesión y tome el control.

![Infografía A02 - Fallos en registro y alertas](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/OWASPTOP10-A02-2025.jpg?raw=true)

---

## A03:2025 - Fallos en la cadena de suministro de software

### 📋 ¿Qué es?

**A03:2025 - Software Supply Chain Failures** corresponde a los fallos de seguridad presentes en la cadena de suministro del software.
Es una de las modificaciones importantes del OWASP Top 10:2025. En 2021 existía A06 – Vulnerable and Outdated Components, pero en 2025 OWASP amplió considerablemente el concepto para cubrir no solamente componentes vulnerables, sino todo el ecosistema utilizado para construir, distribuir y actualizar software

Esta categoría analiza los riesgos asociados con:

- Dependencias de terceros.
- Librerías y frameworks.
- Paquetes de software.
- Dependencias transitivas.
- Repositorios.
- Herramientas de desarrollo.
- Procesos CI/CD.
- Artefactos de software.
- Proveedores externos.
- Componentes desactualizados o abandonados.

> 💡 Una aplicación puede tener un código propio seguro, pero si utiliza un componente externo vulnerable o comprometido, la aplicación también puede quedar expuesta.

### 🔄 Cadena de suministro de software

```text
Desarrollador
      ↓
Código fuente
      ↓
Dependencias
      ↓
Repositorio de paquetes
      ↓
CI/CD
      ↓
Build
      ↓
Artefacto
      ↓
Producción
```

### 🚨 ¿Cómo ocurre una vulnerabilidad A03?
Imagina que una aplicación Java utiliza:
```java
Aplicación
   ↓
Spring
   ↓
Log4j
```
El desarrollador puede haber escrito código completamente correcto.
Pero si Log4j tiene una vulnerabilidad crítica, la aplicación hereda ese riesgo.
Esto es especialmente peligroso porque muchas aplicaciones tienen:

```text
Dependencia directa
       ↓
Dependencia transitiva
       ↓
Otra dependencia
       ↓
Otra dependencia
```
Por ejemplo:
```text
Mi aplicación
 ├── framework A
 │    ├── biblioteca B
 │    │    └── biblioteca vulnerable C
 │    └── biblioteca D
 └── biblioteca E
```
El desarrollador quizá ni siquiera sabe que utiliza C.
Por eso OWASP 2025 hace especial énfasis en las dependencias transitivas
### 📌 Caso real más reciente: Shai-Hulud

OWASP 2025 también incluye el ataque Shai-Hulud de 2025.
Se trató de un ataque relacionado con el ecosistema npm, donde se distribuyeron versiones maliciosas de paquetes.
Según OWASP, el malware podía:
```text
infectar entorno
     ↓
extraer información sensible
     ↓
buscar tokens npm
     ↓
utilizar tokens
     ↓
publicar versiones maliciosas
     ↓
infectar más paquetes
```
OWASP señala que llegó a afectar más de 500 versiones de paquetes antes de ser interrumpido.
Este ejemplo es excelente para explicar por qué A03:2025 ya no se limita a:
"Tengo una librería con un CVE".
Ahora hablamos de todo el ecosistema de confianza del software.

### 👁️ Herramientas de prevencion
- Snyk
- Dependabot
- OWASP Dependency-Check
- GitHub Advanced Security
- herramientas de SBOM

### 🛡️ Prevención y mitigación
- ✅ Detener y Aislar: Bloquea el despliegue del componente afectado y retira de producción los contenedores o paquetes comprometidos.
- ✅ Revocar Claves: Invalida de inmediato todos los tokens de CI/CD, credenciales y certificados de firma que pudieron quedar expuestos.
- ✅ Parchear o Sustituir: Actualiza la dependencia a una versión corregida; si no existe parche, reemplaza la librería o aplica una regla de mitigación temporal.
- ✅ Bloquear Reincidencias: Añade la regla en tus herramientas SCA (Snyk, Dependabot) para rechazar automáticamente cualquier intento futuro de compilar con la versión vulnerable
- 🧪Gestión de Inventario (SBOM): Genera e inspecciona de forma explícita el inventario de software y dependencias (usando herramientas como CycloneDX o Syft) para auditar vulnerabilidades (CVEs).
- 🧪Integridad de Código: Fija versiones exactas (lockfiles) con firmas y hashes SHA-256; evita usar etiquetas como :latest. Firma artefactos mediante Sigstore/Cosign.
- 🧪Control de Repositorios: Utilice proxies o gestores internos (ej. Nexus, Artifactory) para bloquear ataques de Dependency Confusion y Typosquatting.
- 🧪Seguridad en CI/CD: Aplique el principio de menor privilegio a tokens de automatización, use runners efímeros e implemente el marco SLSA.

![Infografía A03 - Fallos en registro y alertas](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/OWASPTOP10-A03-2025.jpg?raw=true)

---
## A04:2025 — Cryptographic Failures
### 📋 ¿Qué es A04?

A04:2025 – Cryptographic Failures son errores relacionados con la protección criptográfica de la información.
OWASP explica que incluye problemas como:

- ausencia de cifrado;
- cifrado débil;
- algoritmos inseguros;
- mala administración de claves;
- claves expuestas;
- generación aleatoria insegura;
- reutilización de claves;
- problemas con IV/nonce;
- hashes inseguros;
- errores de validación de certificados;
- downgrade criptográfico.

### 🧱 ¿Qué intenta proteger la criptografía?
Principalmente:
- Confidencialidad : Que nadie pueda leer
- Integridad : Que nadie pueda modificar
- Autenticidad : Este mensaje realmente proviene de quien dice enviarlo

### 🚨 Principales Causas del Fallo

- Transmisión en texto plano: Uso de protocolos inseguros (HTTP, FTP, SMTP sin TLS) que permiten la intercepción de tráfico (Man-in-the-Middle).
- Algoritmos obsoletos o débiles: Uso de esquemas vulnerables o rotos como MD5, SHA-1, DES o RC4.
- Manejo deficiente de claves: Hardcodear claves secretas en el código fuente, almacenarlas en repositorios o no rotarlas periódicamente.
- Hashing inseguro de contraseñas: Guardar contraseñas sin salt o usando funciones rápidas no diseñadas para contraseñas (como MD5 o SHA-256 estándar en lugar de Argon2, bcrypt o PBKDF2).
- Falta de vectores de inicialización (IV): Reutilizar IVs o emplear modos de cifrado inseguros como Electronic Codebook (ECB).

Ejemplo extremadamente sencillo
Sin cifrado:
```text
Usuario
  |
  | contraseña=Daniel123
  |
  ↓
Servidor
```
Si alguien puede interceptar la comunicación:
```text
Atacante
   ↓
contraseña=Daniel123
```
Con TLS:
```text
Usuario
  |
  | 🔒 datos cifrados
  |
  ↓
Servidor
```
El atacante podría observar tráfico, pero no debería poder obtener el contenido protegido simplemente capturando los paquetes.

### 🛡️ Prevención y mitigación
- ✅ Protección en Tránsito: Forzar HTTPS mediante HSTS y usar únicamente versiones seguras del protocolo (TLS 1.2 o TLS 1.3). Deshabilitar protocolos en texto plano (HTTP, FTP).
- ✅ Protección en Reposo: Cifrar datos sensibles (PII, financieras) con algoritmos modernos y robustos como AES-256-GCM.
- ✅ Protección de Contraseñas: Usar funciones de hash adaptativas con salt automático diseñadas para credenciales (como Argon2id o bcrypt), evitando hashes simples como MD5 o SHA-256.
- ✅ Gestión de Claves: Guardar claves y secretos fuera del código fuente mediante gestores dedicados (AWS Secrets Manager, HashiCorp Vault) y rotarlos periódicamente.
- ✅ Eliminar Criptografía Débil: Prohibir esquemas obsoletos o inseguros (DES, RC4, MD5, SHA-1, modo ECB).

![Infografía A04 - Fallos en registro y alertas](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/OWASPTOP10-A04-2025.jpg?raw=true)

## A06:2025 - Diseño Inseguro



## A09:2025 - Fallos en el registro y las alertas de seguridad

### 🛡️ ¿Qué es?

Ocurre cuando la aplicación no guarda registro de lo que pasa (inicios de sesión, errores, accesos) y no tiene alertas para avisar cuando algo raro ocurre. Esto permite que un atacante actúe sin ser detectado.

### 🚨 Métodos de explotación comunes

- **Falta de registros:** No se guardan eventos importantes como intentos de acceso fallidos.
- **Alertas ineficaces:** Hay tantas alertas falsas que las importantes pasan desapercibidas.
- **Registros inseguros:** Los archivos de registro pueden ser modificados o borrados por el atacante.
- **Sin monitoreo:** Nadie revisa los registros para detectar actividades sospechosas.

### 🛠️ Mejores prácticas de prevención

- Registrar todos los eventos de seguridad (accesos, errores, cambios).
- Proteger los registros para que no puedan ser alterados.
- Configurar alertas reales con umbrales claros (no generar falsas alarmas).
- Monitorear los registros de forma centralizada.
- Tener un plan de respuesta para cuando salte una alerta.

### 📝 Ejemplo de ataque

Un banco no registra los intentos de acceso fallidos. Un atacante prueba miles de contraseñas durante días y nadie se da cuenta. Finalmente logra entrar y roba información de clientes. La brecha se descubre meses después, cuando un cliente reporta cargos no reconocidos.

![Infografía A09 - Fallos en registro y alertas](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/OWASPTOP10-A09-2025.jpg?raw=true)

---

## A10:2025 - Mala gestión de situaciones excepcionales

### 🛡️ ¿Qué es?

Es una categoría nueva. Ocurre cuando el sistema no sabe cómo reaccionar ante errores inesperados. Por ejemplo, si algo falla, el sistema puede mostrar información sensible (como el código interno) o peor aún, dar acceso al atacante "por si acaso".

### 🚨 Métodos de explotación comunes

- **Mostrar errores internos:** Al fallar, el sistema muestra detalles técnicos (rutas de archivos, versiones, etc.).
- **Fallo abierto (fail-open):** Si algo sale mal, el sistema da acceso en lugar de denegarlo.
- **Errores no registrados:** El sistema falla pero nadie lo sabe porque no quedó registro.
- **Casos límite no probados:** Los atacantes buscan situaciones que los desarrolladores no consideraron.

### 🛠️ Mejores prácticas de prevención

- Mostrar mensajes de error amigables sin información técnica sensible.
- Diseñar el sistema para que ante un error, siempre deniegue el acceso (fail-closed).
- Registrar todos los errores para poder investigarlos después.
- Probar qué pasa cuando el sistema recibe entradas inesperadas.

### 📝 Ejemplo de ataque

Un atacante envía un dato malformado a un formulario. La aplicación falla y muestra en pantalla toda la ruta del servidor, la versión del framework y el nombre de la base de datos. Con esa información, el atacante puede buscar vulnerabilidades específicas de esa versión y planear un ataque más grave.

![Infografía A10 - Fallos en registro y alertas](https://github.com/ALEKINN/TEST-DevSecOps/blob/main/OWASPTOP10-A10-2025.jpg?raw=true)
