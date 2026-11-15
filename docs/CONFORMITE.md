# Conformité — bloc production

Vérification du 2026-11-11. Exigences : contraintes du sujet de production, grille d'évaluation et règles du projet (le PDF du sujet de production n'est pas versionné ; la conformité du bloc 1 est dans [`docs/preprod/CONFORMITE.md`](preprod/CONFORMITE.md)).
Statuts : ✅ satisfait · ⚠️ partiel (écart expliqué) · ❌ absent (expliqué).

## Contraintes du sujet

| Exigence | Preuve | Statut |
|---|---|---|
| Python, Django | `pyproject.toml` (Python 3.12, Django 6.0) | ✅ |
| Base SQL PostgreSQL | PostgreSQL 17 en CI et Compose (`ci.yml`, `docker-compose.yml`), Neon prévu en production (ADR-008) | ✅ |
| Tailwind | `uv run python manage.py tailwind build` (`scripts/install.sh`), CSS servi vérifié par le test de fumée Docker | ✅ |
| Docker Compose local | `docker-compose.yml` (web + worker + db) ; job CI « Image Docker et test de fumée » | ✅ |
| Render public, déployé depuis `main` | `render.yaml`, job CI « Déploiement Render » (hook + `/health` en production) | ⚠️ pipeline prêt, **service non créé** : le job saute faute de `RENDER_DEPLOY_HOOK_URL` |
| Budget API ≤ 20 €, appliqué par le code | `ApiCall`, `dreams/services/budget.py`, coupe-circuit à 15 € avant chaque tentative (ADR-009) ; `test_coupe_circuit_bloque_sans_appeler_le_fournisseur` | ✅ code et tests · dépense réelle **à relever** en production |
| Couverture ≥ 70 % des fonctionnalités critiques, par module en CI | `scripts/check_coverage.py` ; 12 fonctionnalités entre 97,3 % et 100 % (run `42700247218`) | ✅ |
| PEP 8, docstrings Google, type hints | ruff (`E`, `W`, `D` convention google, `ANN`…), mypy `strict = true`, en CI | ✅ |
| Branches et PR | `feat\|fix\|test\|docs/DREAM-<n>-…` ; 25 PR fusionnées au 2026-11-14, aucune avec un contrôle en échec ; protection de `main` : 4 contrôles requis, branche à jour obligatoire | ✅ |

## Livrables

| Livrable | Preuve | Statut |
|---|---|---|
| Dépôt GitHub | <https://github.com/BrownGreg/dream>, README complet | ✅ |
| `rapport_<groupe>.pdf` | `docs/rapport/rapport_hery.pdf` (`make rapport`) | ⚠️ production non déployée ; coût réel 0 € ; latences réelles non mesurées (accès API Mistral inactif, BFL sans crédit) |
| `postmortem_<prenom>.pdf` | `docs/postmortem/postmortem_gregory.pdf` (`make postmortem`) : matière factuelle | ⚠️ parties subjectives **à rédiger par l'auteur** |
| Code review live | [`docs/code-review/`](code-review/README.md) : 2 bugs, 1 story, 10 questions | ✅ |

## Grille d'évaluation

| Critère | Preuve | Statut |
|---|---|---|
| Fonctionnalités : auth, STT, classification, image, ambiance, tableau de bord | rapport §1 ; parcours E2E `test_inscription_enregistrement_resultat_historique` | ✅ en mode `fake` · ⚠️ appels réels non exercés |
| Qualité du code | ruff, mypy strict, ports et adapters, ADR | ✅ |
| Intégration IA : délais, retries, quotas, budget, replis | `dreams/services/http.py`, rapport §3, fiche 3 | ✅ |
| Tests : couverture, charge, stratégie écrite | `docs/tests/strategie.md`, `docs/tests/charge/` | ✅ · ⚠️ cassettes VCR non enregistrées (5 tests ignorés, clés requises) |
| CI/CD, configuration par environnement, monitoring, journaux | `.github/workflows/ci.yml`, `config/settings/{base,dev,test,prod}.py`, `/health`, `/ops`, structlog, Sentry | ✅ · ⚠️ déploiement (voir plus haut) |
| Performance : temps de réponse, latence des API | `docs/tests/performance.md` | ✅ pages · ❌ latences réelles des fournisseurs **NON MESURÉES** |
| Documentation : README, rapport, schémas à jour | README, `docs/diagrams/` (ERD généré depuis le code) | ✅ |
| Post-mortem | matière prête | ⚠️ à rédiger par l'auteur |
| Code review live | dossier prêt | ✅ · répétition à faire par l'auteur |

## Règles de sécurité et de données

| Règle | Preuve | Statut |
|---|---|---|
| Aucun contenu de rêve dans les journaux, Sentry, traces | `config/observability.py` ; `test_observability.py` | ✅ |
| Audio supprimé après transcription réussie, conservé si elle échoue | `purge_audio` ; `test_pipeline.py` (l. 50-51, `test_panne_stt_conserve_l_audio_puis_reussit_au_nouvel_essai`) | ✅ |
| Images stockées chez nous | `dreams/storage.py`, ADR-010 | ✅ |
| Émotion inférée du texte, jamais de la voix | ADR-001 ; adapters d'émotion prennent du texte | ✅ |
| Mention « générée par IA » sur chaque image | `dreams/templates/dreams/detail.html` (« Image générée par IA ») | ✅ |
| Secrets uniquement par variables d'environnement | gitleaks sur tout l'historique (65 commits) : 5 faux positifs vérifiés et listés dans `.gitleaksignore`, aucune fuite | ✅ |

## Interdits

| Interdit | Preuve | Statut |
|---|---|---|
| Pipeline IA dans la requête HTTP | mise en file `on_commit`, `db_worker` ; séquence | ✅ |
| Retry sur 4xx non transitoire | `test_4xx_non_passagere_jamais_rejouee` | ✅ |
| Appels API réels en CI ou en charge | `AI_MODE=fake` ; VCR `record_mode: "none"` | ✅ |
| Merge sur `main` sans CI verte | `gh pr view … statusCheckRollup` : aucun échec sur les PR fusionnées ; fusion bloquée par la protection de `main` tant que les 4 contrôles requis ne sont pas verts | ✅ |

## Vérification finale

| Étape | Résultat | Statut |
|---|---|---|
| 1. Ce tableau | — | ✅ |
| 2. Clone propre → `scripts/install.sh` → démarrage → `pytest` | **échec trouvé** : `DATABASE_URL=` vide de `.env.example` cassait `migrate` (incident n° 12). Corrigé par la PR [#31](https://github.com/BrownGreg/dream/pull/31), fusionnée ; clone de la branche corrigée : installation OK, 289 tests verts, `/health` 200 | ✅ |
| 3. CI verte sur `main`, déploiement réussi, `/health` en production | CI verte ; déploiement non effectué | ⚠️ |
| 4. Parcours complet en production (mobile, desktop, erreurs volontaires) | pas de production | ❌ à faire après création du service Render |
| 5. `ApiCall` : coût ≤ budget, coupe-circuit testé | coupe-circuit testé ; aucun coût réel | ⚠️ |
| 6. Recherche de secrets (`gitleaks`) | aucune fuite (voir plus haut) | ✅ |
| 7. Relecture des PDF par un jury simulé | non faite | ❌ à faire une fois les valeurs de production renseignées |
