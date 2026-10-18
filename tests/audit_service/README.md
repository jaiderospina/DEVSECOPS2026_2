# Pruebas automatizadas de Audit Service

Estas pruebas validan la lógica principal de
`servicios/audit-service` sin modificar datos reales.

## Alcance

- Sanitización defensiva de campos sensibles.
- Sanitización de estructuras anidadas.
- Objetos no soportados.
- Modelo Pydantic estricto.
- Timestamp con zona horaria.
- Autenticación interna.
- Inserción de eventos.
- Idempotencia mediante evento_uuid.
- Límite de tamaño de detalle.
- Manejo seguro de errores de PostgreSQL.
- Healthcheck.

Las pruebas utilizan variables ficticias y un engine simulado.

No requieren conexión a PostgreSQL, Identity Service ni Internet.

## Ejecución

Desde la raíz del proyecto:

```powershell
docker run --rm `
    --network none `
    -v "${PWD}:/workspace:ro" `
    -w /workspace `
    prueba-proyectofinal-audit-service `
    python -m unittest discover `
        -s tests/audit_service `
        -p "test_*.py" `
        -v
```
