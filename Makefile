# Raccourcis du projet. `make help` liste les cibles.
.DEFAULT_GOAL := help
.PHONY: help setup dev down test e2e lint fmt load worker run rapport

help: ## Affiche cette aide
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

setup: ## Installation complète (uv ou Docker), .env, migrations, superuser
	./scripts/install.sh

dev: ## Lance web + worker + PostgreSQL avec Docker Compose
	docker compose up --build

down: ## Arrête la pile Docker Compose
	docker compose down

run: ## Lance le serveur de développement sans Docker
	uv run python manage.py tailwind build && uv run python manage.py runserver

worker: ## Lance le worker de tâches sans Docker
	uv run python manage.py db_worker

test: ## Tests + couverture globale et par fonctionnalité critique (≥ 70 %)
	uv run pytest --cov --cov-report=term-missing --cov-report=json --cov-fail-under=70
	uv run python scripts/check_coverage.py coverage.json

e2e: ## Tests navigateur (Playwright) : parcours et audit d'accessibilité
	uv run python manage.py tailwind build
	uv run pytest -m e2e -p no:cacheprovider

lint: ## ruff (lint + format) et mypy strict
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .

fmt: ## Corrige le format et les imports
	uv run ruff check --fix .
	uv run ruff format .

LOCUST_HOST ?= http://127.0.0.1:8000

load: ## Test de charge Locust (serveur et worker lancés à part, AI_MODE=fake, comptes seed_load_users)
	mkdir -p load-results
	uv run locust --config tests/load/locust.conf --host $(LOCUST_HOST)

rapport: ## Rapport PDF (pandoc + typst + plantuml) : docs/rapport/rapport_hery.pdf
	plantuml -tsvg docs/diagrams/coupe_circuit.puml
	pandoc docs/rapport/rapport.md -f markdown -t typst -o docs/rapport/body.typ
	typst compile --root . docs/rapport/main.typ docs/rapport/rapport_hery.pdf
