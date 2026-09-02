## 👥 Integrantes del equipo Grupo 1

🎓**Yeison Fabián Bernal**
🎓**David Diaz**
🎓**Oscar Daniel Acosta**
🎓**Ingrid Vega**
🎓**Jean Carlos Almenarez**

***Análisis de Vulnerabilidades en el OWASP Top 10: Métodos de Explotación y Prevención***

La seguridad de una aplicación web no depende únicamente de que el código funcione correctamente. Una aplicación puede cumplir con sus funciones y, aun así, tener vulnerabilidades que permitan a un atacante acceder a información privada, modificar datos, ejecutar acciones sin autorización o incluso comprometer otros sistemas.

Para entender mejor estos riesgos utilizamos el OWASP Top 10:2025, una de las referencias más conocidas dentro del área de seguridad de aplicaciones.

💡**OWASP Top 10 2025:**

Es un informe de concienciación elaborado por la comunidad internacional que enumera los diez riesgos de seguridad más críticos para las aplicaciones web.

📌**A01:2025 – Broken Access Control (fallo de control de acceso):**

El control de acceso determina qué puede hacer cada usuario dentro de una aplicación. En términos sencillos, no basta con saber quién es el usuario; también debemos comprobar qué está autorizado a hacer.

Una vulnerabilidad aparece cuando una aplicación permite que un usuario realice acciones o consulte información que debería estar restringida.

**¿Qué significa un fallo de control de acceso?**

Ocurre cuando una aplicación no verifica correctamente si un usuario tiene autorización para realizar una determinada acción o acceder a un determinado recurso.

Por ejemplo:
* Un usuario normal puede acceder a funciones exclusivas de un administrador. 
* Un usuario puede consultar información perteneciente a otro usuario. 
* Se puede modificar un recurso cambiando un identificador en una solicitud. 
* Una API permite ejecutar operaciones que el rol del usuario no debería poder realizar. 
* Se puede acceder directamente a una URL restringida sin pasar por la autorización correspondiente. 
* Un usuario puede modificar o eliminar información que no le pertenece.

🔥**Causas**

Los fallos de control de acceso pueden originarse por:

* Ausencia o implementación incorrecta de mecanismos de autorización.
* Validaciones de permisos realizadas únicamente en el frontend y no en el servidor.
* Configuración incorrecta de roles, perfiles o privilegios de usuarios.
* Asignación excesiva de permisos, incumpliendo el principio de mínimo privilegio.
* Falta de validación de los permisos sobre recursos u objetos específicos.
* Controles de acceso inconsistentes entre diferentes módulos, servicios o APIs.
* Permisos que no son revocados oportunamente cuando cambian las funciones o responsabilidades del usuario.
* Uso de identificadores manipulables que permiten acceder a recursos de otros usuarios.
* Falta de pruebas de seguridad orientadas a detectar escalamiento de privilegios horizontal o vertical.
* Configuraciones inseguras en servidores, APIs, aplicaciones o servicios que permiten acceder directamente a recursos restringidos.
* Deficiencias en la gestión y revisión periódica de roles y permisos.

**Ejemplos**

Imaginemos una aplicación:

GET /api/usuarios/100/perfil

Si el usuario autenticado corresponde al ID 100, todo parece correcto.

Pero si el atacante cambia el valor:

GET /api/usuarios/101/perfil

y la aplicación devuelve información del usuario 101 sin comprobar permisos, existe una vulnerabilidad de control de acceso.

Este tipo de escenario suele relacionarse con IDOR/BOLA, especialmente frecuente en aplicaciones y APIs.

También puede ocurrir que un usuario normal intente acceder directamente a una funcionalidad administrativa:

/admin/usuarios

Si el servidor no verifica el rol, el atacante podría acceder aunque no tenga permisos.

🔥**Herramientas utilizadas para identificar problemas**

En entornos autorizados pueden utilizarse:

