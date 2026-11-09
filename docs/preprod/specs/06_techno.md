# 6. Justification technologique

## Bibliothèques Python retenues et écartées
| Besoin | Retenue | Écartée (raison) |
|---|---|---|
| Modèles, validation, schéma JSON | **Pydantic 2** : une classe = validation + schéma généré | dataclasses + jsonschema (deux définitions à maintenir) |
| API | **FastAPI** : OpenAPI générée depuis Pydantic, async natif | Django REST (ORM et admin inutiles ici), Flask (validation à ajouter) |
| Accès base | **SQLAlchemy 2 + Alembic** (migrations versionnées) | ORM Django (couplé au framework) |
| File de tâches | **Arq** sur Redis : async comme httpx, idempotence par `job_id`, tâches planifiées incluses | Celery (synchrone, configuration lourde), RQ (pas d'async) |
| Appels HTTP | **httpx** async + **tenacity** (retries comptés) | SDK de chaque fournisseur (quatre styles d'erreur, dépendances lourdes ; gardés seulement pour le prototypage) |
| Maquette | **Streamlit ≥ 1.40** : `st.audio_input` stable | Streamlit 1.35 du sujet (pas d'enregistrement micro natif stable) |
| Tests | **pytest**, pytest-bdd (Gherkin), pytest-cov, respx (mock httpx), hypothesis (validation audio), `streamlit.testing.v1.AppTest`, Locust (charge) | unittest (verbeux), Selenium pour l'UI (lent, fragile) |
| Qualité | **ruff** (lint + format + docstrings Google), **mypy --strict** | flake8 + black + isort (trois outils pour un) |
| Benchmark | openpyxl (formules vivantes), jiwer (WER) | pandas → Excel (valeurs figées) |
| Observabilité | structlog (JSON), OpenTelemetry, Sentry, Langfuse auto-hébergé UE | traçage IA SaaS hors UE |

## Pipeline CI/CD (GitHub Actions)
`.github/workflows/ci.yml`, sur chaque pull request et sur `main` :
1. `ruff check` et `ruff format --check` ;
2. `mypy --strict src` ;
3. `python tools/backlog.py --check` et `python tools/export_schema.py --check` (backlog cohérent, schéma à jour) ;
4. `pytest --cov=src --cov-fail-under=80` (unitaires, intégration avec mocks, scénarios BDD, AppTest) ;
5. construction de l'image Docker de l'API et du worker, scan des dépendances (`pip-audit`) ;
6. sur `main` uniquement : déploiement en préproduction, test de fumée, puis promotion manuelle en production (environnement protégé).
La protection de branche exige une CI verte et une relecture (section 8 du dossier de cadrage).

## Monitoring
- **Logs structurés** JSON (structlog) : `request_id`, `user_pseudonym`, étape, durée ; filtre qui rejette tout champ `text`, `transcription`, `prompt` — testé (ENF-10).
- **Traces** OpenTelemetry API → file → worker → fournisseur ; un span par appel IA avec fournisseur, modèle, latence, retries, unités facturées et coût (alimente `api_calls` et les SLI d'ADR-006).
- **Erreurs** : Sentry, avec suppression des corps de requête.
- **Tableau de bord** : p95 par étape, taux d'échec, rejets du filtre de sécurité (K5), coût cumulé du mois.
- **Alertes** : p95 bout-en-bout > 30 s sur 1 h ; échecs > 2 % sur 24 h ; budget à 80 % puis 100 % (coupe-circuit automatique, ADR-007) ; fournisseur en erreur > 5 min.
