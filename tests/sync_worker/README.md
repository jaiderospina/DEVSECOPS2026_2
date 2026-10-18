# Pruebas automatizadas del Sync Worker

Estas pruebas cubren la lógica principal de `servicios/sync-service` sin modificar datos reales.

## Alcance

- Configuración del Worker.
- Validación de identidad y compañía objetivo.
- Operaciones soportadas por el conector simulado.
- Reclamación de jobs y `FOR UPDATE SKIP LOCKED`.
- Finalización segura por `worker_id`.
- Reintentos y transición a `FALLIDO`.
- Recuperación de trabajos interrumpidos.
- Manejo seguro de errores inesperados.
- Reintento de conexión a PostgreSQL.
- Apagado controlado.

La concurrencia real con dos Workers se valida por separado mediante la prueba Docker de integración ya ejecutada.

## Ejecutar con la imagen Docker existente

Desde la raíz del proyecto, en PowerShell:

```powershell
docker run --rm `
    --network none `
    -v "${PWD}:/workspace:ro" `
    -w /workspace `
    prueba-proyectofinal-sync-worker `
    python -m unittest discover `
        -s tests/sync_worker `
        -p "test_*.py" `
        -v
```

Las pruebas usan variables ficticias dentro del proceso de test y reemplazan el `engine` por objetos fake. No requieren conexión a PostgreSQL y no alteran `sync_jobs`.

## Ejecutar con Python local

Solo si el entorno local ya tiene instaladas las dependencias de `servicios/sync-service/requirements.txt`:

```powershell
python -m unittest discover -s tests/sync_worker -p "test_*.py" -v
```
