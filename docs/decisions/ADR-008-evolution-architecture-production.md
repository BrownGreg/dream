# ADR-008 — Évolution : architecture de production Django monolithe + tâches en base

- **Statut** : accepté · 2026-11-09
- **Type** : Évolution (révise la cible des specs bloc 1 §1 et §6, ADR-003 pour l'émotion)
- **Liens** : `docs/preprod/specs/01_c4.md`, `docs/preprod/specs/06_techno.md`, ADR-003, ADR-006, ADR-007, ADR-009

## Contexte
L'architecture cible du bloc 1 prévoyait un front Streamlit puis Next.js, une API FastAPI, un worker Arq sur Redis, un stockage objet S3 et une connexion par lien magique. Le sujet de production impose Python, **Django**, une base SQL et Tailwind, un déploiement Heroku / Render / Docker Compose, et **6 jours** de réalisation pour une seule personne. Les fournisseurs IA retenus au bloc 1 (Mistral, BFL) ne changent pas.

## Décision
| Brique | Bloc 1 (cible) | Production (retenu) | Raison |
|---|---|---|---|
| Web + API | FastAPI + Streamlit → Next.js | **Django 6.0** monolithe, gabarits + **HTMX** + Tailwind | Imposé par le sujet ; un seul langage, un seul déploiement ; pas de SPA à maintenir |
| File de tâches | Arq + Redis | **`django.tasks`** (API native Django 6) + backend base de données **`django-tasks-db`**, commande `db_worker` | Django 6 fournit l'API mais aucun backend de production ; le backend en base évite un broker : une seule base, pas de Redis à payer ni à superviser. Le pipeline ne s'exécute jamais dans la requête HTTP |
| Suivi d'avancement | sondage du statut par le front | **Polling HTMX** toutes les 2 s sur `/dreams/<id>/status`, étapes visibles | Plus simple et plus robuste que des WebSockets, suffisant pour un traitement de ~30 s (ADR-006) |
| Authentification | lien magique | **E-mail + mot de passe**, réinitialisation par e-mail, `django-axes` (5 échecs / couple e-mail-IP) | Exigence du sujet (inscription, connexion, réinitialisation) ; pas de dépendance à la délivrabilité d'un e-mail à chaque connexion |
| Base | PostgreSQL 16 | **PostgreSQL 17** (Compose, CI) ; **Neon** (UE) en production | La base gratuite Render expire 30 jours après création ; Neon gratuit n'expire pas |
| Hébergement | non arrêté | **Docker Compose** (référence, README) + **Render** (`render.yaml`, Francfort), déployé par la CI après CI verte | Le web gratuit Render s'endort après 15 min et Render n'a pas de worker gratuit : web et `db_worker` tournent dans le même conteneur (honcho). Un worker séparé passe en offre payante si la charge le demande ; ce coût d'hébergement est distinct du budget API (ADR-009) |
| Émotion | 1 appel Mistral Small : prompt visuel + émotion (ADR-003) | **Hugging Face Inference** en premier, puis Mistral Small à sortie JSON, puis lexique émotionnel français | La grille d'évaluation cite Hugging Face ; trois niveaux gardent une réponse même fournisseur coupé. L'émotion reste inférée **du texte** (ADR-001). Le prompt visuel reste produit par Mistral Small (ADR-003) |
| STT, image | Voxtral Mini Transcribe, FLUX.2 [klein] UE | **inchangés** | ADR-002, ADR-004 |
| Observabilité | OpenTelemetry | **structlog** JSON (`request_id`, `dream_id`, jamais de contenu) + **Sentry** avec scrubbing + table `ApiCall` + page `/ops` | Suffisant pour un monolithe ; les SLI d'ADR-006 se calculent depuis `ApiCall` |

## Points maintenus du bloc 1
- Ports / adapters (`Transcriber`, `EmotionClassifier`, `PromptBuilder`, `ImageGenerator`, `SoundGenerator`), adapter réel et adapter fake sélectionnés par `AI_MODE=real|fake`.
- Idempotence de `process_dream(dream_id)` : reprise à l'étape échouée, aucun appel déjà payé n'est rejoué.
- Suppression de l'audio après transcription réussie ; mention « générée par IA » sur chaque image ; consentement séparé pour l'image (US-03, US-11).
- Quotas par utilisateur et coupe-circuit budgétaire, révisés par ADR-009.

## Points ouverts (tranchés dans leur ticket)
- **Stockage des images** : le disque d'un service web gratuit Render n'est pas persistant. Options : stockage S3-compatible hébergé dans l'UE via `django-storages`, ou stockage en base. Décision dans le ticket image (DREAM-10).
- **Chiffrement applicatif** de `transcription.text` et du prompt visuel (bloc 1, specs §2) : à implémenter avec les modèles (DREAM-6), clé hors base.

## Conséquences
- Un seul service à déployer et à superviser ; la file vit dans PostgreSQL, sa profondeur se lit en SQL (page `/ops`, test de charge).
- La file en base supporte moins de débit que Redis : le test de charge (étape 4) mesure le débit réel du worker et dit si c'est le goulot.
- Le sommeil du service gratuit après 15 min impose un réveil d'environ une minute à la première visite : à mentionner dans la démonstration ou à éviter par une instance payante le jour de la soutenance.
- Les diagrammes C4 conteneurs et séquence sont régénérés à partir du code réel pour le rapport de production.
