# ============================================================
# IAM SECURE - AUDIT SERVICE
# ============================================================

FROM python:3.14-slim

# Evita archivos .pyc y fuerza salida inmediata de logs.
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
# CÓDIGO DEL MICROSERVICIO
# ============================================================

COPY database.py .
COPY seguridad.py .
COPY http_headers.py .
COPY main.py .


# ============================================================
# SEGURIDAD DEL CONTENEDOR
# ============================================================
# Audit Service se ejecuta sin privilegios root.
# ============================================================

RUN adduser \
        --system \
        --group \
        --home /app \
        --shell /usr/sbin/nologin \
        audituser \
    && chown -R audituser:audituser /app

USER audituser


# ============================================================
# PUERTO INTERNO
# ============================================================

EXPOSE 8004


# ============================================================
# INICIO
# ============================================================

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]