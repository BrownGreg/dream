# 4. Étude d'art et benchmark technologique

## Méthode
- **Shortlist** : 7 options STT (6 API, 1 auto-hébergée), 3 options LLM/émotion (dont 1 auto-hébergée), 6 générateurs d'image, 2 générateurs vidéo, 4 TTS, 3 sources d'ambiance — au moins une option hébergée dans l'UE par catégorie.
- **Sources** : uniquement les pages officielles des fournisseurs (prix, DPA, conditions, politique de données), consultées le 2026-11-02 ; chaque URL figure dans l'onglet `Sources` de l'annexe `benchmark.xlsx`. Deux valeurs ne sont pas publiées en clair (FLUX.2) : elles sont marquées ESTIMÉ avec leur méthode.
- **Coût sur 10 rêves/jour** : hypothèses explicites et modifiables (onglet `Hypothèses`) — récit d'1 min (H1), 700/250 tokens LLM (H2/H3), une image 1 MP (H4), 400 caractères lus (H6), 5 % de régénération (H8). Toutes les cellules de coût sont des formules.
- **Latence** : `benchmark/run_latency.py` envoie 10 à 30 appels par fournisseur sur un corpus fixe (5 récits FR synthétiques de 30 à 34 s, 5 prompts visuels), mesure le temps jusqu'au premier octet et le temps total, compte les retries à part (`tenacity`) et exporte des CSV horodatés. Le mode `--mock` valide la chaîne sans clé ; seules les mesures `--live` alimentent le classeur.
- **Qualité FR** : WER (`jiwer`) des transcriptions contre les textes de référence du corpus (`benchmark/wer.py`).

## Tableau comparatif

{{include _gen/benchmark_tables.md}}

## Lecture des résultats
1. **L'image fait le coût** : elle représente 80 % du coût d'un rêve du scénario MVP ; STT et LLM pèsent ensemble 20 %. Le choix du modèle d'image est donc le premier levier : FLUX.2 [klein] coûte 53 % de moins que [pro], qui n'a pour lui qu'une qualité non encore mesurée.
2. **Les options « sonores » génératives sont disproportionnées** : une ambiance générée multiplie le coût par rêve par 2,7 (S4 vs S2) ; une micro-vidéo de 5 s par 11,5 (S6 vs S2). D'où l'ambiance par bibliothèque au MVP et la vidéo à la demande en R3 (ADR-005).
3. **Latence et WER sont mesurés pour trois STT** (campagne `--live` du 15/11/2026 pour Voxtral Mini et Small, locale pour faster-whisper) ; les autres fournisseurs restent notés sur 3 critères sur 5 (coût, RGPD, intégration). Voxtral Mini a la meilleure latence (p95 1,44 s), Voxtral Small le meilleur WER (0,8 % contre 1,3 %) ; avec un WER bien sous le seuil de repli de 10 % (ADR-002), le choix de Voxtral Mini est confirmé.
4. **Le RGPD départage plus que le prix** : en STT, cinq offres sont à moins de 0,001 $ d'écart ; seule Voxtral combine hébergement UE par défaut, DPA publié et opt-out d'entraînement documenté.
5. **Fin de vie** : trois modèles OpenAI du périmètre (gpt-4o-transcribe, gpt-image-1-mini, gpt-4o-mini-tts) sont marqués *Deprecated* et gpt-image-1 a été arrêté le 23/10/2026 (pages modèles OpenAI consultées le 2026-11-02) — le choix doit donc rester réversible (ports/adapters, section 6 des spécifications).

## Choix retenus (détail dans les ADR)

| Étape | Choix | Repli | ADR |
|---|---|---|---|
| Transcription | Mistral Voxtral Mini Transcribe 3 | Voxtral Small (si WER > 10 %) · faster-whisper auto-hébergé | ADR-002 |
| Prompt visuel + émotion | Mistral Small 4, sortie JSON validée par schéma | mDeBERTa zero-shot (émotion seule) | ADR-001, ADR-003 |
| Image | FLUX.2 [klein], endpoint UE — sous 3 conditions (prix, opt-out, DPA) | [pro] si le test de fidélité (Sprint 3, section 8) est défavorable · Nano Banana 2.1 (payant) | ADR-004 |
| Ambiance | Bibliothèque CC0, 6 boucles par émotion | — | ADR-005 |
| Lecture vocale (R2) | Voxtral TTS, voix française | Azure Neural TTS (région UE) | ADR-005 |
| Budget | 25 $/mois en bêta (15 rêves/jour estimés), alerte 80 %, coupe-circuit image à 100 % | — | ADR-007 |

Un seul fournisseur principal (Mistral) pour STT, LLM et TTS : un DPA, un registre de sous-traitance simple, mais une dépendance concentrée — risque R-06, couvert par les replis ci-dessus.

## KPIs retenus

| ID | KPI | Cible | Mesuré en pré-production ? |
|---|---|---|---|
| K1 | Latence p95 bout-en-bout (fin d'envoi → image affichée) | ≤ 30 s (CS-02) | Partiel : transcription 1,44 s + analyse LLM 1,56 s (p95, campagne live du 15/11/2026) ; image non mesurée (pas de clé T2I) |
| K2 | Coût API par rêve | ≤ 0,05 $ (CS-03) | Calculé : 0,0185 $ (S1, contient un prix ESTIMÉ) |
| K3 | WER sur le corpus FR | ≤ 10 % | Oui : Voxtral Mini 1,3 %, Voxtral Small 0,8 % (live, 15/11/2026) ; faster-whisper `small` local 13,2 % ; corpus de voix de synthèse espeak |
| K4 | Taux d'échec API après retries | ≤ 2 % | Partiel : 0 échec sur 40 appels Mistral, aucun retry (live, 15/11/2026) ; image non mesurée |
| K5 | Taux de rejet par le filtre de sécurité image | ≤ 5 % | Non — clé T2I requise |
| K6 | Part des traitements effectués dans l'UE | 100 % au MVP | Par construction du scénario S1 |
| K7 | Sorties LLM conformes au schéma | ≥ 99 % | 10 sur 10 (Mistral Small 4, live, 15/11/2026) : échantillon trop petit pour conclure sur 99 % |
| K8 | Émotions non corrigées par l'utilisateur | ≥ 80 % | En bêta (R2) |

Les cibles sont des hypothèses de pilotage reliées aux critères de succès (K1 ↔ CS-02, K2 ↔ CS-03, K4 ↔ CS-05, K6 ↔ CS-04) ; les seuils K3, K5, K7 et K8 sont des choix de conception, révisés après la première campagne de mesure.
