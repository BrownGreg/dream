# Raccourcis du projet. `make help` liste les cibles.
.DEFAULT_GOAL := help
.PHONY: help setup dev down test e2e lint fmt load worker run rapport postmortem code-review eisvogel rendu

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

EV = $(CURDIR)/docs/templates/eisvogel
EISVOGEL = pandoc --metadata-file=$(EV)/commun.yaml --template=$(EV)/eisvogel.latex \
	--lua-filter=$(EV)/liens_locaux.lua --pdf-engine=xelatex

rapport: ## Rapport de production (Eisvogel) : docs/rapport/rapport_hery.pdf
	plantuml -tsvg docs/diagrams/coupe_circuit.puml
	for d in c4_container sequence_reve; do rsvg-convert -f pdf -o docs/rapport/$$d.pdf docs/diagrams/$$d.svg; done
	cd docs/rapport && $(EISVOGEL) rapport.md --metadata-file=metadata.yaml -o rapport_hery.pdf
	rm -f docs/rapport/c4_container.pdf docs/rapport/sequence_reve.pdf

postmortem: ## Post-mortem (Eisvogel) : docs/postmortem/postmortem_gregory.pdf
	cd docs/postmortem && $(EISVOGEL) postmortem.md --metadata-file=metadata.yaml -o postmortem_gregory.pdf

code-review: ## Dossier de code review (Eisvogel) : docs/code-review/dossier_code_review.pdf
	cd docs/code-review && $(EISVOGEL) README.md 01-bug-mediarecorder.md 02-bug-file-de-taches.md \
		03-story-client-resilient.md questions.md --metadata-file=metadata.yaml -o dossier_code_review.pdf

eisvogel: ## Dossiers du bloc 1 en rendu Eisvogel (pandoc + xelatex), en parallèle des versions Typst
	cd docs/preprod/livrables/_dossier_cadrage && $(EISVOGEL) body.md \
		--metadata-file=../_dossier_cadrage_eisvogel/metadata.yaml -o ../dossier_cadrage_eisvogel.pdf
	cp docs/preprod/diagrams/excalidraw/sequence_reve.png docs/preprod/diagrams/excalidraw/c4_container.png docs/preprod/livrables/_specifications_architecture/
	cd docs/preprod/livrables/_specifications_architecture && $(EISVOGEL) body.md \
		--metadata-file=../_specifications_architecture_eisvogel/metadata.yaml -o ../specifications_architecture_eisvogel.pdf
	rm -f docs/preprod/livrables/_specifications_architecture/sequence_reve.png docs/preprod/livrables/_specifications_architecture/c4_container.png

rendu: ## Dossiers de rendu pré-production et production (PDF régénérés + annexes + ZIP) dans rendu/, hors Git
	uv run python scripts/build_rendu.py
