# One image, several hosts.
#
# Hugging Face Spaces runs containers as uid 1000 and proxies to port 7860 by
# default; Render and Fly inject $PORT and do not care about the user. Building
# for the stricter of the two costs nothing and means the same image deploys
# anywhere without a fork.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dependencies first, as root, so they land in system site-packages and the
# layer caches across code changes.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Everything from here runs as uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user app ./app
COPY --chown=user web ./web
COPY --chown=user knowledge ./knowledge
COPY --chown=user scripts ./scripts

# SQLite lives under the app user's home so it is writable without a chown, and
# on a volume where one is available. Free tiers have no disk, which is what
# SEED_ON_START is for.
ENV DB_PATH=/home/user/app/data/app.db
RUN mkdir -p /home/user/app/data

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os,httpx,sys; p=os.getenv('PORT','7860'); sys.exit(0 if httpx.get(f'http://127.0.0.1:{p}/api/health').status_code==200 else 1)"

# Shell form so $PORT from Render / Fly is picked up, defaulting to the port
# Hugging Face expects.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
