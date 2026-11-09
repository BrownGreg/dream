#!/usr/bin/env sh
# Démarrage du conteneur. Usage : start.sh web | worker | all
#   web    : migrations puis gunicorn
#   worker : worker django.tasks (db_worker)
#   all    : web + worker dans le même conteneur (offre gratuite Render, ADR-008)
set -eu

role="${1:-web}"

run_web() {
  python manage.py migrate --noinput
  exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout 30 \
    --access-logfile - \
    --forwarded-allow-ips "*"
}

case "$role" in
  web) run_web ;;
  worker) exec python manage.py db_worker ;;
  all)
    python manage.py migrate --noinput
    exec honcho -f Procfile start
    ;;
  *) echo "rôle inconnu : $role (web | worker | all)" >&2; exit 2 ;;
esac
