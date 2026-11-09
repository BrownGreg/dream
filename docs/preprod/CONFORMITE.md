# Conformité au sujet — vérification ligne à ligne

Sujet : `docs/source/sujet.pdf` (4 pages). Vérification du 2026-11-06. DC = `build/dossier_cadrage.pdf` (15/15 p.), SP = `build/specifications_architecture.pdf` (10/10 p.).
Statuts : ✅ satisfait · ⚠️ partiel (écart expliqué) · ❌ absent (expliqué).

## 2. Objectifs
| Exigence | Où | Statut |
|---|---|---|
| Transcription d'un rêve raconté à l'oral | ADR-002 ; SP p. 6 ; maquette (mock + adapter Voxtral) | ✅ |
| Image (ou micro-vidéo) + ambiance sonore | ADR-004, ADR-005 ; maquette (image placeholder + 6 ambiances) ; vidéo en R3 (US-20) | ✅ |
| Classification émotionnelle | ADR-001, ADR-003 ; EXF-06 (6 classes) ; maquette | ✅ |
| Consultation historique dans un tableau de bord | US-09/10/16 ; page « Mes rêves » | ✅ |

## 4. Organisation
| Exigence | Où | Statut |
|---|---|---|
| Travail individuel, Scrum, sprints d'1 semaine | DC p. 12 (capacité, cérémonies en solo) | ✅ |
| GitHub Projects ou Jira | `docs/annexes/jira_import.csv` (5 épopées, 21 stories, 13 tâches) | ⚠️ fichier prêt, non importé : consigne « local uniquement » |

## 5.1 Dossier de cadrage (≤ 15 p.)
| Exigence | Où | Statut |
|---|---|---|
| ≤ 15 pages | `pdfinfo` : 15 | ✅ |
| 1. Vision produit (1 p.) : elevator pitch + critères de succès | DC p. 2 | ✅ |
| 2. ≥ 2 personae, journey map illustrée | DC p. 2–4 (3 personae + anti-persona, 3 journey maps) | ✅ |
| 3. User Story Map + MoSCoW | DC p. 5–6 (carte, matrice Kano/MoSCoW, tableau des stories) | ✅ |
| 4. ≥ 3 STT ; ≥ 3 T2I/vidéo ; ≥ 2 TTS | DC p. 7–8 : 7 STT, 6 image + 2 vidéo, 4 TTS | ✅ |
| 4. Tableau comparatif coût ($) | DC p. 7–8 ; `benchmark.xlsx` | ✅ |
| 4. … temps de réponse | Mesuré pour faster-whisper local (p95 3,81 s) ; autres « NON MESURÉ — mock » faute de clé | ⚠️ clé Mistral absente ; scripts `--live` prêts |
| 4. … quota | Quotas officiels relevés pour 7 fournisseurs sur 9 ; Mistral non publié | ⚠️ |
| 4. … RGPD | DC p. 7–8 (UE, DPA, entraînement) ; onglets catégorie du classeur | ✅ |
| 5. RGPD & éthique IA, DPA nécessaire ? | DC p. 10–11 (oui, avec chaque fournisseur : registre §5.3) ; annexe `aipd.md` | ✅ |
| 6. Roadmap, release plan, backlog Sprint #1 détaillé | DC p. 12 | ✅ |
| 7. ≥ 8 risques, matrice probabilité/impact, mesures | DC p. 13 (11 risques) | ✅ |
| 8. Plan qualité : métriques, revue de code, seuil de couverture | DC p. 14–15 (≥ 80 % ; mesuré 98,0 %) | ✅ |

