# Producción simulada

[compose.simulated.json](compose.simulated.json) es una especificación Docker Compose en JSON (formato YAML compatible), separada del Compose de desarrollo. Usa imágenes ya publicadas 1.0.0 por digest, sin builds ni código montado. PostgreSQL 17 también se fija por digest; el servicio histórico usuarios no se ejecuta en el alcance actual.

Ocho servicios permanentes: PostgreSQL, Identity, Permissions, Audit, Sync Worker, Audit Dispatcher, frontend y grilla. `bootstrap-admin` es un perfil puntual opcional. PostgreSQL utiliza una red interna y volumen propio; no publica puerto. Los puertos de aplicaciones se enlazan exclusivamente a 127.0.0.1 (5173, 5176, 8003, 8004, 8005). Todos los servicios tienen raíz de solo lectura, tmpfs, capacidades retiradas, no-new-privileges, límites de procesos/memoria y rotación de logs.

Ansible instala el manifiesto, `.env` y `postgres-init` en un directorio privado. Consulte [las instrucciones](../infraestructura/README.md). No ejecute esta configuración contra el volumen de desarrollo: usa otro proyecto/destino. Los secretos y datos quedan fuera de Git.

Para acceder desde otro equipo use túneles SSH de los puertos de frontend, Identity, Permissions y grilla. Esta simulación local usa HTTP y no implementa dominio, certificados, balanceo o alta disponibilidad. Para una exposición pública se necesita TLS y adaptar los orígenes/CSP compilados del frontend; variables runtime no reconstruyen Vite. La inactividad de cinco minutos se conserva en la imagen 1.0.0 y en la configuración backend.

Fuentes: [Compose services](https://docs.docker.com/reference/compose-file/services/) y [variables requeridas/interpolación](https://docs.docker.com/reference/compose-file/interpolation/).

## Evidencia de ejecución

[Run 37578596462](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37578596462): 29/29 trabajos aprobados. Ocho contenedores no root, cinco sondas HTTP 200, tres puertas de autenticación 401 y datos conservados al recrear PostgreSQL. [Resumen duradero](../docs/evidencias/2026-10-07/ANSIBLE_CD_37578596462.json). PR #3 sigue sin integrar; SMTP real, segundo PC y ZAP automatizado mantienen sus pendientes.
