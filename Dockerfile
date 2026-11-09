# Image unique pour le web et le worker (même code, commande différente).
FROM python:3.15-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# ffmpeg : conversion et durée des enregistrements ; libmagic : vrai type MIME des uploads.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libmagic1 curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# CSS Tailwind compilé et fichiers statiques collectés au build (pas au démarrage).
RUN DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py tailwind build \
 && DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app && mkdir -p /app/media && chown -R app /app/media
USER app

ENV DJANGO_SETTINGS_MODULE=config.settings.prod PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD curl -fsS "http://localhost:${PORT}/health" || exit 1

CMD ["scripts/start.sh", "web"]
