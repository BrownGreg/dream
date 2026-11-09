# Stratégie de tests

> Mesures du 2026-11-09, commit `4957e15` (branche DREAM-18) : 278 tests verts, 5 ignorés (cassettes VCR pas encore enregistrées), couverture globale 99,5 % (branches comprises). Les chiffres à jour sont dans l'artefact `couverture` de chaque exécution de la CI.

## Principes

1. **Aucun appel réel en CI ni en charge.** `AI_MODE=fake` partout ; les adapters réels sont testés contre des réponses HTTP simulées (`respx`) ou rejouées (cassettes VCR). Un appel réseau en CI est impossible : `record_mode=none`.
2. **Les adapters fake passent par le même client résilient que les vrais.** Retries, journal `ApiCall`, coupe-circuit budgétaire et pannes simulées (`AI_FAKE_FAIL_STEPS`) sont donc exercés de bout en bout sans dépenser un centime.
3. **Le seuil de 70 % s'applique par fonctionnalité critique**, pas seulement en global : `scripts/check_coverage.py` agrège la couverture (lignes et branches) des fichiers de chaque fonctionnalité et fait échouer la CI sous le seuil.
4. **Un bug corrigé = un test de non-régression** cité dans [`docs/incidents.md`](../incidents.md).
5. **Données synthétiques uniquement** : corpus audio du bloc 1 (voix de synthèse), sons sinusoïdaux ffmpeg, récits fictifs. Jamais de vrai rêve dans un test, une cassette ou un journal.

## Pyramide

| Niveau | Nombre | Outils | Ce qui est vérifié |
|---|---|---|---|
| Unitaires (`tests/unit/`) | 94 | pytest, pytest-mock, respx, factory_boy | client résilient, budget, prix, chiffrement, audio ffmpeg, adapters (succès, 429, 5xx, 4xx, délai, refus de sécurité, réponse invalide), lexique |
| Intégration (`tests/integration/`) | 145 | pytest-django, client de test Django, PostgreSQL en CI | vues, formulaires, pipeline complet en mode fake, reprise après plantage, HTMX, accès croisé (404), RGPD, observabilité, `collectstatic` de production |
| Cassettes VCR (`tests/integration/test_vcr_providers.py`) | 4 (ignorés tant que non enregistrés) | pytest-recording | format réel des réponses Voxtral, Hugging Face, Mistral, BFL |
| Navigateur (`tests/e2e/`, marqueur `e2e`) | 1 audit (10 pages) + parcours DREAM-19 | Playwright Chromium, axe-core 4.14.0 | accessibilité WCAG 2.2 AA en 390 px ; parcours inscription → micro simulé → résultat |
| Charge (`tests/load/`, marqueur `load`) | DREAM-20 | Locust | p50/p95, erreurs, file, débit du worker sous 5 → 20 → 50 utilisateurs |
| Build | 1 job CI | Docker Compose | image, migrations, `/health`, page de connexion, CSS servi |

## Ce qui est simulé, et pourquoi

