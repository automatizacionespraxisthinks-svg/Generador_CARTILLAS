# Generador de cartillas PRAXIS – THINKS · imagen para servidor (Dokploy / Docker)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # En Linux no hay Microsoft Word: se omiten el conteo de páginas y la maquetación con Word
    PRAXIS_SIN_WORD=1 \
    # La base SQLite vive en un volumen para que no se pierda al redesplegar
    PRAXIS_DATOS=/data \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY plantillas ./plantillas
COPY docs ./docs

# Usuario sin privilegios; /data queda con su dueño para que el volumen nombrado herede los permisos
RUN useradd --uid 1000 --create-home praxis \
 && mkdir -p /data \
 && chown -R praxis:praxis /data /app
USER praxis

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/salud', timeout=4)" || exit 1

# Un solo proceso: SQLite no admite varios escritores a la vez
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*' --workers 1"]
