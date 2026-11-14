# Fiche 3 — Story : client résilient, journal des coûts et coupe-circuit budgétaire

| | |
|---|---|
| Ticket | DREAM-5 · story bloc 1 US-08 · décision ADR-009 |
| PR | [#10](https://github.com/BrownGreg/dream/pull/10) |
| Fichiers | `dreams/services/http.py`, `budget.py`, `pricing.py`, `errors.py`, modèle `ApiCall` |
| Schéma | [`docs/diagrams/coupe_circuit.svg`](../diagrams/coupe_circuit.svg) |

## Besoin

Le sujet plafonne les dépenses API à **20 €** et exige que ce plafond soit appliqué par le code. Il exige aussi des délais, des retries et la gestion des quotas. Le bloc 1 imposait en plus : aucun retry sur une erreur 4xx non transitoire, et un journal de chaque appel pour calculer les SLO et le coût réel.

## Conception

Un **seul point de passage**, `resilient_call(ctx, fn, estimated_units, billed_units)`, utilisé par tous les adapters (réels **et** fake). L'adapter ne s'occupe que du protocole du fournisseur ; le client se charge du reste :

```python
def attempt_once(n):
    budget.ensure_budget(estimated_cost)          # 1. coupe-circuit AVANT chaque tentative
    try:
        result = fn()                              # 2. appel, délai fixé par l'adapter
    except ProviderError as exc:
        timed_out = isinstance(exc, ProviderTimeoutError)
        journal(n, _outcome(exc), …,               # 3. échec journalisé ;
                cost_usd=estimated_cost if timed_out else 0)   # délai dépassé = compté facturé
        raise
    units = billed_units(result) if billed_units else estimated_units
    journal(n, "ok", …, cost_usd=pricing.cost_usd(…, units))  # 4. coût mesuré dans la réponse
    return result

Retrying(stop=stop_after_attempt(attempts),        # 3 par défaut
         wait=_wait,                               # 1 s × 2^n, ≥ Retry-After, ≤ 30 s
         retry=retry_if_exception(_is_transient))  # 408, 429, 5xx, délai — jamais 4xx ni refus
```

Choix à expliquer :

- **Le budget est vérifié avant chaque tentative, retries compris.** Un retry qui ferait dépasser le plafond est refusé.
- **Un délai dépassé est compté comme facturé.** La requête a pu aboutir chez le fournisseur ; sous-estimer le coût serait le mauvais côté de l'erreur.
- **Coût mesuré quand c'est possible.** `billed_units` lit les minutes Voxtral, les jetons Mistral et les crédits BFL dans la réponse ; l'estimation ne sert qu'avant l'appel.
- **Coupe-circuit à 15 € et non 20 €.** La marge de 5 € couvre l'écart entre estimé et facturé et les appels en vol (ADR-009).
- **Prix centralisés** dans `pricing.py`, avec source, date et statut (SOURCÉ, ESTIMÉ, NON PUBLIÉ). Un modèle sans prix est refusé (`test_modele_sans_prix_refuse`).
- **Utilisateur pseudonymisé** dans `ApiCall` (HMAC-SHA256 dérivé de `SECRET_KEY`). Le coût reste attribuable après la suppression d'un compte, sans donnée personnelle.

## Tests (couverture 100 % sur `http.py`, `errors.py`, `budget.py`, `pricing.py`)

| Comportement | Test |
|---|---|
| succès : coût et latence journalisés | `test_succes_premier_essai_journalise_cout_et_latence` |
| unités facturées lues dans la réponse | `test_unites_facturees_lues_dans_la_reponse` |
| 429 puis succès, `Retry-After` respecté | `test_429_puis_succes_deux_lignes_et_respect_du_retry_after` |
| 5xx rejoué jusqu'à épuisement | `test_500_rejoue_jusqu_a_epuisement_puis_releve_l_erreur` |
| 4xx jamais rejoué | `test_4xx_non_passagere_jamais_rejouee` (paramétré) |
| délai dépassé : rejoué et facturé | `test_delai_depasse_rejoue_et_compte_comme_facture` |
| refus de sécurité : non rejoué | `test_refus_de_securite_non_rejoue_et_trace` |
| coupe-circuit : aucun appel réseau | `test_coupe_circuit_bloque_sans_appeler_le_fournisseur` |
| égalité exacte au plafond (incident n° 3) | `test_depassement_atteint` |

## Alternatives écartées

| Alternative | Pourquoi non |
|---|---|
| Retries des SDK fournisseurs | comportement différent par SDK, invisible pour le journal ; les vues ne doivent pas dépendre d'un SDK |
| Disjoncteur classique (`pybreaker`), qui coupe sur un taux d'erreur | protège contre une panne, pas contre une dépense : les deux besoins sont distincts |
| Contrôle du budget une fois par rêve | un rêve fait 4 à 6 appels hors retries (transcription, émotion avec repli éventuel, prompt, image, reformulation éventuelle) ; le dépassement se jouerait au milieu du traitement |
| Réservation du coût avant l'appel, puis ajustement | plus exact face aux appels concurrents, mais plus complexe ; la marge de 5 € absorbe ce risque à l'échelle de la bêta |

## Impact

- **Performance** : une agrégation `SUM(cost_usd)` sur `ApiCall` avant chaque tentative. Coût non mesuré en production ; la table compterait quelques milliers de lignes au plafond du budget (environ 850 rêves). Piste au-delà : un total maintenu dans une ligne dédiée.
- **Lisibilité** : un adapter réel tient en 77 à 118 lignes, sans logique de retry ni de coût.
- **Testabilité** : les adapters fake passent par ce même client. Le pipeline complet, les pannes simulées (`AI_FAKE_FAIL_STEPS`) et le coupe-circuit sont donc testés en CI et en charge **sans dépenser**.
