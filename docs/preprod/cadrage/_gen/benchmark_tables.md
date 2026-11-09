<!-- Généré par benchmark/build_report.py — ne pas éditer -->

Prix et clauses consultés le 2026-11-02. Coût par rêve selon les hypothèses H1–H8 (annexe `benchmark.xlsx`, onglet Hypothèses).

| Cat. | Fournisseur — modèle | $/rêve | p95 (s) | Quota | UE · DPA | Entraînement |
|---|---|---|---|---|---|---|
| STT | Mistral AI — voxtral-mini-transcribe-3 | 0,0035 | n. m. | Non publié (d… | oui · Oui | Opt-out via Admin panel › Privacy… |
| STT | Mistral AI — voxtral-small-transcribe-3 | 0,0040 | n. m. | Non publié (d… | oui · Oui | Opt-out via Admin panel › Privacy |
| STT | OpenAI — gpt-transcribe | 0,0045 | n. m. | Non trouvé (g… | non · non trouvé | Non par défaut |
| STT | Deepgram — nova-3 (monolingue, pré-enregistré) | 0,0043 | n. m. | 50 requêtes s… | non · Mentionné (… | non trouvé |
| STT | AssemblyAI — Universal-3.5 Pro | 0,0035 | n. m. | Non trouvé en… | non · Oui | Oui par défaut, opt-out possible |
| STT | ElevenLabs — Scribe v2 | 0,0037 | n. m. | Concurrence f… | non · Oui | non trouvé |
| STT | SYSTRAN faster-whisper (auto-hébergé) — small (int8, CPU 8 cœurs) | NP | 3,81 | Limité par le… | oui · Sans objet | Non (aucun tiers) |
| LLM | Mistral AI — Mistral Small 4 (mistral-small-2603) | 0,0003 | n. m. | Non publié (d… | oui · Oui | Opt-out via Admin panel › Privacy |
| LLM | OpenAI — gpt-4o-mini | 0,0003 | n. m. | 5 000 RPM · 2… | non · non trouvé | Non par défaut |
| LLM | Hugging Face (auto-hébergé) — MoritzLaurer/mDeBERTa-v3-base-mnli-xnli | NP | auto-hébergé | Limité par le… | oui · Sans objet | Non (aucun tiers) |
| Image | Black Forest Labs — FLUX.2 [pro] | 0,0315 ᴱ | n. m. | 24 requêtes s… | oui · non trouvé | Oui par défaut ; opt-out par e-ma… |
| Image | Black Forest Labs — FLUX.2 [klein] | 0,0147 ᴱ | n. m. | 24 requêtes s… | oui · non trouvé | Oui par défaut ; opt-out par e-ma… |
| Image | Google (Gemini API, payant) — Nano Banana 2.1 | 0,0353 | n. m. | Palier 1 : 10… | non · Oui (Proces… | Non en offre payante (oui en grat… |
| Image | Stability AI — Stable Image Core | 0,0315 | n. m. | 150 requêtes … | non · non trouvé | Oui par défaut, opt-out possible |
| Image | Stability AI — Stable Image Ultra | 0,0840 | n. m. | 150 requêtes … | non · non trouvé | Oui par défaut, opt-out possible |
| Image | OpenAI — gpt-image-1-mini (medium) | 0,0115 | n. m. | Non trouvé (g… | non · non trouvé | Non par défaut |
| Vidéo | Runway — gen4_turbo | 0,2500 | n. m. | Pas de limite… | non · non trouvé | non trouvé |
| Vidéo | Google (Gemini API) — gemini-omni-1.1-flash (720p) | 0,5000 | n. m. | Palier 1 : 10… | non · Oui (Proces… | Non en offre payante |
| TTS | Mistral AI — voxtral-mini-tts-3-0 | 0,0052 | n. m. | Non publié (d… | oui · Oui | Opt-out via Admin panel › Privacy |
| TTS | Microsoft Azure AI Speech — Neural TTS (S1, West Europe) | 0,0060 | n. m. | 30 transactio… | oui · non trouvé | non trouvé |
| TTS | OpenAI — tts-1 | 0,0060 | n. m. | Non trouvé (g… | non · non trouvé | Non par défaut |
| TTS | ElevenLabs — Flash / Turbo | 0,0160 | n. m. | Concurrence f… | non · Oui | non trouvé |
| Son | ElevenLabs — Sound Effects | 0,0400 | n. m. | Concurrence f… | non · Oui | non trouvé |
| Son | Stability AI — Stable Audio 3.0 | 0,0800 | n. m. | 150 requêtes … | non · non trouvé | Oui par défaut, opt-out possible |
| Son | Bibliothèque interne (sons CC0 par émotion) — 6 boucles pré-composées | 0,0000 | local | Aucun | oui · Sans objet | Sans objet |

**Mesure réelle** (local) — `faster_whisper_selfhosted` : 10 appels, p50 3,39 s, p95 3,81 s, premier segment p50 2,25 s, WER 13,2 % (latency_local_20261106T104153Z.csv) ; fichier `summary_local_20261106T104153Z.csv`.

ᴱ prix ESTIMÉ (non publié en clair, méthode dans le classeur) · NP : non publié (auto-hébergé, coût d'infrastructure) · *n. m.* = NON MESURÉ — mock : aucune latence mesurée faute de clé, la colonne reste vide de chiffre.

| Scénario | $/rêve | $/jour | $/mois | $/an | $/mois bêta | ≤ 0,05 $ (CS-03) |
|---|---|---|---|---|---|---|
| S1 MVP retenu ᴱ | 0,0185 | 0,185 | 5,54 | 67,36 | 8,30 | oui |
| S2 R2 (+ lecture vocale) ᴱ | 0,0237 | 0,237 | 7,10 | 86,34 | 10,64 | oui |
| S3 Montée en qualité FLUX.2 [pro] ᴱ | 0,0353 | 0,353 | 10,58 | 128,68 | 15,86 | oui |
| S4 Ambiance générée (ElevenLabs) ᴱ | 0,0637 | 0,637 | 19,10 | 232,34 | 28,64 | non |
| S5 Fournisseurs US | 0,0960 | 0,960 | 28,81 | 350,53 | 43,22 | non |
| S6 R3 micro-vidéo ᴱ | 0,2737 | 2,736 | 82,10 | 998,84 | 123,14 | non |

ᴱ contient au moins un prix ESTIMÉ (FLUX.2, non publié en clair). Mois = 30 jours (H9), an = 365 jours. Bêta : 30 utilisateurs × 0,5 rêve/jour (H10, H11 ESTIMÉ) = 15 rêves/jour.
