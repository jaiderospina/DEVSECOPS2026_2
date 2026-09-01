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
###🛠️ ¿Cómo prevenirlo?
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

---

## 🔴 A03:2025 - Fallos en la cadena de suministro de software

### 📌 ¿Qué es?

**A03:2025 - Software Supply Chain Failures** corresponde a los fallos de seguridad presentes en la cadena de suministro del software.

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
