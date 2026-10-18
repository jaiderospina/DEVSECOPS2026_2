FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ============================================================
# DEPENDENCIAS
# ============================================================

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --disable-pip-version-check \
    -r requirements.txt

# ============================================================
# CÓDIGO DEL SYNC WORKER
# ============================================================

COPY database.py .
COPY main.py .

# ============================================================
# SEGURIDAD DEL CONTENEDOR
# ============================================================
# El worker se ejecuta con un usuario sin privilegios.
# ============================================================

RUN adduser \
        --system \
        --group \
        --home /app \
        --shell /usr/sbin/nologin \
        syncworker \
    && chown -R syncworker:syncworker /app

USER syncworker

# ============================================================
# EJECUCIÓN
# ============================================================
# El Sync Worker no expone ningún puerto HTTP.
# ============================================================

CMD ["python", "main.py"]
