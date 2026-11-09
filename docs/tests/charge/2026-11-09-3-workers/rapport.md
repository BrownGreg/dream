# Test de charge — résultats

Paliers de 90 s : 5 → 20 → 50 utilisateurs virtuels (attente de 2 à 5 s entre deux actions). Adapters **fake** : latence simulée de 1000 ms par appel fournisseur, 4 appels par rêve. 3 processus `db_worker`, gunicorn 2 processus synchrones, PostgreSQL 17. Machine : GitHub Actions ubuntu-latest (2 vCPU, 7 Go).

## Requêtes HTTP par palier

Percentiles calculés sur les requêtes du palier seulement. « pipeline : bout en bout » = de l'envoi à la page terminée, vu par l'utilisateur (polling toutes les 2 s), compté dans le palier où il se termine.

| Palier | Requête | Nombre | Échecs | p50 | p95 | Req/s (moyenne) |
|---|---|---|---|---|---|---|
| 5 utilisateurs | connexion (GET) | 5 | 0 | 5 ms | 139 ms | 0.06 |
| 5 utilisateurs | connexion (POST) | 5 | 0 | 228 ms | 263 ms | 0.06 |
| 5 utilisateurs | détail d'un rêve | 7 | 0 | 16 ms | 51 ms | 0.08 |
| 5 utilisateurs | enregistrement (GET) | 10 | 0 | 7 ms | 10 ms | 0.11 |
| 5 utilisateurs | envoi d'un rêve | 10 | 0 | 54 ms | 1 338 ms | 0.11 |
| 5 utilisateurs | historique | 39 | 0 | 14 ms | 20 ms | 0.43 |
| 5 utilisateurs | historique filtré | 20 | 0 | 10 ms | 14 ms | 0.22 |
| 5 utilisateurs | pipeline : bout en bout | 10 | 0 | 6 083 ms | 7 365 ms | 0.11 |
| 5 utilisateurs | statistiques | 21 | 0 | 12 ms | 18 ms | 0.23 |
| 5 utilisateurs | statut (polling) | 30 | 0 | 9 ms | 12 ms | 0.33 |
| **5 utilisateurs** | **toutes les requêtes HTTP** | **147** | **0 (0.0 %)** | **13 ms** | **58 ms** | **1.63** |
| 20 utilisateurs | connexion (GET) | 15 | 0 | 5 ms | 12 ms | 0.17 |
| 20 utilisateurs | connexion (POST) | 15 | 0 | 334 ms | 523 ms | 0.17 |
| 20 utilisateurs | détail d'un rêve | 66 | 0 | 16 ms | 33 ms | 0.73 |
| 20 utilisateurs | enregistrement (GET) | 39 | 0 | 8 ms | 11 ms | 0.43 |
| 20 utilisateurs | envoi d'un rêve | 39 | 0 | 64 ms | 117 ms | 0.43 |
| 20 utilisateurs | historique | 154 | 0 | 16 ms | 26 ms | 1.71 |
| 20 utilisateurs | historique filtré | 80 | 0 | 13 ms | 20 ms | 0.89 |
| 20 utilisateurs | pipeline : bout en bout | 38 | 0 | 6 097 ms | 8 161 ms | 0.42 |
| 20 utilisateurs | statistiques | 78 | 0 | 14 ms | 21 ms | 0.87 |
| 20 utilisateurs | statut (polling) | 119 | 0 | 10 ms | 17 ms | 1.32 |
| **20 utilisateurs** | **toutes les requêtes HTTP** | **605** | **0 (0.0 %)** | **15 ms** | **68 ms** | **6.72** |
| 50 utilisateurs | connexion (GET) | 30 | 0 | 15 ms | 41 ms | 0.33 |
| 50 utilisateurs | connexion (POST) | 30 | 0 | 793 ms | 997 ms | 0.33 |
| 50 utilisateurs | détail d'un rêve | 115 | 0 | 14 ms | 33 ms | 1.28 |
| 50 utilisateurs | enregistrement (GET) | 81 | 0 | 8 ms | 56 ms | 0.90 |
| 50 utilisateurs | envoi d'un rêve | 81 | 0 | 60 ms | 99 ms | 0.90 |
| 50 utilisateurs | historique | 393 | 0 | 14 ms | 55 ms | 4.37 |
| 50 utilisateurs | historique filtré | 170 | 0 | 12 ms | 65 ms | 1.89 |
| 50 utilisateurs | pipeline : bout en bout | 63 | 0 | 10 129 ms | 24 198 ms | 0.70 |
| 50 utilisateurs | statistiques | 158 | 0 | 14 ms | 58 ms | 1.76 |
| 50 utilisateurs | statut (polling) | 513 | 0 | 9 ms | 16 ms | 5.70 |
| **50 utilisateurs** | **toutes les requêtes HTTP** | **1571** | **0 (0.0 %)** | **13 ms** | **84 ms** | **17.46** |

## File de tâches et worker

- 5 utilisateurs : file max **1** tâches en attente, plus longue attente **0 s**.
- 20 utilisateurs : file max **3** tâches en attente, plus longue attente **2 s**.
- 50 utilisateurs : file max **15** tâches en attente, plus longue attente **20 s**.
- Rêves traités : **130** (0 en échec), débit **28.0 rêves/min**.
- Attente en file : p50 3 977 ms, p95 18 841 ms.
- Traitement par le worker : p50 4 098 ms, p95 4 139 ms.
- Mise en file → terminé : p50 8 066 ms, p95 22 925 ms.
