# ADR-009 — Évolution : budget API de production plafonné à 20 €, coupe-circuit à 15 €

- **Statut** : accepté · 2026-11-09
- **Type** : Évolution (révise ADR-007)
- **Liens** : ADR-007, ADR-004, ADR-008, table `ApiCall`, page `/ops`

## Contexte
ADR-007 dimensionnait un budget **mensuel** de bêta de 25 $ (alerte 80 %, coupe-circuit 100 %). Le sujet de production fixe une contrainte différente : **20 € au total** de dépenses API en production. Les prix fournisseurs sont exprimés en dollars (onglet `Sources` du benchmark, prix ESTIMÉ pour FLUX.2).

## Décision
| Paramètre | Valeur par défaut | Variable | Justification |
|---|---|---|---|
| Plafond dur (sujet) | 20 € cumulés | — | Contrainte du sujet, jamais atteinte grâce au coupe-circuit |
| Coupe-circuit | **15 € cumulés** | `AI_BUDGET_EUR` | 5 € de marge pour l'écart entre coût estimé et facturé, et pour les appels en vol au moment de la coupure |
| Alerte | 80 % du coupe-circuit (12 €) | `AI_BUDGET_ALERT_RATIO` | Visible sur `/ops` et dans les logs |
| Taux de conversion USD → EUR | **1,0** | `AI_USD_EUR_RATE` | Prudent : surestime le coût en euros tant que le dollar vaut moins d'un euro. À remplacer par un taux daté (source BCE) si l'on veut la valeur exacte |
| Quota par utilisateur | 5 rêves / jour | `AI_USER_DAILY_DREAMS` | Repris d'ADR-007 |
| Générations d'image par rêve | 2 | `AI_MAX_IMAGE_ATTEMPTS` | Repris d'ADR-007 (génération initiale + une régénération) |

**Application dans le code, pas seulement dans la doc :**
1. Chaque appel externe crée une ligne `ApiCall` (fournisseur, modèle, étape, durée, statut HTTP, unités facturées, coût estimé, `dream_id`), y compris les échecs et les retries.
2. Avant tout appel payant, le client résilient compare la somme des coûts `ApiCall` au coupe-circuit ; au-delà, il lève `BudgetExceededError` sans appeler le fournisseur.
3. Dégradation, pas panne : budget épuisé, la transcription bascule sur un message clair, l'émotion sur le lexique local (gratuit) et l'image sur un placeholder « image indisponible ». L'utilisateur garde ce qui a déjà réussi (état `partial`).
4. Les tests, la CI et les tests de charge tournent en `AI_MODE=fake` : aucun appel réel, aucun coût.

## Conséquences
- Le coût réel par rêve et la projection mensuelle du rapport sont calculés depuis `ApiCall`, pas depuis les hypothèses du bloc 1.
- Le budget est cumulé sur toute la durée de production (pas de remise à zéro mensuelle) ; une remise à zéro exigerait un nouvel ADR.
- Les prix unitaires vivent dans une configuration unique du code, avec leur source et leur date ; un prix ESTIMÉ y reste marqué comme tel.
