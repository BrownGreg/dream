# 8. Plan qualité

## Métriques cibles
| Métrique | Cible | Contrôle | État en pré-production |
|---|---|---|---|
| Couverture de `src/` (lignes + branches) | ≥ 80 % | `pytest --cov-fail-under=80` en CI | 98,0 % |
| Lint PEP 8 + docstrings Google | 0 erreur | `ruff check`, `ruff format --check` | 0 |
| Typage | 0 erreur, mode strict | `mypy --strict src` | 0 (17 fichiers) |
| Complexité cyclomatique | ≤ 10 par fonction | règle ruff `C901` | respectée |
| Exigences couvertes par un test | 100 % des EXF, ENF mesurables | `tracabilite.csv` | 30/34 ; 3 scénarios écrits pour des stories non implémentées (R2/R3), ENF-05 mesurée en production |
| Scénarios d'acceptation exécutés | 100 % des stories implémentées | `pytest tests/features` | 23 passés, 3 ignorés et signalés (US-18, US-20, US-23) |
| Vulnérabilités des dépendances | 0 critique | `pip-audit` en CI (`ci.yml`) | étape définie ; première exécution à la création du dépôt distant |

## Revue de code
- **Branche par story** (`feat/US-xx-…`), commits conventionnels, pull request liée au ticket Jira.
- **Fusion** si CI verte **et** une relecture approuvée. Travail individuel : la relecture est faite par un pair de promotion une fois par sprint et, entre-temps, par une relecture différée de 24 h avec la checklist (jamais le jour même de l'écriture).
- **Checklist PR** : ID de story et d'exigence cités ; tests ajoutés (Gherkin si critère d'acceptation, unitaire sinon) ; aucun secret, aucun contenu de rêve dans les journaux ; messages d'erreur issus de `errors.py` ; ADR créé si une décision structurante change ; documentation régénérée (`tools/*.py`).

## Definition of Ready / Definition of Done
| DoR — une story entre en sprint si… | DoD — une story est terminée si… |
|---|---|
| elle est estimée en points (Fibonacci) | ses scénarios Gherkin passent en CI |
| ses critères d'acceptation Gherkin sont écrits | couverture ≥ 80 %, ruff et mypy à 0 |
| ses exigences EXF/ENF sont liées | relecture approuvée, PR fusionnée |
| le contrat d'API ou l'écran est décrit | démontrée en revue de sprint |
| aucune dépendance fournisseur ou juridique n'est ouverte | journaux vérifiés sans contenu de rêve ; registre des sous-traitants à jour (CS-04) |

## Stratégie BDD / TDD
- **BDD** : les critères d'acceptation vivent dans `stories.toml` et sont générés en `.feature` (`# language: fr`) exécutés par `pytest-bdd` ; chaque scénario porte l'étiquette de sa story. Une story sans scénario vert n'est pas « Done ».
- **TDD** : tests unitaires écrits avant les services (validation audio, pipeline, dépôt) ; propriétés vérifiées par `hypothesis` (règle de durée de l'audio) ; adapters réels testés contre une API simulée (`respx`), sans réseau.
- **Pyramide actuelle** : 54 tests unitaires et d'intégration, 23 scénarios BDD, 8 tests d'interface (`streamlit.testing.v1.AppTest`), 4 tests budget et journalisation.

## Plan de test de charge
| Élément | Choix |
|---|---|
| Cible | Bouchon de l'API cible (`tests/load/stub_api.py`) reproduisant le contrat `/v1/dreams`, les budgets de durée d'ADR-006 et la limite de 24 générations d'image simultanées de BFL ; en production, l'API réelle en préproduction |
| Scénario | Un utilisateur virtuel envoie un récit, interroge l'état toutes les 2 s, publie la durée « fin d'envoi → done » (`tests/load/locustfile.py`) |
| Paliers | 1 → 10 → 50 → 100 rêves simultanés, 60 s chacun |
| Métriques | p50/p95 du parcours, taux d'échec, réponses 429 (quota) et 503 (file pleine) comptées à part, longueur de file |
| Critères de réussite | p95 ≤ 30 s (ENF-11) et échecs ≤ 2 % (ENF-03) jusqu'à 50 rêves simultanés (ENF-12) ; au-delà, refus explicites `503 busy` avec `retry_after` (comptés à part) et aucune autre erreur serveur |
| Goulot attendu | L'attente des places de génération d'image (24), pas le CPU de l'API : la réponse est d'ajouter des workers seulement jusqu'à la limite fournisseur, puis la file absorbe |
| État | Chaîne validée en mode réduit (durées simulées ×0,02) ; campagne complète à mener au Sprint 4 sur la préproduction |

## Test de fidélité des images (ADR-004)
5 prompts du corpus × FLUX.2 [klein] et [pro], images présentées à l'aveugle et dans un ordre aléatoire à 5 personnes, note 1–5 à « l'image correspond au récit » ; [pro] est retenu si son gain moyen dépasse 0,5 point et que [klein] reste sous 4/5 (CS-06).