* OWASP ZAP para analizar solicitudes y respuestas.
* Burp Suite para interceptar y modificar peticiones HTTP.
* Navegadores y sus herramientas de desarrollador.
* Pruebas automatizadas sobre endpoints de APIs.
* Pruebas manuales basadas en diferentes roles de usuario.
* La herramienta no reemplaza el análisis: lo importante es comprobar que cada operación tenga una autorización adecuada.

🔥**Impacto potencial en aplicaciones y sistemas**

Un fallo de control de acceso puede permitir que un usuario acceda o realice operaciones que no corresponden a sus privilegios, generando impactos como:

* Acceso no autorizado a información confidencial o restringida.
* Modificación o eliminación no autorizada de información y recursos.
* Escalamiento de privilegios, permitiendo que un usuario obtenga capacidades superiores a las asignadas.
* Acceso a información perteneciente a otros usuarios, clientes o áreas.
* Ejecución de funciones administrativas sin autorización.
* Compromiso de la confidencialidad, integridad y disponibilidad de la información.
* Alteración de configuraciones, parámetros o recursos críticos de las aplicaciones.
* Posible afectación de otros sistemas o servicios integrados con la aplicación.
* Incumplimiento de políticas internas, requisitos contractuales o disposiciones de protección de información.
* Impacto reputacional y pérdida de confianza de clientes, usuarios o partes interesadas.
* Posibles pérdidas económicas derivadas de fraude, interrupciones operativas, recuperación de información o incidentes de seguridad.

🔥**Métodos específicos de explotación – OWASP A01:2025 Broken Access Control**

Enunciamos a continuación algunos métodos que pueden utilizar los atacantes para explotar vulnerabilidades de control de acceso incluyen:

  💥 **Escalamiento de privilegios vertical**

     Un usuario con privilegios limitados intenta acceder a funcionalidades reservadas para usuarios con mayores privilegios, como administradores o supervisores.

  💥 **Escalamiento de privilegios horizontal**

     Un usuario accede a información o funcionalidades pertenecientes a otro usuario con un nivel de privilegio similar.

  💥 **Manipulación de identificadores de recursos (IDOR)**

     El atacante modifica identificadores asociados a recursos, registros, documentos u objetos para intentar acceder a información que pertenece a otro usuario.

  💥 **Acceso directo a funcionalidades restringidas**

     Se intenta acceder directamente a páginas, endpoints, servicios o funciones administrativas sin pasar por los controles de autorización correspondientes.

  💥 **Manipulación de parámetros de las solicitudes**

     Se modifican parámetros relacionados con roles, usuarios, identificadores, permisos u otros atributos para intentar obtener acceso no autorizado.

  💥 **Abuso de APIs**

     Se utilizan endpoints de API que presentan controles de autorización insuficientes o inconsistentes entre diferentes operaciones.

  💥 **Explotación de controles implementados únicamente en el cliente**

     Cuando la aplicación solamente oculta botones, menús o funcionalidades en el frontend, un atacante puede intentar invocar directamente la funcionalidad desde las solicitudes hacia el servidor.

  💥 **Explotación de configuraciones incorrectas de roles y permisos**

     Se aprovechan permisos excesivos, roles mal configurados o relaciones incorrectas entre usuarios, grupos y recursos.

  💥 **Uso indebido de cuentas o sesiones con privilegios**

     Una cuenta legítimamente autenticada puede ser utilizada para realizar acciones que exceden los privilegios que deberían corresponderle, cuando existen controles de autorización deficientes.

  💥 **Acceso a recursos mediante rutas o endpoints alternativos**

     El atacante busca diferentes rutas, métodos HTTP o interfaces que permitan acceder al mismo recurso cuando una de ellas tiene controles de autorización deficientes.

🔥**Herramientas utilizadas**

Algunas herramientas utilizadas durante una evaluación autorizada son:

* OWASP ZAP.
* Burp Suite.
* Nmap.    
* Nikto.
* OpenSCAP.
* Trivy.
* Herramientas de seguridad cloud.