## 5.2 Spécifications & architecture (≤ 10 p.)
| Exigence | Où | Statut |
|---|---|---|
| ≤ 10 pages | `pdfinfo` : 10 | ✅ |
| 1. C4 Context + Container complets | SP p. 2–3 | ✅ |
| 2. ERD + dictionnaire d'attributs | SP p. 4–5 | ✅ |
| 3. Séquence UML du traitement d'un rêve | SP p. 6 (page paysage, branches d'erreur) | ✅ |
| 4. API interne : choix argumenté | SP p. 7 (+ contrats REST, codes d'erreur) | ✅ |
| 5. Exigences, performance, SLO, budget API | SP p. 8–9 ; ADR-006, ADR-007 | ✅ |
| 6. Libs Python, CI/CD, monitoring | SP p. 9–10 ; `.github/workflows/ci.yml` | ✅ |

## 5.3 Maquette Streamlit
| Exigence | Où | Statut |
|---|---|---|
| Enregistrer / uploader (.wav/.mp3) | `app/pages/1_Nouveau_reve.py` (`st.audio_input`, `st.file_uploader`) ; validation `src/dreamsynth/audio.py` | ✅ |
| Transcription fictive (mock) affichée | `MockTranscriber`, zone modifiable | ✅ |
| Image placeholder via API publique / stable-url | `PlaceholderImageGenerator` (picsum.photos, graine = hash du prompt) | ✅ |
| Sélecteur d'émotion simulé + icône | « Corriger l'émotion », badge icône + couleur | ✅ |
| Gestion d'erreurs et indicateurs de chargement | `st.status` + barre par étape ; messages + « Relancer » ; mode démo de pannes | ✅ |
| Vidéo démo ≤ 3 min | `demo/script_video.md` (minutage) | ⚠️ enregistrement à faire par l'auteur (micro réel requis) |
| README d'installation | `README.md` | ✅ |

## 5.4 Annexes obligatoires
| Exigence | Où | Statut |
|---|---|---|
| `benchmark.xlsx` coût / performance | `docs/annexes/benchmark.xlsx` (349 formules, 0 erreur au recalcul LibreOffice) | ✅ |
| Scripts de test prototypaux (pytest) | `tests/` : 89 passés, 3 ignorés et signalés | ✅ |

## 6. Détails des tâches
| Exigence | Où | Statut |
|---|---|---|
| Interviews éclair (2 fictifs) | `docs/annexes/interviews.md` ; insights DC p. 3 | ✅ |
| Matrice Kano, priorités | DC p. 5 ; `docs/annexes/kano.md` | ✅ |
| Wireframes basse fidélité (Figma) | DC p. 4–5 (PlantUML Salt) | ⚠️ PlantUML et non Figma : versionnés et régénérés avec le code |
| Charte minimaliste, flow diagram | DC p. 4–5 | ✅ |
| Scripts Python de mesure de latence | `benchmark/run_latency.py` (`--mock`, `--live`, `--local`) | ✅ |
| Analyse coût sur 10 rêves/jour | DC p. 8 ; onglet « Coût 10 rêves-jour » (formules) | ✅ |
| Modèle relationnel + schéma JSON d'un rêve stocké | SP p. 4–5 ; `docs/schemas/dream.schema.json` (généré) | ✅ |
| Architecture de l'application à développer | SP p. 2–3 | ✅ |
| Stratégie BDD/TDD, plan de test de charge | DC p. 15 ; `tests/features/`, `tests/load/` | ✅ |
| Tickets / stories Jira pour la Production | `docs/annexes/jira_import.csv` | ✅ |

## 7. Contraintes
| Exigence | Où | Statut |
|---|---|---|
| Python 3.12 | `.venv` 3.12.15, `requires-python` | ✅ |
| Streamlit ≥ 1.35 | 1.66.1 (≥ 1.40 retenu pour `st.audio_input` stable, README) | ✅ |
| Git | dépôt local | ⚠️ travail non commité (aucun commit demandé) |
| draw.io ou PlantUML | PlantUML (C4, ERD, séquence, flow, wireframes) | ✅ |
| PEP 8 + type hints | ruff 0 erreur ; mypy `--strict` 0 erreur | ✅ |
| Docstrings Google style | règle ruff `D` (convention google) | ✅ |

**Aucun ❌.** Les ⚠️ restants dépendent de l'auteur : clé API pour les mesures live, enregistrement de la vidéo, date de rendu sur les pages de garde, import Jira et commit.
