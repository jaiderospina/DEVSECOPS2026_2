# Infraestructura con Ansible

Controlador Linux/Python 3.12+, Docker y Compose v2. El playbook prepara el directorio, instala Docker opcionalmente en Ubuntu, copia el esquema, obtiene las imágenes inmutables 1.0.0, inicia los servicios y aplica las migraciones 11/12. Los secretos se renderizan con permisos 0600 y tareas `no_log`; no se incluyen en las evidencias.

## Ejecución en un host propio

Use una VM Ubuntu 24.04 o WSL2. Instale las dependencias del controlador:

```bash
python3 -m venv .venv-ansible
. .venv-ansible/bin/activate
python -m pip install -r infraestructura/ansible/requirements.txt
ansible-vault create ~/iam-vars.yml
```

En el archivo cifrado declare `iam_project_name: iam-demo`, `iam_deploy_dir: /opt/iam-demo` y los secretos `iam_postgres_password`, `iam_jwt_secret`, `iam_audit_token` (mínimo 32 caracteres) y `iam_mfa_key` (Fernet de 32 bytes en base64 URL-safe). Conserve esas claves para reinicios y actualizaciones; cambiarlas puede invalidar JWT o el descifrado de MFA.

Opcionales: `iam_install_docker: true` requiere sudo en Ubuntu; `iam_bootstrap_admin: true` y `iam_admin_password` crean exclusivamente el ADMIN_TI académico 1051, sin enviar correo. La contraseña debe cumplir la política del backend. Configure `iam_smtp_host`, `iam_smtp_port`, `iam_smtp_user`, `iam_smtp_password` e `iam_smtp_from` para operaciones que envían correo. El valor SMTP predeterminado es deliberadamente no operativo.

Copie y ajuste [el inventario](ansible/inventory.example.ini) para SSH o localhost. El usuario necesita acceso al daemon Docker y permisos sobre el directorio destino. Para /opt, puede ejecutar el playbook con `--become --ask-become-pass`; Docker equivale a acceso administrativo al host.

```bash
ansible-playbook -i infraestructura/ansible/inventory.example.ini infraestructura/ansible/deploy.yml --syntax-check
ansible-playbook -i infraestructura/ansible/inventory.example.ini infraestructura/ansible/deploy.yml --ask-vault-pass -e @~/iam-vars.yml
```

El despliegue normal conserva el volumen y nunca ejecuta `down --volumes`. Los scripts de inicialización solo corren automáticamente en una base nueva; Ansible aplica también las migraciones idempotentes 11/12. Use una base del alcance actual para actualizar desde un despliegue anterior y respalde los datos antes de cualquier actualización. No importa las cuentas del equipo de desarrollo ni genera el catálogo de correos.

## Validación y límites

[El workflow](../.github/workflows/deploy-simulated.yml) ejecuta CI, sintaxis Ansible, Checkov y un validador propio de Compose antes del despliegue. Checkov revisa los controles soportados para Ansible (apt sin paquetes no autenticados ni force); **no escanea Compose**. El validador propio exige digest, usuario no root por configuración, aislamiento, límites y secretos externos; sus nueve pruebas negativas comprueban el bloqueo.

El runner Linux crea un proyecto `iam-ci-RUN_ID-ATTEMPT` y secretos desechables fuera del checkout. Despliega con Ansible, verifica UID efectivo no root, estado y digest de ocho contenedores, HTTP y puertas de autenticación, tablas y un ADMIN_TI. Una segunda ejecución debe registrar `changed=0`. Recrea PostgreSQL y comprueba que el administrador y esquema siguen presentes. La limpieza borra exclusivamente ese volumen efímero de CI. Los informes no contienen variables de entorno ni contraseñas.