🔥**Prevención**

La aplicación debería:

* Validar autorización en el servidor.
* Aplicar el principio de mínimo privilegio.
* Denegar por defecto las acciones no autorizadas.
* Implementar controles de acceso centralizados.
* No confiar en controles realizados solamente mediante JavaScript.
* Verificar permisos en cada endpoint sensible.
* Realizar pruebas con diferentes roles.
* Utilizar identificadores que no sustituyan la autorización real.
* Registrar intentos de acceso no autorizado.

**Casos Reales**

💢 Facebook – 2018 // Control de acceso - tokens // Una vulnerabilidad en la función “View As” permitió obtener tokens de acceso de otras cuentas // 50 millones de cuentas afectadas

💢 AT&T – 2024 // Acceso no autorizado - API // Se descubrió que una interfaz utilizada para acceder a datos de clientes permitía consultar información de cuentas sin los controles de autorización adecuados // Exposición de datos de clientes.

💢 GitLab – 2021 // Control de acceso // Una vulnerabilidad permitía acceder a determinados recursos mediante solicitudes que no aplicaban correctamente las restricciones de autorización. // Acceso no autorizado a información y recursos de proyectos.

📌**A02:2025 — Configuración de Seguridad Incorrecta**

Esta vulnerabilidad ocurre cuando un servidor, aplicación, framework, servicio cloud, base de datos o componente está configurado de una manera insegura, predeterminadas o incompletas, permitiendo que un atacante aproveche dichas debilidades para obtener acceso no autorizado, exponer información o comprometer el sistema. 

Esta categoría incluye errores de configuración en todos los niveles del entorno tecnológico: aplicaciones, servicios, contenedores, sistemas operativos, plataformas en la nube y componentes de red.

🔥**Causas principales**

* Uso de credenciales o configuraciones predeterminadas.
* Servicios, puertos o funcionalidades innecesarias habilitadas.
* Mensajes de error excesivamente detallados que revelan información del sistema.
* Encabezados (HTTP Security Headers) o políticas de seguridad ausentes.
* Permisos de acceso demasiado amplios en aplicaciones o infraestructura.
* Configuración incorrecta de CORS, TLS, almacenamiento o servicios cloud.
* Componentes administrativos expuestos a usuarios no autorizados.
* Falta de endurecimiento (hardening) de servidores y aplicaciones.

**Ejemplos**

El atacante normalmente comienza realizando reconocimiento.

Por ejemplo, puede buscar:

/admin
/backup
/test
/.git

o identificar servicios expuestos.

También puede observar mensajes de error de la aplicación para conocer:

Framework utilizado.
Versiones.
Rutas internas.
Stack traces.
Información de la base de datos.

Otro escenario sería encontrar almacenamiento cloud configurado como público y acceder a información que debería ser privada.

🔥**Impacto potencial**

Una configuración insegura puede provocar:

* Exposición de información sensible.
* Acceso no autorizado a sistemas o paneles administrativos.
* Ejecución de funcionalidades restringidas.
* Compromiso de la confidencialidad, integridad y disponibilidad de la información.
* Incremento de la superficie de ataque y facilidad para explotar otras vulnerabilidades.

🔥**Métodos específicos de explotación**

