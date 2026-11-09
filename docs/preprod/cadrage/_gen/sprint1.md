<!-- Généré par tools/agile.py — ne pas éditer -->

**Objectif** : Un rêve raconté au micro, avec consentement, devient une transcription réelle (Voxtral) via l'API et le worker de l'architecture cible ; les premières latences et le WER sont mesurés.

**Capacité** : 25 h (5 jours × 5 h productives (hypothèse, travail individuel en parallèle des cours), dont 3,8 h de cérémonies ; le reste après tâches est une marge non planifiée). Planifié : 11 points, 18 h de tâches + 3,8 h de cérémonies ; marge 3,2 h.

| Story | Pts | Tâche technique | h |
|---|---|---|---|
| Socle technique | — | Projet FastAPI + Arq + Redis en docker compose, endpoint /healthz | 2 |
|  |  | PostgreSQL + Alembic : tables users, consents, dreams, audio_assets, transcriptions | 2 |
| US-03 Consentement explicite | 3 | PUT /v1/me/consents + historique horodaté (text_version) | 1,5 |
|  |  | Contrôle 403 consent_required avant toute tâche | 1 |
|  |  | Écran de consentement relié à l'API | 1 |
| US-01 Enregistrement micro | 3 | POST /v1/dreams multipart + validation (signature, taille, durée) | 2 |
|  |  | Dépôt S3 chiffré, clé aléatoire, 202 + status_url | 1,5 |
| US-04 Transcription réelle | 5 | Worker process_dream idempotent (verrou dream_id) | 2 |
|  |  | Adapter Voxtral branché, retries ×2, api_calls avec coût | 2 |
|  |  | Purge de l'audio après transcription + tâche 24 h | 1 |
|  |  | Campagne run_latency --live + WER sur le corpus | 1 |
| Actions du plan AIPD (1 et 2) | — | Opt-out d'entraînement Mistral (capture conservée) + demande ZDR | 0,5 |
|  |  | Demande DPA + opt-out écrit à BFL (R-03) | 0,5 |

**Cérémonies** : Sprint planning (Lundi 9 h, 1 h) → Objectif, stories engagées, tâches estimées · Point quotidien (solo) (Chaque matin, 10 min) → Journal : fait / à faire / blocage, burndown mis à jour · Affinage du backlog (Mercredi, 45 min) → Stories du Sprint 2 prêtes (DoR) · Revue de sprint (Vendredi 14 h, 45 min) → Démo au tuteur ou à un pair, retours notés dans le backlog · Rétrospective (Vendredi 15 h, 30 min) → 1 action d'amélioration pour le sprint suivant

**Reporté au Sprint 2** : US-08 Progression et erreurs (3 pts) ; US-02 Import de fichier (2 pts) ; US-06 Émotion (5 pts) ; CI : build Docker et pip-audit.
