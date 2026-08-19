FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY web ./web
COPY knowledge ./knowledge
COPY scripts ./scripts

# SQLite lives on a volume so the index and leads survive a redeploy.
ENV DB_PATH=/srv/data/app.db
RUN mkdir -p /srv/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import os,httpx,sys; p=os.getenv('PORT','8000'); sys.exit(0 if httpx.get(f'http://127.0.0.1:{p}/api/health').status_code==200 else 1)"

# Shell form so $PORT from Render / Railway / Fly is picked up automatically.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
