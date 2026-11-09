# ADR-005 — Son : bibliothèque d'ambiances au MVP, Voxtral TTS en R2, vidéo reportée en R3

- **Statut** : accepté · 2026-11-02 (chiffres mis à jour le 2026-11-06 après ADR-004 révisé)
- **Compétence** : C1-2 · **Liens** : US-13, US-20, onglets TTS, Ambiance, Vidéo, « Coût 10 rêves-jour »

## Contexte
Le sujet demande « image (ou micro-vidéo) + ambiance sonore ». Trois briques possibles : ambiance (sons d'atmosphère), voix lisant le résumé (TTS), micro-vidéo.

## Options et coûts par rêve (scénarios du classeur)
| Scénario | Contenu | $/rêve | $/mois (10 rêves/j) |
|---|---|---|---|
| S1 MVP | image + ambiance **bibliothèque** (6 boucles CC0, une par émotion) | 0,0185 | 5,54 |
| S2 R2 | S1 + lecture du résumé par **Voxtral TTS** (H6 = 400 car.) | 0,0237 | 7,10 |
| S4 | S2 + ambiance **générée** ElevenLabs (20 s) | 0,0637 | 19,10 |
| S6 R3 | S2 + micro-vidéo **Runway gen4_turbo** 5 s | 0,2737 | 82,10 |

TTS comparés : Voxtral TTS 13 $/M car. (UE, 4 voix FR) · Azure Neural 15 $/M (région West Europe) · OpenAI tts-1 15 $/M (US) · ElevenLabs Flash 40 $/M (US). Ambiances générées : ElevenLabs 0,04 $/rêve, Stable Audio 0,08 $/rêve.

## Décision
- **MVP** : ambiance tirée d'une bibliothèque interne de 6 boucles CC0 indexées par émotion — coût marginal nul, aucune donnée transmise.
- **R2** : Voxtral TTS (même contrat et même DPA que STT/LLM), voix française « Marie ».
- **Ambiance générée** : écartée — elle multiplie le coût par rêve par 2,7 (S4 vs S2) et ajoute un sous-traitant américain sans bénéfice prouvé.
- **Micro-vidéo** : *Could* en R3 (US-20), à la demande uniquement — 11,5 × le coût de S2 ; la génération systématique ferait sortir CS-03 de sa cible.

## Conséquences
- La promesse « ambiance sonore » est tenue dès le MVP sans dépense ni transfert.
- Azure Neural TTS reste le repli TTS (région UE, aucune conservation en temps réel).
- La vidéo sera réévaluée en R3 sur les prix du moment (marché très mouvant).