Los atacantes pueden aprovechar diferentes deficiencias de configuración para obtener información, acceder a funcionalidades restringidas o comprometer componentes tecnológicos. A continuación enunciamos algunos de ellos.

   💥 **Explotación de credenciales predeterminadas**

    - Descripción: Intento de acceder a aplicaciones, dispositivos o servicios que mantienen usuarios, contraseñas o claves configuradas por defecto.
    - Riesgo asociado: Acceso no autorizado y compromiso de cuentas o sistemas.

   💥 **Acceso a interfaces administrativas expuestas**

    - Descripción: Identificación y acceso a paneles de administración, consolas o interfaces de gestión que se encuentran accesibles desde redes no confiables.
    - Riesgo asociado: Compromiso de funciones administrativas.

   💥 **Explotación de servicios innecesariamente expuestos**

    - Descripción: Identificación de puertos, servicios o protocolos que no son requeridos para la operación pero permanecen accesibles.
    - Riesgo asociado: Incremento de la superficie de ataque.

   💥 **Enumeración de información técnica**
    
    - Descripción: Aprovechamiento de mensajes de error, encabezados, páginas predeterminadas o respuestas del sistema que revelan versiones, tecnologías o configuraciones.
    - Riesgo asociado: Facilita el reconocimiento y la selección de ataques posteriores.

   💥 **Explotación de permisos excesivos**
    
    - Descripción: Uso de recursos o funcionalidades que poseen permisos más amplios de los necesarios.
    - Riesgo asociado: Acceso o modificación no autorizada de información y recursos.

   💥 **Explotación de modo debug**

    - Descripción: Aprovechamiento de funcionalidades de depuración habilitadas en ambientes productivos.
    - Riesgo asociado: Posible exposición de información técnica, rutas, variables o detalles internos de la aplicación.

   💥 **Explotación de almacenamiento público**

    - Descripción: Acceso a repositorios, buckets, archivos o recursos cloud configurados con permisos públicos o demasiado permisivos.
    - Riesgo asociado: Exposición o modificación de información.

   💥 **Abuso de configuraciones CORS inseguras**

    - Descripción: Aprovechamiento de políticas de intercambio de recursos entre orígenes configuradas de manera demasiado permisiva.
    - Riesgo asociado: Acceso no deseado a determinados recursos o información.

   💥 **Explotación de configuraciones TLS inseguras**

    - Descripción: Aprovechamiento de protocolos, algoritmos o configuraciones criptográficas obsoletas o débiles.
    - Riesgo asociado: Riesgo para la confidencialidad e integridad de las comunicaciones.

   💥 **Acceso a archivos o directorios expuestos**

    - Descripción: Aprovechamiento de listados de directorios, archivos temporales, copias de seguridad o archivos de configuración accesibles desde la aplicación.
    - Riesgo asociado: Divulgación de información sensible.

    
🔥**Prevención**

La aplicación debería:

* Implementar un proceso formal de hardening
* Eliminar funcionalidades y componentes innecesarios
* Eliminar configuraciones y credenciales predeterminadas
* Aplicar el principio de mínimo privilegio
* Proteger los servicios cloud
* Deshabilitar el modo debug en producción
* Implementar manejo centralizado de errores
* Implementar Security Headers
* Mantener actualizadas las configuraciones de seguridad
* Utilizar gestión segura de secretos
* Segmentar la infraestructura
* Automatizar la validación de configuraciones
* Comparar contra líneas base de seguridad
* Revisar periódicamente la configuración

**Casos Reales**

💢 Capital One – 2019 // Una configuración incorrecta del Web Application Firewall permitió acceder a recursos de almacenamiento que contenían datos de Capital One. // Acceso no autorizado a información almacenada y exposición de datos de millones de solicitudes de crédito. El Departamento de Justicia de EE. UU. confirmó que la intrusión se produjo mediante un WAF mal configurado. 

💢 Microsoft – 2023 // Un token SAS de Azure Storage con permisos excesivos fue publicado accidentalmente en un repositorio público de GitHub. // Investigadores pudieron acceder a información interna almacenada en el recurso, incluyendo respaldos de perfiles de estaciones de trabajo y mensajes internos de Teams. Microsoft indicó que no se expusieron datos de clientes. 

💢 Storm-0501 – 2025 // Durante una intrusión, el actor modificó configuraciones de acceso de Azure Storage para permitir acceso desde infraestructura controlada por el atacante. // Posteriormente se produjo extracción de información almacenada en Azure. Microsoft documentó el caso como parte de una campaña de ransomware contra entornos cloud. 

