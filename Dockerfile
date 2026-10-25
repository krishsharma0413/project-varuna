# Images for the api, worker and logger services (different commands in docker-compose.yml).
# Slow-changing layers (system packages, Python deps, Chromium) come before the app code, so a code
# change only rebuilds the last few layers.

FROM python:3.13-slim AS base
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN useradd --create-home --uid 1000 varuna \
    && mkdir -p /data/logs /data/instaloader /tmp/varuna-jobs \
    && chown -R varuna:varuna /data /tmp/varuna-jobs

# api and logger
FROM base AS app
COPY main.py ./
COPY app ./app
COPY data ./data
COPY prompts.yaml ./
USER varuna
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# worker: adds headless Chromium for the last-resort Selenium search (kept out of api/logger)
FROM base AS worker
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
COPY main.py ./
COPY app ./app
COPY data ./data
COPY prompts.yaml ./
USER varuna
CMD ["python", "-m", "app.worker.main"]

# Test image: `docker build --target test -t varuna-test . && docker run --rm varuna-test`
FROM app AS test
USER root
RUN uv sync --frozen
COPY tests ./tests
COPY config.example.yaml ./
USER varuna
CMD ["pytest", "-q"]
