# Test de charge — résultats

Paliers de 90 s : 5 → 20 → 50 utilisateurs virtuels (attente de 2 à 5 s entre deux actions). Adapters **fake** : latence simulée de 1000 ms par appel fournisseur, 4 appels par rêve. 1 processus `db_worker`, gunicorn 2 processus synchrones, PostgreSQL 17. Machine : GitHub Actions ubuntu-latest (2 vCPU, 7 Go).

## Requêtes HTTP par palier

Percentiles calculés sur les requêtes du palier seulement. « pipeline : bout en bout » = de l'envoi à la page terminée, vu par l'utilisateur (polling toutes les 2 s), compté dans le palier où il se termine.

| Palier | Requête | Nombre | Échecs | p50 | p95 | Req/s (moyenne) |
|---|---|---|---|---|---|---|
| 5 utilisateurs | connexion (GET) | 5 | 0 | 5 ms | 126 ms | 0.06 |
| 5 utilisateurs | connexion (POST) | 5 | 0 | 276 ms | 279 ms | 0.06 |
| 5 utilisateurs | détail d'un rêve | 12 | 0 | 14 ms | 22 ms | 0.13 |
| 5 utilisateurs | enregistrement (GET) | 11 | 0 | 8 ms | 10 ms | 0.12 |
| 5 utilisateurs | envoi d'un rêve | 11 | 0 | 50 ms | 158 ms | 0.12 |
| 5 utilisateurs | historique | 43 | 0 | 14 ms | 16 ms | 0.48 |
| 5 utilisateurs | historique filtré | 16 | 0 | 12 ms | 42 ms | 0.18 |
| 5 utilisateurs | pipeline : bout en bout | 10 | 0 | 6 080 ms | 8 117 ms | 0.11 |
| 5 utilisateurs | statistiques | 18 | 0 | 13 ms | 15 ms | 0.20 |
| 5 utilisateurs | statut (polling) | 34 | 0 | 10 ms | 19 ms | 0.38 |
| **5 utilisateurs** | **toutes les requêtes HTTP** | **155** | **0 (0.0 %)** | **13 ms** | **59 ms** | **1.72** |
| 20 utilisateurs | connexion (GET) | 15 | 0 | 5 ms | 7 ms | 0.17 |
| 20 utilisateurs | connexion (POST) | 15 | 0 | 442 ms | 485 ms | 0.17 |
| 20 utilisateurs | détail d'un rêve | 17 | 0 | 14 ms | 23 ms | 0.19 |
| 20 utilisateurs | enregistrement (GET) | 34 | 0 | 8 ms | 227 ms | 0.38 |
| 20 utilisateurs | envoi d'un rêve | 34 | 0 | 49 ms | 77 ms | 0.38 |
| 20 utilisateurs | historique | 152 | 0 | 14 ms | 18 ms | 1.69 |
| 20 utilisateurs | historique filtré | 49 | 0 | 12 ms | 16 ms | 0.54 |
| 20 utilisateurs | pipeline : bout en bout | 22 | 0 | 18 152 ms | 34 217 ms | 0.24 |
| 20 utilisateurs | statistiques | 52 | 0 | 13 ms | 23 ms | 0.58 |
| 20 utilisateurs | statut (polling) | 297 | 0 | 9 ms | 12 ms | 3.30 |
| **20 utilisateurs** | **toutes les requêtes HTTP** | **665** | **0 (0.0 %)** | **11 ms** | **50 ms** | **7.39** |
| 50 utilisateurs | connexion (GET) | 30 | 0 | 185 ms | 745 ms | 0.33 |
| 50 utilisateurs | connexion (POST) | 30 | 0 | 1 213 ms | 2 275 ms | 0.33 |
| 50 utilisateurs | détail d'un rêve | 37 | 0 | 13 ms | 19 ms | 0.41 |
| 50 utilisateurs | enregistrement (GET) | 49 | 0 | 8 ms | 254 ms | 0.54 |
| 50 utilisateurs | envoi d'un rêve | 49 | 0 | 52 ms | 178 ms | 0.54 |
| 50 utilisateurs | historique | 186 | 0 | 13 ms | 276 ms | 2.07 |
| 50 utilisateurs | historique filtré | 93 | 0 | 11 ms | 908 ms | 1.03 |
| 50 utilisateurs | pipeline : bout en bout | 22 | 0 | 53 761 ms | 72 400 ms | 0.24 |
| 50 utilisateurs | statistiques | 83 | 0 | 13 ms | 241 ms | 0.92 |
| 50 utilisateurs | statut (polling) | 1312 | 0 | 10 ms | 18 ms | 14.58 |
| **50 utilisateurs** | **toutes les requêtes HTTP** | **1869** | **0 (0.0 %)** | **10 ms** | **355 ms** | **20.77** |

## File de tâches et worker

- 5 utilisateurs : file max **1** tâches en attente, plus longue attente **2 s**.
- 20 utilisateurs : file max **12** tâches en attente, plus longue attente **29 s**.
- 50 utilisateurs : file max **39** tâches en attente, plus longue attente **158 s**.
- Rêves traités : **94** (0 en échec), débit **13.4 rêves/min**.
- Attente en file : p50 50 875 ms, p95 156 071 ms.
- Traitement par le worker : p50 4 079 ms, p95 4 103 ms.
- Mise en file → terminé : p50 54 954 ms, p95 160 149 ms.
