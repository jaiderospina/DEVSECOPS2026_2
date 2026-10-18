FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --disable-pip-version-check \
    -r requirements.txt

COPY *.py ./

# El dispatcher no requiere privilegios root.
RUN adduser \
        --system \
        --group \
        --home /app \
        --shell /usr/sbin/nologin \
        auditdispatcher \
    && chown -R auditdispatcher:auditdispatcher /app

USER auditdispatcher

CMD ["python", "main.py"]
