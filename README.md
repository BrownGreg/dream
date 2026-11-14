# Synthétiseur de rêves — maquette Streamlit (pré-production)

Maquette interactive du bloc 1 : l'utilisateur raconte un rêve à voix haute, l'application le transcrit, en déduit l'émotion dominante, génère une image et une ambiance sonore, puis range le rêve dans un historique personnel.

Cette branche (`maquette`) ne contient **que la maquette**. L'application de production (Django) est sur la branche `main`.

> Tout fonctionne **sans clé d'API** : la transcription, l'analyse et l'image sont simulées. Les adapters Mistral réels sont branchables par variable d'environnement.

## Prérequis

- **Python 3.12**
- [**uv**](https://docs.astral.sh/uv/) (recommandé) ou `pip`
- Un navigateur récent (Chrome, Firefox, Edge) pour l'enregistrement au micro

## Installation

```bash
git clone -b maquette https://github.com/BrownGreg/dream.git maquette-dream
cd maquette-dream
uv venv --python 3.12
uv pip install -e ".[dev]"        # sans uv : python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env              # facultatif : seulement pour les adapters réels
```

## Lancer la maquette

```bash
DREAMSYNTH_MOCK_LATENCY=0.8 uv run streamlit run app/streamlit_app.py
```

Puis ouvrir **http://localhost:8501**. `DREAMSYNTH_MOCK_LATENCY` ajoute 0,8 s par étape simulée pour rendre la progression visible ; sans elle, le traitement est instantané.

## Parcours de démonstration

1. **Accueil** : cocher les consentements (transcription, image, suivi des émotions), puis « Enregistrer mes choix ». Sans consentement à la transcription, l'envoi d'un rêve est bloqué.
2. **Raconter un rêve** :
   - enregistrer au micro, ou importer un fichier `.wav` / `.mp3` de **3 s à 5 min**, **20 Mo au plus** ; des exemples prêts à l'emploi sont dans `benchmark/corpus/audio/` (`01_heureux.mp3`, `02_cauchemar.mp3`…) ;
   - options : « Ne pas générer d'image », style visuel ;
   - **« Mode démonstration »** : simule une panne (service indisponible, délai dépassé, refus du filtre de sécurité) pour montrer les messages d'erreur et les indicateurs de chargement.
3. **Mes rêves** : filtre par émotion, frise, tendances mensuelles, export JSON, suppression d'un rêve ou de tout le journal.

Les rêves sont gardés **en mémoire, le temps de la session** (`st.session_state`) : recharger la page repart de zéro.

## Configuration (`.env`)

| Variable | Valeurs | Effet |
|---|---|---|
| `DREAMSYNTH_TRANSCRIBER` | `mock` (défaut) · `mistral` | Transcription simulée, ou Voxtral (Mistral) |
| `DREAMSYNTH_ANALYZER` | `mock` (défaut) · `mistral` | Émotion par mots-clés, ou Mistral Small |
| `DREAMSYNTH_IMAGE` | `mock` (seule valeur prise en charge) | Image de remplacement (`picsum.photos`) |
| `DREAMSYNTH_MOCK_LATENCY` | secondes | Latence simulée par étape |
| `MISTRAL_API_KEY` | clé | Requise pour les valeurs `mistral` |
| `MISTRAL_STT_MINI`, `MISTRAL_LLM_MODEL` | identifiants de modèles | Modèles utilisés par les adapters Mistral |

## Tests

```bash
uv run pytest                              # unitaires, intégration, scénarios BDD, interface (AppTest)
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check . && uv run mypy --strict src
```

Résultat attendu : **89 réussis, 3 ignorés**. Les trois tests ignorés correspondent aux stories US-18, US-20 et US-23, prévues pour les releases R2 et R3 et non implémentées dans la maquette.

| Dossier | Contenu |
|---|---|
| `tests/unit/` | domaine, audio, budget et journalisation, pipeline, services et dépôt |
| `tests/integration/` | adapters Mistral (réponses HTTP simulées avec `respx`) |
| `tests/features/` | scénarios Gherkin issus des user stories (`pytest-bdd`) |
| `tests/app/` | interface Streamlit (`AppTest`) |
| `tests/load/` | plan de test de charge (Locust, bouchon d'API) |

## Benchmark des API (facultatif)

```bash
uv pip install -e ".[bench]"
uv run python benchmark/run_latency.py --mock          # valide la chaîne sans clé
uv run python benchmark/run_latency.py --live -n 10    # mesures réelles, MISTRAL_API_KEY requise
uv run python benchmark/cost_model.py                  # coût pour 10 rêves par jour, par scénario
```

## Structure

```
app/                 interface Streamlit (accueil, nouveau rêve, mes rêves) et ambiances sonores
src/dreamsynth/      logique : modèles Pydantic, pipeline, services simulés et adapters Mistral, budget
tests/               tests pytest (voir plus haut)
benchmark/           corpus audio synthétique, scripts de latence, de WER et de coût
docs/backlog/        user stories (source des scénarios BDD)
docs/schemas/        schéma JSON d'un rêve exporté, généré depuis les modèles Pydantic
tools/               scripts de génération (schéma, backlog, journey maps)
demo/                script de la vidéo de démonstration
```

## Choix techniques

- **Streamlit ≥ 1.40** (et non 1.35 comme proposé par le sujet) : `st.audio_input`, qui permet l'enregistrement au micro, n'est stable qu'à partir de la version 1.40.
- La logique métier (`src/dreamsynth`) est indépendante de Streamlit : l'interface ne parle qu'au pipeline, qui choisit les services simulés ou réels.
