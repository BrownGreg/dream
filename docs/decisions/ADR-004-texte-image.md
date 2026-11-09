# ADR-004 — Génération d'image : FLUX.2 [klein] (endpoint UE), montée en [pro] conditionnée, repli Nano Banana 2.1

- **Statut** : accepté sous conditions contractuelles · 2026-11-06 (révise la version du 2026-11-02 qui retenait [pro])
- **Compétence** : C1-2, C1-3 · **Liens** : US-07, US-11, CS-06, R-03, R-05, onglets « Texte-image » et « Scoring »

## Contexte
L'image est le poste de coût dominant (≈ 80 % du coût d'un rêve du scénario S1). Le fournisseur reçoit le prompt visuel reformulé (ADR-003), jamais la transcription.

## Options (H4 = 1 image ≈ 1 MP, H8 = 5 % de régénération)
| Option | $/rêve | Statut prix | Données | Entraînement | DPA | Score /5 (rang) |
|---|---|---|---|---|---|---|
| **BFL FLUX.2 [klein]** | 0,0147 | ESTIMÉ | `api.eu.bfl.ai`, routage UE | oui par défaut, opt-out par e-mail | non trouvé | 3,45 (1) |
| OpenAI gpt-image-1-mini | 0,0115 | SOURCÉ | US | non par défaut | non trouvé | 2,88 (2) — fin de vie annoncée, écarté |
| Google Nano Banana 2.1 (payant) | 0,0353 | SOURCÉ | « any country » | non (payant) | oui | 2,77 (3) |
| BFL FLUX.2 [pro] | 0,0315 | ESTIMÉ | idem [klein] | idem | non trouvé | 2,74 (4) |
| Stability Image Core | 0,0315 | SOURCÉ | US | oui par défaut, opt-out | non trouvé | 1,74 (5) |
| Stability Image Ultra | 0,0840 | SOURCÉ | US | idem | non trouvé | 1,27 (6) |

Le score pondéré (coût 25, latence 20, WER 20, RGPD 25, intégration 10) ne porte que sur les critères renseignés ; la qualité visuelle n'est pas encore mesurée.

## Décision
**FLUX.2 [klein]** via `api.eu.bfl.ai` pour le MVP : premier du scoring, seul acteur européen (BFL GmbH) avec routage limité à l'UE, 53 % moins cher que [pro].
**Montée en [pro]** (scénario S3, +0,0168 $/rêve) si le test de fidélité du Sprint 3 (section 8 du cadrage) donne [klein] sous 4/5 et un gain de [pro] supérieur à 0,5 point : la qualité est le seul argument de [pro] et elle doit être prouvée, pas supposée. CS-06 confirme ensuite le choix en bêta.
**Conditions bloquantes avant la bêta** (Definition of Done de la release MVP) :
1. tarif confirmé au calculateur officiel (aujourd'hui ESTIMÉ) ;
2. opt-out d'entraînement obtenu par écrit ;
3. DPA (ou Developer Terms couvrant l'art. 28) signé.
Si l'une échoue au Sprint 2 : repli sur Nano Banana 2.1 en offre payante (DPA publié, pas d'entraînement), au prix d'un transfert hors UE à couvrir dans l'AIPD.

## Conséquences
- Interface `ImageGenerator` : changer de modèle ou de fournisseur = changer d'adapter ou de paramètre, pas de code métier.
- Les images BFL expirent après 10 min : l'asset est copié immédiatement dans notre stockage objet (pas de diffusion directe, pas de CORS).
- Test de fidélité prévu au Sprint 3 : 5 prompts du corpus × [klein] et [pro], notation à l'aveugle (protocole en section 8).
- Refus du filtre de sécurité : rêve enregistré sans image + message (US-07, scénario 2).
