## 👥 Integrantes del equipo Grupo 1

🎓**Yeison Fabián Bernal**
🎓**David Diaz**
🎓**Oscar Daniel Acosta**
🎓**Ingrid Vega**
🎓**Jean Carlos Almenarez**

📌**Participación Jean Carlos**

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

## 📌 Participación

**Daniel** 

* **A09:2025 – Fallas en el Registro y Alertamiento de Seguridad**
* **A10:2025 – Manejo Inadecuado de Condiciones Excepcionales**

---

# A09:2025 – Fallas en el Registro y Alertamiento de Seguridad

Las **fallas en el registro y alertamiento de seguridad** ocurren cuando una aplicación no registra correctamente los eventos relevantes para la seguridad, no protege adecuadamente sus registros o no genera alertas cuando sucede una actividad sospechosa.
En otras palabras, una aplicación puede estar siendo atacada y, aunque el ataque esté ocurriendo, el equipo encargado de la seguridad puede no enterarse a tiempo.
El registro de eventos, conocido comúnmente como **logging**, y el monitoreo permiten conocer qué está sucediendo dentro de una aplicación y facilitan la detección, investigación y respuesta ante incidentes.

Por ejemplo, deberían existir registros relacionados con:

* Inicios de sesión exitosos.
* Inicios de sesión fallidos.
* Cambios de contraseña.
* Cambios de permisos.
* Creación, modificación o eliminación de usuarios.
* Operaciones administrativas.
* Acceso a información sensible.
* Errores relacionados con autenticación o autorización.
* Actividades sospechosas.
* Errores críticos de la aplicación.

El problema no consiste solamente en "tener logs". También es necesario que estos registros sean **útiles, protegidos, centralizados y monitoreados**.

---

## ¿Por qué ocurre?

Algunas de las causas más comunes de A09 son:

### 1. Falta de registros de seguridad

La aplicación simplemente no registra eventos importantes.

Por ejemplo:

```text
Usuario: admin
Acción: cambio de contraseña
Resultado: exitoso
```

Si este evento no queda registrado, posteriormente será mucho más difícil determinar quién realizó el cambio.

---

### 2. No registrar intentos fallidos

Un atacante puede intentar miles de combinaciones de usuario y contraseña.
Si solamente se registran los accesos exitosos, el sistema pierde información fundamental para detectar ataques de fuerza bruta.

Ejemplo:

```text
Login fallido - usuario: admin
Login fallido - usuario: admin
Login fallido - usuario: admin
Login fallido - usuario: admin
...
Login exitoso - usuario: admin
```

La secuencia anterior podría ser una señal de ataque.

---

### 3. No generar alertas

Registrar información no es suficiente.
Si un atacante realiza 1.000 intentos de autenticación y el sistema los registra pero nadie los revisa, el registro tiene poca utilidad para una respuesta inmediata.
Por eso es importante implementar reglas de alertamiento.

Ejemplo:

```text
10 intentos fallidos en 1 minuto
        ↓
Generación de alerta
        ↓
Revisión del evento
        ↓
Bloqueo o investigación
```

---

### 4. Logs descentralizados

Cuando cada servidor guarda sus registros de manera independiente, investigar un incidente puede convertirse en una tarea complicada.

Por ejemplo:

```text
Servidor Web
      ↓
auth.log

Servidor API
      ↓
application.log

Servidor BD
      ↓
database.log
```

El equipo de seguridad tendría que revisar diferentes sistemas para reconstruir lo ocurrido.
Una alternativa más adecuada es centralizar los registros.

```text
Servidor Web ─────┐
Servidor API ─────┼──→ Sistema centralizado de logs
Servidor BD ──────┤
Firewall ─────────┘
                         ↓
                    Monitoreo
                         ↓
                      Alertas
```

---

### 5. Registrar información sensible

Los logs también pueden convertirse en un problema de seguridad.

No se deberían almacenar innecesariamente:

* Contraseñas.
* Tokens de autenticación.
* Claves privadas.
* Información financiera completa.
* Secretos de aplicaciones.
* Tokens de sesión.

Un error como:

```text
ERROR login:
username=admin
password=MiPassword123
```

