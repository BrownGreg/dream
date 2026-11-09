#!/usr/bin/env bash
# Installation en une commande. Usage : ./scripts/install.sh [--docker]
#   sans option : environnement uv local (SQLite par défaut, AI_MODE=fake)
#   --docker    : pile Docker Compose (web + worker + PostgreSQL)
set -euo pipefail
cd "$(dirname "$0")/.."

info() { printf '\033[36m→ %s\033[0m\n' "$*"; }

if [[ ! -f .env ]]; then
  info "Création de .env depuis .env.example"
  cp .env.example .env
  secret=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
  sed -i.bak "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${secret}|" .env && rm -f .env.bak
fi

if [[ "${1:-}" == "--docker" ]]; then
  command -v docker >/dev/null || { echo "Docker introuvable. Installez Docker Desktop ou relancez sans --docker." >&2; exit 1; }
  info "Construction et démarrage de la pile Docker Compose"
  docker compose up --build -d
  info "Création d'un superuser (accès /admin et /ops)"
  docker compose exec web python manage.py createsuperuser
  info "Prêt : http://localhost:8000"
  exit 0
fi

command -v uv >/dev/null || { info "Installation de uv"; curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
info "Dépendances Python 3.12 (uv sync)"
uv sync
info "CSS Tailwind"
uv run python manage.py tailwind build
info "Migrations"
uv run python manage.py migrate
info "Création d'un superuser (accès /admin et /ops)"
uv run python manage.py createsuperuser || true
info "Prêt. Lancez « make run » et, dans un second terminal, « make worker »."
