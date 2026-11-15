# Backlog de production

`jira_production.csv` : les 24 tickets de production, numérotés **DREAM-1 à DREAM-24** dans le dépôt (branches, commits, PR). La description de chaque ticket rappelle les stories `US-xx` du bloc 1 ([`../preprod/backlog/stories.toml`](../preprod/backlog/stories.toml)).

## Correspondance avec Jira

Le CSV supposait un projet Jira vide, où l'import aurait attribué les clés DREAM-1 à DREAM-24. Or le projet **DREAM** contenait déjà le backlog de pré-production (epics DREAM-1 à 5, stories DREAM-6 à 26, tâches de la maquette DREAM-27 à 39). Les tickets de production y ont été créés le 15/11/2026 sous d'autres clés, sans renommer les branches déjà fusionnées : **une référence `DREAM-n` dans Git désigne la ligne n du CSV, pas la clé Jira `DREAM-n`**. Chaque ticket Jira rappelle sa « référence dépôt » dans sa description.

Suivi : <https://gregoryyazidi.atlassian.net/jira/software/projects/DREAM/boards/2>, sprint « Production » (09/11/2026 → 15/11/2026), epic **DREAM-41**.

| Référence dépôt | Clé Jira | Ticket |
|---|---|---|
| DREAM-1 | DREAM-42 | Socle Django 6 et authentification par e-mail |
| DREAM-2 | DREAM-43 | Pipeline CI/CD, Docker Compose et Blueprint Render |
| DREAM-3 | DREAM-44 | ADR d'évolution d'architecture et de budget |
| DREAM-4 | DREAM-45 | Modèles de données alignés sur l'ERD du bloc 1 |
| DREAM-5 | DREAM-46 | Client résilient, journal ApiCall et coupe-circuit budget |
| DREAM-6 | DREAM-47 | Enregistrement micro et import audio validés |
| DREAM-7 | DREAM-48 | Transcription Voxtral avec adapter fake |
| DREAM-8 | DREAM-49 | Classification d'émotion HF → Mistral → lexique |
| DREAM-9 | DREAM-50 | Prompt visuel et image FLUX.2 [klein] |
| DREAM-10 | DREAM-51 | Tâche process_dream idempotente et suivi HTMX |
| DREAM-11 | DREAM-52 | Historique paginé et filtres date + humeur |
| DREAM-12 | DREAM-53 | Statistiques du tableau de bord (Chart.js) |
| DREAM-13 | DREAM-54 | Détail d'un rêve : corriger, régénérer, supprimer |
| DREAM-14 | DREAM-55 | Export JSON et suppression du compte |
| DREAM-15 | DREAM-56 | Ambiance sonore selon l'émotion (bonus) |
| DREAM-16 | DREAM-57 | Accessibilité et mobile d'abord |
| DREAM-17 | DREAM-58 | Observabilité : structlog, Sentry, /health worker, /ops |
| DREAM-18 | DREAM-59 | Stratégie de tests et tests d'intégration VCR |
| DREAM-19 | DREAM-60 | Parcours E2E Playwright avec micro simulé |
| DREAM-20 | DREAM-61 | Test de charge Locust 5 → 20 → 50 utilisateurs |
| DREAM-21 | DREAM-62 | Mesures de performance contre les SLO |
| DREAM-22 | DREAM-63 | README, schémas C4 et séquence mis à jour |
| DREAM-23 | DREAM-64 | Rapport de production et matière du post-mortem |
| DREAM-24 | DREAM-65 | Dossier de code review et conformité |

Bugs, rattachés à l'epic DREAM-41 :

| Clé Jira | Bug | Référence dépôt |
|---|---|---|
| DREAM-66 | Enregistrement micro refusé sous Chrome et Firefox (incident n° 9) | DREAM-19, corrige DREAM-6 |
| DREAM-67 | Installation neuve en échec : `DATABASE_URL` vide (incident n° 12, PR #31) | DREAM-24, corrige DREAM-1 |
| DREAM-40 | Les rêves en échec côté fournisseur consomment le quota quotidien (PR #34) | DREAM-5 |

Les tâches de la maquette prévues pour l'ancienne architecture (DREAM-29 à 37 : FastAPI, Arq, Redis, S3) sont closes avec un commentaire d'abandon renvoyant à l'[ADR-008](../decisions/ADR-008-evolution-architecture-production.md) ; Jira n'offrant pas de statut « Abandonné », elles apparaissent « Terminé ».
