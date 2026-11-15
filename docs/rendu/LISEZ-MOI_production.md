---
title: "Rendu — Production (bloc 3)"
subtitle: "Synthétiseur de rêves"
header-left: "Rendu production"
titlepage: false
toc: false
---

# Accès

| | |
|---|---|
| Code source (rendu du code) | [github.com/BrownGreg/dream](https://github.com/BrownGreg/dream) |
| Application en production | [dreamsynth.onrender.com](https://dreamsynth.onrender.com) |
| Intégration et déploiement continus | [GitHub Actions du dépôt](https://github.com/BrownGreg/dream/actions) |
| Suivi Jira (epic DREAM-41, sprint « Production ») | [Tableau Jira du projet DREAM](https://gregoryyazidi.atlassian.net/jira/software/projects/DREAM/boards/2) |

**Tester l'application.** Créer un compte sur <https://dreamsynth.onrender.com>, accepter le consentement « génération d'image », puis « Raconter un rêve ». L'offre gratuite de Render met l'instance en veille : la première visite peut prendre environ une minute. Le quota est de 5 rêves par jour et par compte.

**Installer en local.** `make setup` (uv ou Docker), puis `make run` et `make worker`, ou `make dev` (Docker Compose). Sans clé d'API, `AI_MODE=fake` fait tout fonctionner hors ligne. Données de démonstration : `DJANGO_DEBUG=true uv run python manage.py seed_demo`.

**Clés Jira.** Les branches et PR citent `DREAM-1` à `DREAM-24` ; dans Jira, ces tickets portent les clés DREAM-42 à 65 (le projet contenait déjà le backlog du bloc 1). Table complète : `annexes/backlog_jira.pdf`.

# État du dossier

{{ETAT}}

# Contenu

| Fichier | Livrable du sujet |
|---|---|
| `rapport_hery.pdf` | 3.2 Rapport technique ({{PAGES_RAPPORT}} pages) |
| `postmortem_gregory.pdf` | 3.3 Post-mortem individuel ({{PAGES_PM}} pages) |
| `dossier_code_review.pdf` | 3.4 Préparation de la code review live ({{PAGES_CR}} pages) |
| `annexes/` | conformité au sujet, journal des incidents, stratégie de tests, performance, correspondance Jira (PDF) ; mesures de production (JSON) ; schéma d'architecture (PNG) |

# Correspondance avec le sujet

## 3.1 Application fonctionnelle

| Fonctionnalité | Où |
|---|---|
| Authentification, espace utilisateur et historique | en production ; rapport §1 |
| Enregistrement audio (micro et import) | « Raconter un rêve » ; rapport §1, incident n° 9 |
| Transcription (Mistral Voxtral) | rapport §1 et §3, vérifiée en production |
| Classification émotionnelle (Hugging Face, repli Mistral, lexique) | rapport §1 et §3 |
| Génération d'image (FLUX.2) et ambiance sonore (bonus) | rapport §1 et §3 |
| Tableau de bord : filtres date et humeur, fréquences, émotions dominantes | « Mes rêves » et « Statistiques » ; rapport §1 |
| CI/CD : tests, lint, build, déploiement automatisé | `.github/workflows/ci.yml` ; rapport §4 ; déploiement Render vérifié par commit |
| README complet et script d'installation | `README.md`, `scripts/install.sh`, `.env.example` |

## 3.2 Rapport technique (`rapport_hery.pdf`)

| Exigence | Section |
|---|---|
| Architecture finale mise à jour | §2 (C4 conteneurs, séquence, ADR-008 à 010) |
| Gestion des appels API, quotas, erreurs | §3 (client résilient, coupe-circuit à 15 €, coût réel) |
| Stratégie de tests | §4 ; `annexes/strategie_tests.pdf` |
| Monitoring, journaux, métriques clés | §5 et §6 ; `annexes/performance.pdf` |
| Difficultés techniques et solutions | §7 (16 incidents) ; `annexes/incidents.pdf` |
| Répartition du travail, accès GitHub et Jira | §8 et bandeau d'accès |

## 3.3 Post-mortem (`postmortem_gregory.pdf`)

Chronologie, prévu et réalisé, incidents, métriques, statistiques Git et Jira (§1 à 5) ; auto-évaluation, points forts et faibles, améliorations, usage des outils (§6, rédigé par l'auteur).

## 3.4 Code review live (`dossier_code_review.pdf`)

Trois tickets résolus, avec diff commenté, méthode de debug, alternatives écartées et impact : enregistrement micro refusé (bug critique), file de tâches invisible (bug), client résilient et coupe-circuit (story) ; dix questions probables du jury.

## 4. Contraintes techniques

| Contrainte | Preuve |
|---|---|
| Python, Django | Django 6.0, Python 3.12 |
| Déploiement Render et Docker Compose | <https://dreamsynth.onrender.com> ; `docker-compose.yml`, `render.yaml` |
| Budget API ≤ 20 € | coupe-circuit à 15 € dans le code ; coût réel au 15/11/2026 : 0,019 $ (rapport §3.3) |
| Couverture ≥ 70 % des fonctionnalités critiques | 12 fonctionnalités entre 97,3 % et 100 %, contrôlées en CI (rapport §4.2) |
| PEP 8, docstrings Google, branches et PR | ruff et mypy strict en CI ; toutes les fusions sur `main` par PR avec CI verte |
