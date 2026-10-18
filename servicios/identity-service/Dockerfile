# ============================================================
# IAM SECURE - IDENTITY SERVICE
# ============================================================

FROM python:3.14-slim

# Evita archivos .pyc y permite visualizar inmediatamente
# los logs generados por Python.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app


# ============================================================
# DEPENDENCIAS
# ============================================================
# Se copian primero para aprovechar la caché de Docker.
# ============================================================

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --disable-pip-version-check \
    -r requirements.txt


# ============================================================
# CÓDIGO DEL IDENTITY SERVICE
# ============================================================
# Se copian todos los módulos Python del microservicio.
#
# Esto incluye, entre otros:
# - main.py
# - database.py
# - autenticacion.py
# - seguridad.py
# - usuarios.py
# - companias.py
# - mfa.py
# - auditoria.py
# - correo.py
# - sync_jobs.py
# - scripts bootstrap
#
# Los secretos NO se encuentran en estos archivos.
# Se reciben mediante variables de entorno.
# ============================================================

COPY *.py ./


# ============================================================
# SEGURIDAD DEL CONTENEDOR
# ============================================================
# El microservicio se ejecuta con un usuario sin privilegios.
# ============================================================

RUN useradd \
        --system \
        --create-home \
        --home-dir /home/appuser \
        --shell /usr/sbin/nologin \
        appuser \
    && chown -R appuser:appuser /app

USER appuser


# ============================================================
# PUERTO
# ============================================================

EXPOSE 8003


# ============================================================
# INICIO DEL MICROSERVICIO
# ============================================================

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]