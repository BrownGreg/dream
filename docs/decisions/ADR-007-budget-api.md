# ADR-007 — Budget API, seuil d'alerte et coupe-circuit

- **Statut** : accepté · 2026-11-06 (révisé après relecture : dimensionnement sur l'usage de la bêta)
- **Compétence** : C1-2, C1-3 · **Liens** : CS-03, ADR-004, ENF-06, R-07, onglet « Coût 10 rêves-jour »

## Contexte
Le sujet impose l'analyse à 10 rêves/jour : 5,54 $/mois en S1 (FLUX.2 [klein]). La bêta compte 30 utilisateurs (H10) ; à 0,5 rêve par utilisateur et par jour (H11, ESTIMÉ), elle produit 15 rêves/jour : 8,30 $/mois en S1, 10,64 $ en S2 (R2, lecture vocale), 15,86 $ en S3 (montée en [pro]). Tous contiennent un prix ESTIMÉ (FLUX.2). Le quota maximal théorique (30 × 5 rêves/jour) serait de 83 $/mois en S1 : c'est le coupe-circuit qui protège ce cas.

## Décision
| Paramètre | Valeur | Justification |
|---|---|---|
| Budget mensuel bêta | **25 $** | Couvre S3 à l'usage de la bêta (15,86 $) avec 58 % de marge, et S2 2,3 fois : ni la lecture vocale ni la montée en [pro] ne demandent de nouvel arbitrage ; absorbe une erreur sur le prix ESTIMÉ ou un usage plus élevé que H11 |
| Alerte | 80 % (20 $) | Notification au PO ; revue de l'usage par utilisateur et de H11 |
| Coupe-circuit | 100 % (25 $) | Génération d'image suspendue ; transcription, émotion et ambiance continuent ; message « image indisponible ce mois-ci » |
| Quota par utilisateur | 5 rêves / jour | Empêche un compte de consommer le budget de tous ; au-delà, HTTP 429 avec date de réinitialisation |
| Plafond par rêve | 2 générations d'image | Borne les régénérations (H8) |

Le coût est calculé à chaque appel (`api_calls.cost_usd`, prix lus dans une configuration générée depuis `benchmark/catalog.toml`) et agrégé par jour.

## Conséquences
- Le service reste utile même budget épuisé (dégradation gracieuse, pas de panne).
- Toute révision des prix du catalogue met à jour le budget prévisionnel sans retoucher le code.