La ejecución real quedó aprobada en el [run 37578596462](https://github.com/jeancarlosalmenarez8318-tech/DevSecOps-proyecto-Final/actions/runs/37578596462): 29/29 trabajos, segunda ejecución changed=0/failed=0 y persistencia después de recrear PostgreSQL. [Resumen e informes duraderos](../docs/evidencias/2026-10-07/ANSIBLE_CD_37578596462.json). La instalación opcional de Docker se omitió porque el runner ya lo tenía. La prueba no sustituye la carga de varios usuarios con correos reales (pendiente por solicitud del usuario), una instalación en otro PC, ZAP automatizado o TLS para una exposición pública.

Fuentes: [Ansible command](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/command_module.html), [template](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html), [políticas Checkov para Ansible](https://www.checkov.io/5.Policy%20Index/ansible.html).

## Límites de los scripts de automatización

Los scripts rechazan traversal, rutas fuera del alcance y enlaces simbólicos. Los informes se leen/escriben solo en reports/ del checkout o RUNNER_TEMP; la escritura JSON es atómica y no trunca el destino de un hardlink. El generador de secretos de CI exige un proyecto iam-ci-RUN_ID-ATTEMPT y crea exclusivamente un archivo 0600 dentro de RUNNER_TEMP.

El verificador permite únicamente inspect, la sonda id -u, la lectura de metadata de imágenes y las consultas PostgreSQL fijadas en código. Valida proyecto, IDs completos y directorios antes de ejecutar el binario Docker resuelto en PATH; no acepta otro ejecutable, subcomandos arbitrarios ni shell. La verificación de persistencia conserva su contrato, pero requiere informes dentro de reports/ o RUNNER_TEMP. Para un despliegue manual, el operador autoriza exactamente un directorio existente mediante IAM_DEPLOY_DIR:

```bash
IAM_DEPLOY_DIR=/opt/iam-demo python infraestructura/scripts/verify_deployment.py --deploy-dir /opt/iam-demo --project iam-demo --report reports/deployment/manual.json
```

Compose y .env son 0600 y el directorio de despliegue es 0700. Los scripts SQL son 0640 y su directorio 0750: solo el operador y su grupo pueden leerlos. Ansible obtiene el grupo primario del operador y PostgreSQL lo recibe mediante group_add/IAM_SQL_READ_GID. Si el operador usa GID 0, se usa el grupo PostgreSQL 999. No se requiere sudo para un operador no root con permisos en su directorio. La prueba real con UID/GID 1000 confirmó inicialización de los doce SQL por PostgreSQL no root y denegó lectura al UID 1001; la segunda preparación Ansible registró changed=0. [E14](../docs/evidencias/2026-10-07/SONAR_SECURITY_CI_20261007.json).

## Dependencias reproducibles de CI

Los dos pasos Ansible instalan requirements-ci.lock exclusivamente como wheels con --only-binary :all: y --require-hashes. El lock fija 97 distribuciones para CPython 3.12/Linux x86_64; el de tests/bulk_users fija 41 para CPython 3.14/Linux x86_64. Son específicos de esos runners. Para regenerarlos, resolver los requirements directos en un entorno limpio de la misma plataforma, descargar solo wheels, fijar cada distribución transitiva y su SHA-256, comprobar pip check y repetir SCA y regresiones antes de publicar. No reutilizar estos hashes en otro sistema o ABI.

Checkov queda fijado en 3.2.506 porque 3.3.25 instala ecdsa, afectado por [CVE-2024-23342 sin corrección publicada](https://github.com/advisories/GHSA-wj6h-64fc-37mp). La versión seleccionada se descargó de PyPI y conserva CKV_ANSIBLE_5/6: dos aprobados, cero omitidos y fixture insegura rechazada. Trivy analiza también todas las dependencias de ambos locks y conserva su política HIGH/CRITICAL, sin excluir esa CVE.

El job de carga genera una contraseña PostgreSQL de 32 bytes aleatorios por ejecución, la enmascara antes de exportarla mediante GITHUB_ENV y elimina su contenedor al terminar. Las 51 pruebas de carga pasaron con PostgreSQL real y SMTP simulado. Ninguna contraseña se incorpora a las evidencias. Esto no repite el despliegue completo histórico de ocho contenedores ni valida correo real.

