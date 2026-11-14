# Performance mesurée face aux SLO

Sources : tests de charge du 2026-11-09 ([`charge/`](charge/README.md), runs GitHub Actions `42695022252` et `42698871160`, 2 vCPU, PostgreSQL 17, gunicorn 2 processus, adapters **fake** avec 1 000 ms de latence simulée par appel), capture de `/ops` ([`captures/ops-2026-11-09-mode-fake.png`](captures/ops-2026-11-09-mode-fake.png)). Les latences **réelles** des fournisseurs restent à mesurer (Jalon B, clés d'API) : leurs lignes sont marquées NON MESURÉ.

## Temps de réponse des pages (serveur, mesuré par Locust)

Temps complet de la requête vu par le client sur la même machine (réseau local) : c'est une borne haute du TTFB serveur, sans la latence Internet.

| Page | 5 utilisateurs p50 / p95 | 50 utilisateurs, 1 worker p50 / p95 | 50 utilisateurs, 3 workers p50 / p95 |
|---|---|---|---|
| Historique | 14 / 16 ms | 13 / 276 ms | 14 / 55 ms |
| Statistiques (12 mois) | 13 / 15 ms | 13 / 241 ms | 14 / 58 ms |
| Détail d'un rêve | 14 / 22 ms | 13 / 19 ms | — |
| Enregistrement (formulaire) | 8 / 10 ms | 8 / 254 ms | — |
| Envoi d'un rêve (validation + mise en file) | 50 / 158 ms | 52 / 178 ms | 60 / 99 ms |
| Statut (polling) | 10 / 19 ms | 10 / 18 ms | — |
| Connexion (POST, hachage du mot de passe) | 276 / 279 ms | 1 213 / 2 275 ms | 793 / 997 ms |

Les valeurs « — » ne sont pas reprises ici ; elles figurent dans les rapports complets. Au palier de 5 utilisateurs avec 3 workers, le p95 de l'envoi (1 338 ms) est la valeur maximale d'un échantillon de 10, isolée : elle n'est pas retenue comme représentative.

## SLO du bloc 1 (ADR-006)

| SLO | Cible | Mesure | Statut |
|---|---|---|---|
| Accusé de réception de l'envoi | p95 ≤ 1 s | 77 à 178 ms selon le palier (1 worker) | ✅ tenu jusqu'à 50 utilisateurs |
| Bout en bout (envoi → page terminée) | p95 ≤ 30 s | 1 worker : 8,1 s (5 u.), 34,2 s (20 u.), 72,4 s (50 u.) ; 3 workers : 7,4 s, 8,2 s, 24,2 s | ⚠️ tenu jusqu'à 5 utilisateurs avec 1 worker, jusqu'à 50 avec 3 — **avec une latence simulée** |
| Transcription | p95 ≤ 8 s | NON MESURÉ (latence réelle Voxtral) | ⏳ Jalon B |
| Analyse LLM | p95 ≤ 4 s | NON MESURÉ | ⏳ Jalon B |
| Image | p95 ≤ 15 s | NON MESURÉ | ⏳ Jalon B |
| Fiabilité | ≤ 2 % de rêves `failed` | 0 / 224 rêves en charge (adapters fake) | ✅ en simulation ; à confirmer en réel |
| Disponibilité | ≥ 99,5 % de réponses non-5xx | 0 erreur sur 5 012 requêtes en charge | ✅ en charge ; la production n'a pas encore d'historique |

## Ce qu'il faut retenir

- Le serveur web répond en quelques dizaines de millisecondes ; les pics viennent de la saturation CPU des 2 vCPU du runner (connexion, pages pendant un afflux).
- Le temps de bout en bout est dominé par **l'attente en file** dès que les envois dépassent la capacité d'un worker (≈ 14,7 rêves/min avec 4 s de traitement). Ajouter des workers suffit : à 3, l'attente p95 passe de 156 s à 18,8 s.
- Avec les latences réelles des fournisseurs (cibles ADR-006 : 27 s de traitement au total), un worker traiterait 2 à 3 rêves par minute. Pour la bêta (15 rêves/jour, ADR-007), c'est largement suffisant ; un pic de plusieurs envois simultanés imposera plusieurs workers pour tenir 30 s.
