---
title: "Rendu — Pré-production (bloc 1)"
subtitle: "Synthétiseur de rêves"
header-left: "Rendu pré-production"
titlepage: false
toc: false
---

# Accès

| | |
|---|---|
| Code (maquette, tests, scripts) | [github.com/BrownGreg/dream › docs/preprod](https://github.com/BrownGreg/dream/tree/main/docs/preprod) |
| Installation de la maquette | [README de la maquette](https://github.com/BrownGreg/dream/blob/main/docs/preprod/maquette/README.md) |
| Suivi Jira (stories du bloc 1 : DREAM-1 à 39) | [Tableau Jira du projet DREAM](https://gregoryyazidi.atlassian.net/jira/software/projects/DREAM/boards/2) |

Le code n'est pas joint à ce dossier : il est dans le dépôt GitHub ci-dessus.

# État du dossier

{{ETAT}}

# Contenu

| Fichier | Livrable du sujet |
|---|---|
| `01_dossier_cadrage.pdf` | 5.1 Dossier de cadrage ({{PAGES_DC}} pages, limite 15) |
| `02_specifications_architecture.pdf` | 5.2 Spécifications & architecture ({{PAGES_SP}} pages, limite 10) |
| `03_benchmark.xlsx` | 5.4 Tableau benchmark coût / performance |
| `04_tests_maquette.txt` | 5.4 Scripts de test prototypaux (pytest) : résultat d'exécution et couverture |
| `05_video_demo.mp4` | 5.3 Vidéo de démonstration (≤ 3 min) |
| `annexes/` | entretiens, matrice Kano, AIPD (PDF) ; import Jira et traçabilité (CSV) ; schéma JSON d'un rêve ; diagrammes (SVG) |

# Correspondance avec le sujet

## 5.1 Dossier de cadrage (`01_dossier_cadrage.pdf`)

| Exigence | Section (page) |
|---|---|
| 1. Vision produit : elevator pitch, critères de succès | §1 (p. 2) |
| 2. Personae (≥ 2) et journey map illustrée | §2 (p. 2–4) : 3 personae, 1 anti-persona, 3 journey maps |
| 3. User Story Map et priorisation MoSCoW | §3 (p. 5–6) |
| 4. Benchmark : ≥ 3 STT, ≥ 3 texte-image ou vidéo, ≥ 2 TTS ; coût, temps de réponse, quota, RGPD | §4 (p. 7–9) : 7 STT, 6 image + 2 vidéo, 4 TTS ; latences Mistral mesurées en réel le 15/11/2026 |
| 5. RGPD et éthique IA, DPA | §5 (p. 10–11) ; annexe `aipd.pdf` |
| 6. Roadmap, release plan, backlog du Sprint 1 | §6 (p. 12) |
| 7. Plan de risques (≥ 8, matrice, mesures) | §7 (p. 13) : 11 risques |
| 8. Plan qualité : métriques, revue de code, seuil de couverture | §8 (p. 14–15) |

## 5.2 Spécifications & architecture (`02_specifications_architecture.pdf`)

| Exigence | Section (page) |
|---|---|
| 1. C4 Context et Container | §1 (p. 2–3) |
| 2. ERD et dictionnaire d'attributs | §2 (p. 4–5) ; annexe `dream.schema.json` |
| 3. Séquence UML du traitement d'un rêve | §3 (p. 6) |
| 4. API interne : choix argumenté | §4 (p. 7) |
| 5. Exigences, performance, SLO, budget API | §5 (p. 8–9) |
| 6. Justification technologique : bibliothèques, CI/CD, monitoring | §6 (p. 9–10) |

## 5.3 Maquette Streamlit (dépôt, `docs/preprod/maquette/`)

| Exigence | Où |
|---|---|
| Enregistrer ou importer un audio (.wav, .mp3) | `app/pages/1_Nouveau_reve.py` (`st.audio_input`, `st.file_uploader`) ; validation `src/dreamsynth/audio.py` |
| Transcription fictive affichée | `MockTranscriber`, zone de texte modifiable |
| Image placeholder par une URL stable | `PlaceholderImageGenerator` (picsum.photos, graine dérivée du prompt) |
| Sélecteur d'émotion simulé et icône | « Corriger l'émotion », badge icône et couleur |
| Gestion d'erreurs et indicateurs de chargement | `st.status` et barre par étape ; messages et « Relancer » ; mode démo de pannes |
| Vidéo de démonstration | `05_video_demo.mp4` (script : `maquette/demo/script_video.md`) |
| README d'installation | `maquette/README.md` |

## 5.4 Annexes obligatoires

| Exigence | Où |
|---|---|
| `benchmark.xlsx` | `03_benchmark.xlsx` : 12 onglets, coûts en formules, latences et WER mesurés |
| Scripts de test (pytest) | `04_tests_maquette.txt` ; sources : `maquette/tests/` (unitaires, intégration, BDD Gherkin, interface, charge) |

## 6. Tâches détaillées

| Tâche | Où |
|---|---|
| Interviews éclair, matrice Kano | `annexes/entretiens.pdf`, `annexes/kano.pdf` ; dossier de cadrage §2–3 |
| Wireframes basse fidélité, charte, flow diagram | dossier de cadrage §2–3 ; `annexes/diagrammes/wireframes.svg`, `flow.svg` (PlantUML, et non Figma : versionnés avec le code) |
| Scripts de mesure de latence, coût sur 10 rêves par jour | `maquette/benchmark/run_latency.py`, `cost_model.py` ; onglet « Coût 10 rêves-jour » du classeur |
| Modèle relationnel et schéma JSON d'un rêve | spécifications §2 ; `annexes/dream.schema.json` |
| Architecture de l'application de production | spécifications §1 |
| Stratégie BDD/TDD, plan de test de charge | dossier de cadrage §8 ; `maquette/tests/features/`, `maquette/tests/load/` |
| Tickets Jira pour la production | `annexes/jira_import.csv` (importé : DREAM-1 à 39) |

## 7. Contraintes

Python 3.12 ; Streamlit ≥ 1.35 ; Git ; diagrammes PlantUML ; PEP 8, annotations de type et docstrings Google (ruff, mypy strict). Détail ligne à ligne : `docs/preprod/CONFORMITE.md` dans le dépôt.
