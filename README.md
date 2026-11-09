# Synthétiseur de rêves

Application web : vous racontez un rêve à voix haute au réveil ; l'application le transcrit, en déduit l'émotion dominante, génère une image onirique et range le tout dans un tableau de bord personnel.

> Projet individuel, bloc production. Les livrables de pré-production (cadrage, architecture, benchmark, maquette) sont dans [`docs/preprod/`](docs/preprod/).

## Installation en une commande

Prérequis : Python 3.12 et [uv](https://docs.astral.sh/uv/), **ou** Docker.

```bash
git clone https://github.com/BrownGreg/dream.git && cd dream
make setup                     # uv : .env, dépendances, CSS, migrations, superuser
# ou
./scripts/install.sh --docker  # Docker Compose : web + worker + PostgreSQL
```

Sans clé d'API, l'application fonctionne entièrement en mode `AI_MODE=fake` (adapters simulés).

## Lancement

| Commande | Effet |
|---|---|
| `make run` + `make worker` | Serveur de développement et worker de tâches, sans Docker |
| `make dev` | Pile Docker Compose complète sur http://localhost:8000 |
| `make test` | Tests, couverture globale et par fonctionnalité critique (seuil 70 %) |
| `make lint` | ruff (PEP 8, docstrings Google) et mypy strict |

## Variables d'environnement

Voir [`.env.example`](.env.example). Les secrets ne sont jamais commités : `.env` en local, variables de la plateforme en production.

## Intégration et déploiement continus

Chaque PR passe par [`ci.yml`](.github/workflows/ci.yml) : lint → types → migrations → tests sur PostgreSQL → couverture ≥ 70 % par fonctionnalité critique → construction de l'image et test de fumée de la pile Compose. Sur `main`, la CI déclenche ensuite le déploiement Render du commit testé ([`render.yaml`](render.yaml)) et vérifie `/health` en production.

## Organisation du dépôt

```
config/      réglages base/dev/test/prod, urls, /health
accounts/    inscription, connexion, consentements, RGPD
dreams/      rêves, pipeline IA, journal des appels API, budget
dashboard/   historique, filtres, statistiques, /ops
tests/       unit/ integration/ e2e/ load/
docs/        decisions/ (ADR), incidents.md, preprod/ (bloc 1)
```
