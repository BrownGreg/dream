# ADR-006 — Objectifs de niveau de service (SLO)

- **Statut** : accepté, cibles à confirmer par la campagne `--live` · 2026-11-06
- **Compétence** : C1-3 · **Liens** : CS-02, CS-05, ENF-01 à ENF-05, ENF-11, KPIs K1 et K4

## Contexte
Les critères de succès fixent p95 bout-en-bout ≤ 30 s (CS-02) et ≥ 98 % de rêves aboutis (CS-05). Aucune latence fournisseur n'est encore mesurée (pas de clé au moment de la rédaction) : les budgets par étape ci-dessous sont des **cibles** de conception, à réviser après la première campagne `run_latency.py --live`.

## Décision
| SLO | Indicateur (SLI) | Cible | Fenêtre | Exigence |
|---|---|---|---|---|
| Accusé de réception | p95 de `POST /v1/dreams` → 202, hors transfert | ≤ 1 s | 7 j | ENF-04 |
| Transcription | p95 durée appel STT (récit ≤ 90 s) | ≤ 8 s | 7 j | ENF-01 |
| Analyse LLM | p95 durée appel LLM | ≤ 4 s | 7 j | — |
| Image | p95 durée génération + copie | ≤ 15 s | 7 j | ENF-02 |
| **Première image affichée** | p95 fin d'envoi → image visible | **≤ 30 s** | 7 j | ENF-11 |
| Fiabilité | rêves `failed` / rêves soumis | ≤ 2 % | 30 j | ENF-03 |
| Disponibilité | requêtes API non-5xx / requêtes | ≥ 99,5 % | 30 j | ENF-05 |

Budget d'erreur : 0,5 % de disponibilité = 3 h 36 min d'indisponibilité par mois de 30 jours. Budget épuisé → gel des déploiements non correctifs jusqu'au mois suivant.

## Conséquences
- Les budgets par étape totalisent 28 s (1 + 8 + 4 + 15) et laissent 2 s pour l'attente en file et l'intervalle de sondage. Si la campagne live les contredit, on révise CS-02 dans cet ADR plutôt que de masquer l'écart.
- Chaque étape est tracée (`api_calls.latency_ms`, span OpenTelemetry) : les SLI se calculent sans instrumentation supplémentaire.
