# Synthétiseur de rêves — pré-production

Raconter un rêve à voix haute → transcription → image + ambiance sonore → émotion → historique personnel.
Ce dépôt contient la **pré-production** : dossiers de cadrage et de spécifications, benchmark des API, maquette Streamlit, tests prototypaux.

| Livrable | Emplacement |
|---|---|
| Dossier de cadrage (≤ 15 p.) | `build/dossier_cadrage.pdf` (sources `docs/cadrage/`) |
| Spécifications & architecture (≤ 10 p.) | `build/specifications_architecture.pdf` (sources `docs/specs/`) |
| Benchmark | `docs/annexes/benchmark.xlsx` (généré par `benchmark/build_xlsx.py`) |
| Décisions | `docs/decisions/ADR-00x-*.md` |
| Maquette | `app/` |
| Tests | `tests/` (unitaires, intégration, BDD, UI, charge) |
| Démo | `demo/script_video.md` |

## Prérequis
- Python **3.12**, [uv](https://docs.astral.sh/uv/) (ou `pip`)
- `ffmpeg` (corpus audio et ambiances), `espeak` (corpus local) — facultatifs pour lancer la maquette
- Pour régénérer les documents : `typst`, `pandoc`, Java + PlantUML

## Installation
```bash
uv venv --python 3.12
uv pip install -e ".[dev,bench]"      # ou : python -m pip install -e ".[dev,bench]"
cp .env.example .env                  # facultatif : clés API pour le mode réel
```

## Variables d'environnement
| Variable | Valeurs | Effet |
|---|---|---|
| `DREAMSYNTH_TRANSCRIBER` | `mock` (défaut) · `mistral` | Transcription simulée ou Voxtral |
| `DREAMSYNTH_ANALYZER` | `mock` (défaut) · `mistral` | Émotion par mots-clés ou Mistral Small 4 |
| `DREAMSYNTH_IMAGE` | `mock` (défaut) | Image placeholder `picsum.photos` (adapter BFL prévu au Sprint 2) |
| `DREAMSYNTH_MOCK_LATENCY` | secondes | Latence simulée par étape (rend la progression visible en démo) |
| `MISTRAL_API_KEY` | clé | Requise pour `mistral` et pour le benchmark `--live` |

Sans aucune clé, tout fonctionne en mode simulé.

## Lancer la maquette
```bash
DREAMSYNTH_MOCK_LATENCY=0.8 streamlit run app/streamlit_app.py
```
1. **Accueil** : cocher les consentements (transcription, image, suivi des émotions) puis « Enregistrer mes choix ».
2. **Raconter un rêve** : enregistrer au micro ou importer un `.wav`/`.mp3` (3 s à 5 min, ≤ 20 Mo), option « Ne pas générer d'image », style visuel ; « Mode démonstration » pour simuler une panne (service indisponible, délai dépassé, refus du filtre).
3. **Mes rêves** : filtre par émotion, frise, tendances mensuelles, export JSON, suppression d'un rêve ou du journal.

## Tests et qualité
```bash
ruff check . && ruff format --check . && mypy --strict src
pytest --cov=src --cov-report=term-missing      # unitaires, intégration, BDD (Gherkin), UI (AppTest)
python tools/backlog.py --check && python tools/export_schema.py --check
```
Plan de charge (bouchon d'API, durées simulées) :
```bash
python tests/load/stub_api.py &
locust -f tests/load/locustfile.py --host http://127.0.0.1:8765 --headless --csv benchmark/results/load
```

## Benchmark
```bash
python benchmark/run_latency.py --mock          # valide la chaîne sans clé
python benchmark/run_latency.py --live -n 10    # avec MISTRAL_API_KEY dans .env
python benchmark/wer.py                         # WER du dernier passage live
python benchmark/cost_model.py                  # coût 10 rêves/jour par scénario
python benchmark/build_xlsx.py                  # → docs/annexes/benchmark.xlsx
```

## Régénérer les artefacts dérivés
```bash
python tools/backlog.py          # story map, Gherkin, exigences, traçabilité, import Jira
python tools/export_schema.py    # docs/schemas/dream.schema.json depuis Pydantic
python tools/journey_map.py      # journey maps
python tools/build_docs.py       # diagrammes PlantUML + les deux PDF
```

## Pourquoi Streamlit ≥ 1.40 et non ≥ 1.35 (sujet)
`st.audio_input` (enregistrement micro) n'est disponible en version stable qu'à partir de Streamlit 1.40 ; la version installée est 1.66.1.