puede convertir el sistema de logging en una nueva fuente de exposición.

---

### 6. No proteger los registros

Los logs deben protegerse contra:

* Modificación.
* Eliminación.
* Acceso no autorizado.
* Manipulación por parte de atacantes.

Si un atacante obtiene privilegios administrativos y puede borrar los registros, podría intentar eliminar evidencia de sus actividades.

---

# Impacto de A09

Una implementación deficiente de logging y alertamiento puede provocar:

* Detección tardía de ataques.
* Mayor tiempo de permanencia del atacante.
* Dificultad para investigar incidentes.
* Pérdida de evidencia.
* Dificultad para determinar el alcance de una intrusión.
* Incumplimiento de requisitos de auditoría.
* Mayor impacto económico y operativo.

Una de las consecuencias más importantes es que **un ataque puede permanecer oculto durante mucho tiempo**.

---

# Métodos de Explotación de A09

El atacante puede aprovechar la falta de monitoreo para realizar actividades sin ser detectado.

## 1. Fuerza bruta

El atacante realiza numerosos intentos de autenticación.

Si no existen alertas:

```text
Intento 1 → Fallido
Intento 2 → Fallido
Intento 3 → Fallido
...
Intento 500 → Exitoso
```

El ataque podría pasar desapercibido.

---

## 2. Escalamiento de privilegios

Un atacante que obtiene una cuenta con pocos privilegios puede intentar acceder a permisos superiores.

Si los cambios de permisos no son registrados:

```text
Usuario normal
      ↓
Obtiene privilegios administrativos
      ↓
No se genera alerta
      ↓
Continúa operando
```

Esto dificulta detectar el compromiso.

---

## 3. Extracción lenta de información

Un atacante puede evitar realizar una extracción masiva de datos y hacerlo lentamente.

Por ejemplo:

```text
Día 1 → 100 registros
Día 2 → 100 registros
Día 3 → 100 registros
...
```

Si no existen mecanismos de monitoreo adecuados, el comportamiento puede no generar una alerta.

---

## 4. Manipulación o eliminación de registros

Si los logs no están protegidos correctamente, un atacante con suficientes privilegios podría intentar modificarlos o eliminarlos.

Esto afecta directamente la capacidad de realizar una investigación forense.

---

# Herramientas relacionadas

Existen diferentes herramientas que pueden utilizarse para implementar logging, monitoreo, análisis y alertamiento.

### Wazuh

