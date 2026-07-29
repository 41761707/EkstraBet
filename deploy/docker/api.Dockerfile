# Produkcyjny obraz FastAPI — Python 3.11 slim, użytkownik bez roota.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UVICORN_WORKERS=2

RUN groupadd --system --gid 1000 ekstrabet \
    && useradd --system --uid 1000 --gid ekstrabet \
        --home-dir /app --shell /usr/sbin/nologin ekstrabet

WORKDIR /app

COPY requirements-vps.txt .
RUN pip install --no-cache-dir -r requirements-vps.txt

COPY api/ ./api/
COPY backend/ ./backend/

RUN chown -R ekstrabet:ekstrabet /app

USER ekstrabet

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5)"

# Bez --reload; ograniczona liczba workerów (UVICORN_WORKERS)
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]
