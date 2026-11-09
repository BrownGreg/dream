# Test de charge

Scénario : [`tests/load/locustfile.py`](../../../tests/load/locustfile.py). Exécution : workflow [`charge`](../../../.github/workflows/charge.yml) (à la demande : nombre de workers, latence simulée, durée des paliers). Rapport généré par [`scripts/load_report.py`](../../../scripts/load_report.py) à partir des requêtes horodatées, de l'échantillonnage de la file et de la table des tâches : aucun chiffre n'est saisi à la main.

**Toujours sur les adapters fake** : aucun appel réel, aucun coût. La latence des fournisseurs est **simulée** (1 000 ms par appel, 4 appels par rêve) ; les latences réelles sont mesurées séparément dans `ApiCall` (page `/ops`).

## Exécution du 2026-11-09 — 1 worker

Données : [`2026-11-09-1-worker/`](2026-11-09-1-worker/) (rapport, `requests.csv`, `file.csv`, statistiques Locust). Run GitHub Actions `42695022252` : PostgreSQL 17, gunicorn 2 processus synchrones, 1 `db_worker`, runner 2 vCPU / 7 Go, paliers de 90 s.

| Palier | Requêtes HTTP | Échecs | p50 | p95 | Bout en bout p50 / p95 | File max |
|---|---|---|---|---|---|---|
| 5 utilisateurs | 155 | 0 | 13 ms | 59 ms | 6,1 s / 8,1 s | 1 |
| 20 utilisateurs | 665 | 0 | 11 ms | 50 ms | 18,2 s / 34,2 s | 12 |
| 50 utilisateurs | 1 869 | 0 | 10 ms | 355 ms | 53,8 s / 72,4 s | 39 |

Worker : 94 rêves traités, 0 échec ; **4,08 s** de traitement par rêve (p50, p95 4,10 s) ; débit mesuré **13,4 rêves/min**.

## Lecture

1. **Le web n'est pas le goulot.** Aucune erreur jusqu'à 50 utilisateurs ; p95 des pages ≤ 355 ms. Les pages lourdes (historique filtré, statistiques) montent à 0,9 s et 0,24 s au p95 à 50 utilisateurs, quand les 2 processus gunicorn sont occupés.
2. **La connexion est la page la plus lente** (p95 2,3 s à 50 utilisateurs) : le hachage PBKDF2 du mot de passe est volontairement coûteux en CPU, et 30 utilisateurs se connectent pendant ce palier sur 2 vCPU. C'est un pic d'arrivée, pas un état stable.
3. **Le goulot est le worker unique.** Il traite un rêve à la fois : sa capacité est d'environ 60 / 4,08 ≈ 14,7 rêves/min, et le débit mesuré (13,4) en est proche. Dès que les envois dépassent ce rythme, la file s'allonge (12 puis 39 tâches) et l'attente domine le temps de bout en bout (attente p95 156 s, traitement 4 s).
4. **SLO de bout en bout (ADR-006 : p95 ≤ 30 s)** : tenu à 5 utilisateurs (8,1 s), dépassé dès 20 (34,2 s).

## Capacité et conséquences

- Avec les **latences réelles** visées par ADR-006 (STT 8 s, LLM 4 s, image 15 s au p95), un rêve occupe le worker environ 20 à 27 s : **2 à 3 rêves par minute et par worker**. Ce sont des ordres de grandeur, à remplacer par les p50 mesurés dans `ApiCall` après le Jalon B.
- La file en base tient la charge (aucune tâche perdue ni en échec) : le passage à l'échelle se fait **en ajoutant des processus `db_worker`**, sans changer d'architecture. Pour la bêta (30 utilisateurs, 15 rêves/jour, ADR-007), un seul worker suffit largement ; pour tenir le SLO pendant un pic à 20 envois simultanés, il en faut plusieurs.
- Sur l'offre gratuite Render (0,1 CPU, web et worker dans le même conteneur), la capacité est très inférieure à celle de ce runner : ces chiffres sont un plafond, pas une promesse de production.

À faire : relancer le workflow avec 3 workers (`workers=3`) pour mesurer le gain, puis avec la latence réelle relevée dans `ApiCall`.
