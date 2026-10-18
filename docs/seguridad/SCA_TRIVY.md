# SCA de dependencias con Trivy

Revisado: 14 de octubre de 2026. [E29: cobertura CI y Quality Gate](../evidencias/2026-10-14/sonar-cobertura-ci/README.md): **f87243e, CI 31/31 y Quality Gate passed**. Cobertura nueva Sonar **88,1 %**, mínimo 80 %; cobertura global Sonar **54,5 %**. XML Python y LCOV generados en la misma ejecución; 26 controles DAST, 11 SCA y 21 de automatización. Las instalaciones nuevas usan wheels con hashes y locks, y el CI directo del espejo exige el Quality Gate. Los cortes E25/E27 son históricos; los riesgos STRIDE, la release 1.0.0 y los alcances GET-only conservan sus límites. E11/E14/E24 conservan inventarios y conteos de sus ejecuciones; no se declara resuelto el bloqueo histórico por facturación del principal.


Implementación integrada en master mediante el PR #3. El historial que sigue conserva el alcance de cada ejecución; E24 añade CI aprobado en el espejo sobre 8262da2. Validación registrada: [E11](../evidencias/2026-10-07/SCA_TRIVY_20261007.json). Ocho manifiestos locales (121 ocurrencias de paquetes) y seis jobs Python de CI (98 ocurrencias) sin hallazgos; fixture vulnerable rechazada y ocho regresiones locales aprobadas. La revisión final 73154a4 no pudo iniciar jobs por facturación/límite de GitHub Actions; no se acredita CI integral aprobado para esa revisión.

## Alcance y política

Trivy 0.65.0 ejecuta filesystem SCA sobre los siete requirements.txt versionados (seis servicios y Ansible/Checkov) y package-lock.json del frontend, además de los dos requirements-ci.lock de Ansible y carga Excel (diez manifiestos). El staging contiene solo manifiestos; copia package.json para comprobar coherencia con el lock. Se normalizan UTF-8/BOM y UTF-16/BOM a UTF-8 en el staging, sin editar los manifiestos originales; se conservan hashes de origen y de entrada.

Cada uno de los seis jobs SCA Python resuelve además su requirements en un venv limpio con Python 3.14 y genera un listado pip freeze. Trivy analiza ese listado con todas las versiones resueltas, incluidas transitivas y extras. Es una resolución del momento, no un nuevo lockfile versionado ni una equivalencia con cada imagen 1.0.0 ya publicada.

El frontend se analiza desde package-lock.json, con --include-dev-deps. No se ejecutan scripts npm ni se instala la dependencia de la fixture negativa. La infraestructura se escanea desde sus pins directos y el nuevo lock completo de CI (97 distribuciones); el lock de carga contiene 41. Para Trivy, los pins de los locks se copian a ci-lock/requirements.txt en staging después de validar los hashes SHA-256, sin modificar los archivos originales. pip verifica esos hashes durante la instalación.

Los informes JSON conservan todos los niveles de severidad y el inventario (--list-all-pkgs). El verificador exige los paquetes/versiones esperados en cada resultado de tipo pip/npm; un escaneo vacío o incompleto falla. El gate bloquea HIGH/CRITICAL, incluidas vulnerabilidades sin corrección. LOW/MEDIUM/UNKNOWN se registran para revisión; no se suprimen CVEs ni se utiliza ignore-unfixed. Un error de Trivy también hace fallar el job.

pip-audit y npm audit permanecen como controles complementarios. El gate principal depende del nuevo job sca-trivy-manifests y de los seis SCA Python. Por workflow_call, el control también precede a una futura publicación/despliegue que reutilice CI.

## Evidencias y regresión del bloqueo

- sca-trivy-manifests conserva expected.json, trivy-manifests.json y summary.json.
- Cada artifact sca-SERVICIO conserva resolved-requirements.txt, trivy-expected.json, trivy-dependencies.json y trivy-summary.json junto a pip-audit.
- La fixture Django==2.2.0 se crea en RUNNER_TEMP, se escanea y no se instala. Se exige exit-code 1 de Trivy por HIGH/CRITICAL y salida 1 del verificador, con JSON de hallazgos y resumen.
- Once pruebas locales/CI comprueban inventario completo, faltante, versión incorrecta, extras/BOM, requisitos sin pin y política por severidad.
- Retención del nuevo artifact: 30 días. Conservar resumen e informes antes de expirar.

