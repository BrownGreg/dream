# Fiche 2 — Bug : la supervision ne voyait pas la file de tâches

| | |
|---|---|
| Ticket | DREAM-20 (corrige DREAM-17) · incident n° 10 de [`docs/incidents.md`](../incidents.md) |
| PR | [#28](https://github.com/BrownGreg/dream/pull/28) |
| Fichiers | `dashboard/ops.py`, `tests/integration/test_observability.py` |
| Gravité | haute pour l'exploitation : `/health` et `/ops` auraient déclaré le worker « à l'heure » même arrêté |

## Symptôme

Pendant le test de charge à 50 utilisateurs, `/ops` affiche **36 tâches en attente** mais une **attente maximale de 0 s**. Les deux chiffres sont incompatibles. Les tests de `/health` (« worker en retard → `degraded` ») étaient verts.

## Méthode de debug

1. **Comparer les deux requêtes** de `queue_state()` : le compteur filtre `status="READY"` ; l'attente filtre `status="READY"` **et** `run_after <= now`. Seul le second filtre peut vider le résultat.
2. **Vérifier ce que le backend écrit** : `django-tasks-db` enregistre une tâche **sans délai** avec `run_after` à la **date maximale** (`get_date_max()`), et non « maintenant ».
3. **Lire le code du paquet** : son QuerySet fournit `ready()`, qui gère ce cas.
4. **Pourquoi les tests passaient** : la fixture créait ses tâches avec `run_after=now`, c'est-à-dire avec l'hypothèse fausse du code, et non avec le comportement réel du backend. Le test validait l'erreur.
5. **Test rouge** : fixture corrigée (`run_after=get_date_max()`) → `test_file_en_retard` et `test_health_degrade_si_le_worker_est_en_retard` rouges. Puis correctif → verts.

## Diff commenté

Avant :

```python
oldest = (
    tasks.filter(status="READY", run_after__lte=now)   # hypothèse : run_after = date de mise en file
    .order_by("enqueued_at").values_list("enqueued_at", flat=True)
)
first = oldest.first()
```

Après :

```python
# `ready()` du paquet : une tâche sans délai est stockée avec `run_after` à la date maximale
# (et non « maintenant ») ; un filtre `run_after <= now` les ignorerait toutes (incident #10).
first = DBTaskResult.objects.ready().order_by("enqueued_at").values_list("enqueued_at", flat=True).first()
```

Fixture de test, avant → après :

```python
run_after=now,              # ce que le code supposait
run_after=get_date_max(),   # ce que le backend écrit réellement
```

## Alternatives écartées

| Alternative | Pourquoi non |
|---|---|
| Corriger le filtre à la main (`run_after__lte=now` **ou** `run_after = date max`) | reproduit une règle interne du paquet ; cassera si le paquet change sa convention |
| Mesurer l'attente avec `enqueued_at` seul, sans `run_after` | compterait comme « en retard » une tâche volontairement différée |
| Laisser la fixture inchangée et ajouter un test séparé | les deux tests existants auraient continué à valider la mauvaise hypothèse |

## Impact

- **Performance** : une requête identique en coût (un `ORDER BY … LIMIT 1` sur la table des tâches).
- **Lisibilité** : le code dit ce qu'il veut (« les tâches prêtes ») au lieu de réimplémenter la règle.
- **Testabilité** : la fixture reproduit l'écriture réelle du backend ; un changement de convention du paquet ferait échouer le test.

## Ce que le bug enseigne (factuel)

Le défaut ne venait pas du code seul : la fixture partageait la même hypothèse fausse que le code. Seul un test sur de vraies données, le test de charge, l'a révélé.
