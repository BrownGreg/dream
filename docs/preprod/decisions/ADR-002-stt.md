# ADR-002 — Transcription : Mistral Voxtral Mini Transcribe 3

- **Statut** : accepté sous condition de mesure (WER) · 2026-11-02
- **Compétence** : C1-2 · **Liens** : US-04, KPI K3, `benchmark.xlsx` onglet STT

## Contexte
Récits de 30–90 s, en français, souvent dits à voix basse au réveil. Données potentiellement sensibles (art. 9 RGPD). Six options comparées (onglet STT du benchmark, prix consultés le 2026-11-02).

## Options (coût par rêve, hypothèse H1 = 1 min)
| Option | $/rêve | Hébergement | Entraînement sur les données | DPA |
|---|---|---|---|---|
| **Mistral Voxtral Mini Transcribe 3** | 0,0035 | UE par défaut | opt-out (console) | oui |
| Mistral Voxtral Small Transcribe 3 | 0,0040 | UE | opt-out | oui |
| AssemblyAI Universal-3.5 Pro | 0,0035 | US | oui par défaut, opt-out | oui |
| ElevenLabs Scribe v2 | 0,0037 | à la discrétion du fournisseur | non trouvé | oui |
| Deepgram Nova-3 | 0,0043 | US | non trouvé | mentionné |
| OpenAI gpt-transcribe | 0,0045 | US (UE sur approbation) | non par défaut | non trouvé |
| faster-whisper auto-hébergé | coût GPU | notre infra | aucun tiers | sans objet |

Sources : onglet `Sources` du classeur.

## Décision
Voxtral Mini Transcribe 3 via l'endpoint UE, `language=fr`. Il est à égalité de prix avec le moins cher, seul de la liste hébergé dans l'UE par défaut avec DPA publié, et mesurable en direct (clé Mistral disponible).
**Condition** : si le WER mesuré sur le corpus (K3) dépasse 10 %, bascule sur Voxtral Small Transcribe 3 (+0,0005 $/rêve), même contrat.

## Conséquences
- Avant toute donnée réelle : opt-out d'entraînement activé (Admin › Privacy) et demande de Zero Data Retention déposée (couvre `/v1/audio/transcriptions`) — critères de la Definition of Done de la release MVP.
- Un seul sous-traitant pour STT + LLM + TTS : un DPA, une AIPD fournisseur, mais dépendance concentrée (risque R-06) ; faster-whisper reste le plan de repli documenté.
- Le benchmark live est biaisé si le corpus est produit par Voxtral TTS : corpus de référence généré par espeak (manifeste `benchmark/corpus/audio/manifest.json`).