[Wazuh](https://wazuh.com?utm_source=chatgpt.com)

Plataforma de seguridad que permite recopilar y analizar eventos, detectar comportamientos sospechosos y generar alertas.

### Splunk

[Splunk](https://www.splunk.com?utm_source=chatgpt.com)

Plataforma ampliamente utilizada para la recopilación, búsqueda y análisis de grandes cantidades de datos y registros.

### Elastic Stack

[Elastic Security](https://www.elastic.co/security?utm_source=chatgpt.com)

Permite centralizar y analizar logs y eventos de seguridad.

### Microsoft Sentinel

[Microsoft Sentinel](https://www.microsoft.com/en-us/security/business/siem-and-xdr/microsoft-sentinel?utm_source=chatgpt.com)

Solución SIEM utilizada para recopilar información de seguridad, correlacionar eventos y generar alertas.

### Burp Suite

[Burp Suite](https://portswigger.net/burp?utm_source=chatgpt.com)

Puede utilizarse durante pruebas de seguridad para analizar las solicitudes y respuestas de una aplicación web.

### OWASP ZAP

[OWASP ZAP](https://www.zaproxy.org?utm_source=chatgpt.com)

Herramienta de pruebas de seguridad de aplicaciones web que puede ayudar a identificar diferentes comportamientos vulnerables.

---

# Casos relacionados con A09

## Caso 1 – Exposición de información en servicios de salud

Un ejemplo de los riesgos asociados a una deficiente capacidad de detección se presenta en incidentes relacionados con proveedores de servicios de salud, donde el acceso no autorizado a grandes cantidades de información puede permanecer sin ser identificado durante largos períodos.

Este tipo de escenario demuestra la importancia de:

* Registrar accesos.
* Monitorear actividades anormales.
* Generar alertas.
* Investigar eventos sospechosos.
* Mantener los registros disponibles para análisis posteriores.

Cuando estas capacidades son insuficientes, el tiempo necesario para detectar un incidente puede aumentar considerablemente.

---

## Caso 2 – Incidentes en el sector aeronáutico

Otro ejemplo se encuentra en incidentes relacionados con compañías del sector aeronáutico en los que se produjo exposición de información de clientes y posteriormente se generaron consecuencias regulatorias.
Estos casos muestran que la seguridad no termina en prevenir una vulnerabilidad.

También es necesario poder:

1. Detectar actividades sospechosas.
2. Registrar correctamente los eventos.
3. Investigar lo sucedido.
4. Responder rápidamente.
5. Mantener evidencia para determinar el alcance del incidente.

---

# Prevención de A09

Para reducir el riesgo asociado a A09 se recomienda implementar una estrategia de logging y monitoreo de seguridad.

## Eventos que deberían registrarse

Como mínimo, deberían considerarse:

* Intentos de autenticación exitosos.
* Intentos de autenticación fallidos.
* Cambios de contraseña.
* Cambios de privilegios.
* Creación y eliminación de usuarios.
* Operaciones administrativas.
* Cambios de configuración.
* Errores relacionados con autorización.
* Acceso a recursos sensibles.
* Actividades potencialmente sospechosas.

---

## Centralización

Los registros importantes deberían enviarse a una plataforma centralizada.

```text
                  ┌──────────────┐
                  │ Servidor Web │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │ Servidor API │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │ Base de Datos│
                  └──────┬───────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Centralización  │
                │    de Logs      │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │     Alertas     │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │    Respuesta    │
                │   al incidente  │
                └─────────────────┘
```

---

## Alertas

No todos los eventos requieren una alerta inmediata.

Es recomendable establecer reglas para detectar comportamientos anormales.

Ejemplos:

```text
Muchos intentos fallidos de login
                ↓
          Posible fuerza bruta
```

```text
Cambio de privilegios inesperado
                ↓
       Posible escalamiento
```

```text
Acceso masivo a información
                ↓
      Posible extracción de datos
```

---

## Protección de los logs

Los registros deben contar con controles que dificulten su manipulación.

Algunas medidas:

* Control de acceso.
* Separación de privilegios.
* Centralización.
* Retención adecuada.
* Integridad de registros.
* Monitoreo de acceso a los logs.
* Copias de respaldo cuando corresponda.

---

# A10:2025 – Manejo Inadecuado de Condiciones Excepcionales

**A10:2025 – Mishandling of Exceptional Conditions**, o manejo inadecuado de condiciones excepcionales, se relaciona con situaciones en las que una aplicación no maneja correctamente errores, excepciones o estados inesperados.
Un error por sí solo no necesariamente representa una vulnerabilidad.

El problema aparece cuando el comportamiento producido por ese error permite:

* Saltarse controles de seguridad.
* Obtener información sensible.
* Continuar una operación que debería detenerse.
* Acceder a recursos sin autorización.
* Dejar el sistema en un estado inconsistente.
* Generar condiciones inseguras.

---

# Ejemplo de Fail Open

Uno de los conceptos importantes relacionados con este riesgo es **fail open**.
Un sistema debería bloquear una operación cuando no puede determinar correctamente si esta es segura.

Sin embargo, en un comportamiento inseguro puede ocurrir:

```text
Solicitud
   ↓
Validación de seguridad
   ↓
Ocurre una excepción
   ↓
Error no controlado
   ↓
Sistema continúa
   ↓
Operación permitida
```

Esto se conoce como un patrón de **fail open**.

En determinadas situaciones de seguridad, el comportamiento esperado debería ser:

```text
Solicitud
   ↓
Validación
   ↓
Ocurre una excepción
   ↓
Operación bloqueada
   ↓
Error controlado
   ↓
Evento registrado
```

Este principio se conoce como **fail closed**.

---

# Causas comunes de A10

## 1. Excepciones sin controlar

Por ejemplo:

```python
try:
    resultado = operacion()
except:
    pass
```

El problema de este enfoque es que la aplicación puede ignorar completamente una condición inesperada.
Una excepción debería ser manejada de manera explícita y segura.

---

## 2. Validaciones incompletas

Una aplicación puede validar correctamente los datos normales, pero no comprobar qué sucede cuando recibe:

* Parámetros faltantes.
* Valores negativos.
* Valores extremadamente grandes.
* Tipos de datos inesperados.
* Valores nulos.
* Solicitudes incompletas.

---

## 3. Mensajes de error demasiado detallados

Un mensaje como:

```text
Database connection failed:
host=10.10.10.25
database=production
user=admin
driver=PostgreSQL
```

puede revelar información que debería permanecer interna.
Los usuarios deberían recibir mensajes controlados, mientras que los detalles técnicos deberían registrarse internamente.

Ejemplo:

```text
Usuario:
"Ha ocurrido un error procesando la solicitud."

Log interno:
Error de conexión con base de datos.
Exception ID: 82f91a
```

---

## 4. Condiciones de carrera

Una condición de carrera ocurre cuando dos o más operaciones se ejecutan de manera concurrente y el resultado depende del orden en que se procesan.

Por ejemplo:

```text
Solicitud A ───────┐
                   ├──→ Validación
Solicitud B ───────┘
                   ↓
             Operación crítica
```

Si la aplicación no controla correctamente la concurrencia, un atacante podría intentar aprovechar el comportamiento para realizar una operación más de una vez o saltarse una validación.

---

## 5. Manejo incorrecto de permisos

Una excepción durante la comprobación de autorización no debería convertirse automáticamente en una autorización.

Ejemplo conceptual:

```text
¿Usuario autorizado?
        ↓
      Error
        ↓
¿Entonces permitir?
        ↓
       ❌
```

El error debería producir un comportamiento seguro:

```text
¿Usuario autorizado?
        ↓
      Error
        ↓
   Denegar acceso
        ↓
Registrar evento
```

---

# Métodos de Explotación de A10

Los atacantes pueden intentar provocar condiciones excepcionales para observar cómo responde la aplicación.

## 1. Parámetros faltantes

Por ejemplo:

```http
POST /api/users
Content-Type: application/json

{
    "username": "admin"
}
```

Si la aplicación esperaba también un campo de autorización o alguna información adicional, el atacante puede analizar qué ocurre.

---

## 2. Valores extremos

Ejemplos:

```text
ID = -1
ID = 0
ID = 999999999999999999
```

También pueden probarse:

```text
String vacío
NULL
Valores demasiado largos
Tipos incorrectos
```

El objetivo es determinar si una condición inesperada produce un comportamiento inseguro.

---

## 3. Solicitudes simultáneas

Un atacante puede enviar solicitudes de manera concurrente para intentar generar una condición de carrera.

Por ejemplo:

```text
Solicitud 1 ──→ Verificar saldo ──→ Retirar
Solicitud 2 ──→ Verificar saldo ──→ Retirar
Solicitud 3 ──→ Verificar saldo ──→ Retirar
```

Si las operaciones no están correctamente sincronizadas, podría producirse un resultado diferente al esperado.

---

## 4. Análisis de mensajes de error

Los errores pueden proporcionar información útil para un atacante.

Por ejemplo:

```text
Error:
SQL connection refused at 192.168.1.20:5432
```

El atacante obtiene información sobre:

* Dirección IP.
* Puerto.
* Tecnología.
* Arquitectura.
* Base de datos.
* Componentes internos.

Por eso los mensajes externos deben ser controlados.

---

# Caso relacionado con A10 – Excepciones y fail open

Un ejemplo relacionado con este tipo de riesgo se encuentra en vulnerabilidades donde una excepción no controlada puede provocar que una operación continúe cuando debería detenerse.
El caso de **pyOpenSSL** es útil como ejemplo conceptual de este patrón: una condición excepcional relacionada con una conexión podía provocar un comportamiento inseguro en lugar de producir un rechazo apropiado.

La lección principal es:

> Una excepción no debería cambiar accidentalmente una decisión de seguridad de "denegar" a "permitir".

Esto demuestra por qué el manejo de errores debe considerarse parte de la seguridad de la aplicación y no solamente de su estabilidad.

---

# Relación con CWE

A10 puede relacionarse con diferentes categorías de debilidades de software descritas en **CWE (Common Weakness Enumeration)**.

Entre los patrones relevantes se encuentran situaciones como:

* Manejo incorrecto de errores.
* Exposición de información mediante mensajes de error.
* Parámetros que no son correctamente validados.
* Condiciones de carrera.
* Comportamientos inseguros después de una excepción.

Esto demuestra que un error aparentemente técnico puede terminar convirtiéndose en un problema de seguridad.

---

# Prevención de A10

## 1. Manejar las excepciones correctamente

Las excepciones deben capturarse de forma específica.

Evitar patrones como:

```python
try:
    operacion()
except:
    pass
```

Es preferible manejar explícitamente las condiciones esperadas y registrar aquellas que requieran investigación.

---

## 2. Utilizar Fail Closed

Cuando ocurre un error durante una decisión de seguridad, la aplicación debería adoptar el comportamiento más seguro.

Ejemplo:

```text
Error al validar autorización
           ↓
       DENEGAR
           ↓
Registrar evento
```

No:

```text
Error al validar autorización
           ↓
       PERMITIR
```

---

## 3. Validar entradas

Las aplicaciones deberían validar:

* Tipo de dato.
* Longitud.
* Formato.
* Rango.
* Valores permitidos.
* Campos obligatorios.

Ejemplo:

```text
ID esperado: entero positivo

ID = 25      → ✔ válido
ID = -5      → ❌ rechazado
ID = "abc"   → ❌ rechazado
ID = NULL    → ❌ rechazado
```

---

## 4. Evitar información sensible en mensajes

Los usuarios no deberían recibir detalles internos de la aplicación.

### Incorrecto

```text
Traceback:
File "/app/database.py"
Line 82
Connection refused
10.10.10.25:5432
```

### Correcto

```text
No fue posible procesar la solicitud.
Código de referencia: ERR-92831
```

Los detalles técnicos pueden mantenerse en los logs internos.

---

## 5. Pruebas negativas

Las pruebas no deberían limitarse a verificar que todo funciona correctamente.
También deben comprobar qué ocurre cuando algo sale mal.

Ejemplos:

```text
¿Qué sucede si falta un parámetro?

¿Qué sucede si el usuario no tiene permisos?

¿Qué sucede si la base de datos no responde?

¿Qué sucede si llega un valor inesperado?

¿Qué sucede si dos solicitudes llegan simultáneamente?

¿Qué sucede si ocurre una excepción durante una validación?
```

---

## 6. Pruebas automatizadas

Los casos excepcionales deberían formar parte de las pruebas automatizadas.

Ejemplo conceptual:

```text
Test normal
     ↓
Solicitud válida
     ↓
Respuesta esperada
```

Y también:

```text
Test negativo
     ↓
Solicitud inválida
     ↓
Aplicación rechaza correctamente
```

---

## 7. Revisar condiciones de carrera

Las operaciones críticas deben diseñarse teniendo en cuenta la concurrencia.

Especialmente en:

* Transacciones.
* Pagos.
* Cambios de permisos.
* Creación de recursos.
* Inventarios.
* Procesamiento de sesiones.
* Operaciones financieras.

---

# A09 vs A10

| Categoría          | A09                        | A10                          |
| ------------------ | -------------------------- | ---------------------------- |
| Problema principal | Falta de visibilidad       | Manejo inseguro de errores   |
| Riesgo             | Ataques no detectados      | Errores que generan bypass   |
| Ejemplo            | No registrar login fallido | Excepción permite continuar  |
| Impacto            | Detección tardía           | Comportamiento inseguro      |
| Control principal  | Logging y alertas          | Manejo seguro de excepciones |
| Concepto clave     | Monitoreo                  | Fail Closed                  |
| Pruebas            | Detección de eventos       | Pruebas negativas            |
| DevSecOps          | Observabilidad y respuesta | Seguridad durante errores    |

---
