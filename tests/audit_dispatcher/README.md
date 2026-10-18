# Pruebas automatizadas del Audit Dispatcher

Estas pruebas validan la lógica principal de
`servicios/audit-dispatcher` sin modificar datos reales.

## Alcance

- Configuración del Dispatcher.
- Reclamación atómica de eventos.
- `FOR UPDATE SKIP LOCKED`.
- Cambio a estado PROCESANDO.
- Incremento de intentos.
- Finalización segura por `worker_id`.
- Reintentos y regreso a PENDIENTE.
- Transición a FALLIDO.
- Límite seguro de mensajes de error.
- Recuperación de trabajos interrumpidos.
- Entrega exitosa al Audit Service.
- Manejo de entrega fallida.
- Reintento de conexión a PostgreSQL.
- Apagado controlado.
- Cliente HTTP interno.
- Manejo seguro de errores HTTP y de red.

Las pruebas utilizan variables ficticias, un engine SQL simulado
y respuestas HTTP simuladas.

No requieren conexión a PostgreSQL, Audit Service ni Internet.

## Ejecución

Desde la raíz del proyecto:

```powershell
docker run --rm `
    --network none `
    -v "${PWD}:/workspace:ro" `
    -w /workspace `
    prueba-proyectofinal-audit-dispatcher `
    python -m unittest discover `
        -s tests/audit_dispatcher `
        -p "test_*.py" `
        -v
```

## Resultado validado

```text
Ran 19 tests
OK
```

La concurrencia real con dos Dispatchers se validó adicionalmente
mediante una prueba Docker de integración con dos workers activos
simultáneamente.