La ausencia de bloqueantes en este alcance no certifica DAST, secretos, seguridad de imágenes ni todos los paquetes de infraestructura. Esos controles tienen evidencia y estados separados.

## Referencias

[Filesystem Trivy](https://trivy.dev/docs/latest/target/filesystem/), [Python: requisitos resueltos](https://trivy.dev/docs/latest/coverage/language/python/) y [Node: lockfiles y dependencias de desarrollo](https://trivy.dev/docs/latest/coverage/language/nodejs/).

## Bloqueo histórico de CI en el repositorio original

La captura de facturación aportada por el usuario muestra 2.000/2.000 minutos incluidos consumidos, $0 facturable y reinicio de cuota en 25 días. Los $12 de consumo están compensados por descuentos; no se acredita deuda. No se habilitó consumo de pago. Repetir CI de la revisión vigente cuando Actions disponga de cuota.

## Límites de archivos y registros

El verificador endurecido en ef41394 limita entradas resueltas, informes y staging a reports/ del checkout o RUNNER_TEMP. Los manifiestos originales se leen dentro del checkout o de un árbol de prueba de RUNNER_TEMP; se rechazan traversal y enlaces simbólicos. Los informes se reemplazan de forma atómica. Un inventario inválido no se copia al staging ni se imprime en el error. [E12](../evidencias/2026-10-07/SONAR_LOCAL_FIXES_20261007.json) conserva las regresiones y la revalidación de E11; SonarCloud quedó pendiente en ese corte; el CI de 8262da2 se aprobó posteriormente en el espejo, E24.

## Validación de los locks de CI

[E14](../evidencias/2026-10-07/SONAR_SECURITY_CI_20261007.json): diez manifiestos, 259 ocurrencias de paquetes detectadas y 199 requeridas verificadas; cero HIGH/CRITICAL y tres MEDIUM registrados. Las dos instalaciones offline pasaron con hashes y pip check; un hash alterado fue rechazado. Se sustituyó Checkov 3.3.25 por 3.2.506 para eliminar su dependencia ecdsa afectada por CVE-2024-23342. Se verificaron los mismos controles Ansible y su bloqueo negativo. No se añadieron ignorados ni se debilitó el gate. Ese corte no acreditó CI integral ni SonarCloud; E24 documenta la posterior aprobación CI de 8262da2 en el espejo, manteniendo SonarCloud pendiente.


## Validación CI posterior — 13 de octubre de 2026

[E24: CI/CD del espejo](../evidencias/2026-10-13/ci-espejo/README.md): sca-trivy-manifests y los seis sca-python aprobaron en el espejo para 8262da2. El resumen preservado confirma diez manifiestos, dos MEDIUM y cero bloqueantes HIGH/CRITICAL, sin CVEs ignoradas. La fixture vulnerable negativa y el verificador se mantienen en el workflow aprobado. El hallazgo transitivo de ply indicado por Snyk para tooling no se considera resuelto por aprobar Trivy; las herramientas tienen alcances distintos. SonarCloud no forma parte de esa aprobación.


## Cierre SonarCloud del espejo — 13 de octubre de 2026

[E25: SonarCloud del espejo](../evidencias/2026-10-13/sonar-espejo/README.md): workflow CI de f026d19 aprobado (29/29), incluido el análisis real, y check externo **Quality Gate passed** para el proyecto del espejo. El check informa 45 issues nuevos y 0 % de cobertura de código nuevo; esta métrica no sustituye el 69 % local. Las notas E24/anteriores conservan sus cortes históricos. El resultado no acredita una nueva publicación/deploy Docker, elimina los riesgos residuales ni valida automáticamente posteriores commits.

## Lock de cobertura y suministro de dependencias CI

Se incluye `tests/coverage/requirements-ci.lock` en el inventario Trivy, con las mismas barreras de staging y gate HIGH/CRITICAL. Coverage 7.16.2 se instala como wheel con hashes oficiales; el lock compartido de pruebas conserva los pins directos de cinco servicios. Los locks pertenecen al entorno de pruebas y no alteran las dependencias runtime ni eliminan los hallazgos residuales del tooling.