| Dépendance | Simulation | Raison |
|---|---|---|
| Mistral, Hugging Face, BFL | `respx` (erreurs), cassettes VCR (formats réels), adapters fake (pipeline) | coût (budget de 20 €), déterminisme, scénarios d'erreur impossibles à provoquer à la demande |
| Horloge | `datetime` fixé, `time.monotonic` / `time.sleep` remplacés | quotas à minuit, délai de polling BFL, backoff sans attente réelle |
| Worker | backend `ImmediateBackend` en test ; vrai `db_worker` en charge et en vérification manuelle | exécuter la tâche dans le test tout en gardant `on_commit` (le traitement n'est jamais dans la requête) |
| Stockage | `InMemoryStorage` en test ; `DatabaseStorage` testé séparément | isolation des tests |
| Verrou PostgreSQL | connexion simulée **limitée à `dreams.locks`** | SQLite en local ; voir incident #6 |

Non simulé : ffmpeg/ffprobe et libmagic (vrais binaires sur les fichiers de `tests/fixtures/`), PostgreSQL en CI, Chromium pour les tests navigateur.

## Fonctionnalités critiques → modules → tests

| Fonctionnalité | Couverture | Modules | Tests principaux |
|---|---|---|---|
| Authentification et consentement | 100 % | `accounts/forms.py`, `services.py`, `views.py` | `test_auth.py` (inscription, consentements séparés, casse de l'e-mail, blocage après 5 échecs, réinitialisation) |
| Upload et validation audio | 98,3 % | `dreams/audio.py`, `dreams/forms.py` | `test_audio.py`, `test_record_views.py` (wav/webm/m4a, vide, corrompu, faux type, trop long/court/lourd, quota, budget) |
| Pipeline et reprise par étape | 98,6 % | `dreams/pipeline.py`, `tasks.py`, `locks.py` | `test_pipeline.py` (bout en bout, idempotence, reprise, `partial`, refus de sécurité, panne STT, verrou) |
| Pipeline IA : adapters | 100 % | `dreams/services/adapters/*`, `registry.py`, `emotion.py` | `test_stt_adapters.py`, `test_emotion.py`, `test_prompt_image.py` |
| Client résilient (timeouts, retries) | 100 % | `dreams/services/http.py`, `errors.py` | `test_resilient_client.py` (429 + `Retry-After`, 5xx, 4xx jamais rejoués, délai facturé, backoff) |
| Garde-fou budget et quotas | 100 % | `dreams/services/budget.py`, `pricing.py` | `test_budget.py`, `test_resilient_client.py::test_coupe_circuit_…` |
| Données sensibles chiffrées | 100 % | `dreams/fields.py` | `test_dreams_models.py` (chiffré en base, rotation de clé, clé absente) |
| Stockage et accès aux fichiers | 98,8 % | `dreams/storage.py`, `dreams/views.py` | `test_storage_files.py` (propriétaire seulement, chemins invalides, CSP SVG) |
| Tableau de bord : historique, filtres, statistiques | 100 % | `dashboard/forms.py`, `queries.py`, `views.py`, `stats.py` | `test_dashboard_history.py` (filtres combinés, pagination, requêtes bornées), `test_dashboard_stats.py` |
| Suppression et export RGPD | 98,7 % | `accounts/gdpr.py`, `dreams/deletion.py` | `test_gdpr.py`, `test_dream_actions.py` (fichiers effacés, coût conservé sans lien) |
| Observabilité | 98,6 % | `config/observability.py`, `middleware.py`, `dashboard/ops.py` | `test_observability.py` (aucun contenu de rêve dans les journaux, Sentry nettoyé, `/ops` staff) |
| Santé de l'application | 100 % | `config/views.py` | `test_health.py` (base en panne → 503, worker en retard → `degraded`) |

## Cassettes VCR

- Enregistrées une fois avec les vraies clés sur le **corpus synthétique** : `AI_MODE=real uv run pytest tests/integration/test_vcr_providers.py --record-mode=once`.
- `vcr_config` remplace les en-têtes `Authorization`, `x-key` et les cookies par `[secret]`, et le **corps de chaque requête** (audio, récit) par `[corps retire]`.
- `test_cassettes_sans_secret.py` inspecte chaque cassette versionnée (motifs de clés Mistral, HF, BFL ; corps de requête).

## Portes de la CI

lint (ruff, docstrings Google) → types (mypy strict) → migrations à jour → tests sur PostgreSQL 17 (`--cov-fail-under=70` global) → **seuil de 70 % par fonctionnalité critique** → E2E navigateur (audit axe) → image Docker + test de fumée → déploiement Render + `/health` en production (sur `main`).

## Limites connues

- La qualité de la transcription (WER) et la pertinence de l'émotion ne sont pas testées automatiquement : elles se mesurent sur le corpus avec les vraies API (benchmark du bloc 1, Jalon B).
- L'enregistrement micro réel n'est couvert que par Chromium avec un faux périphérique (DREAM-19) ; Safari (mp4/aac) est couvert par la conversion du fichier `reve_court.m4a`, pas par un navigateur.
