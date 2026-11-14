> **Mode d'emploi.** Ce document réunit la **matière factuelle** du post-mortem : chronologie, écarts entre le prévu et le réalisé, incidents, métriques, statistiques Git et Jira. Chaque chiffre vient d'un fichier du dépôt ou de GitHub, cité. Les parties **subjectives** (auto-évaluation, recul critique, leçons) sont à rédiger par l'auteur dans les encadrés « À rédiger », guidés par des questions. Rien n'y est pré-écrit.

# 1. Chronologie

| Date | Événement | Source |
|---|---|---|
| bloc 1 | Dossier de cadrage, spécifications et architecture, maquette Streamlit, benchmark | `docs/preprod/` |
| 2026-11-09, 15 h 54 | Import des livrables du bloc 1 sur un `main` réécrit (l'ancien projet est retiré) | premier commit de `main` |
| 2026-11-09, 16 h 01 | DREAM-1 : socle Django 6 et authentification (PR #1) | `git log` |
| 2026-11-09, 18 h 34 – 18 h 37 | DREAM-2 : CI/CD, Docker Compose, Blueprint Render · DREAM-3 : ADR-008 et ADR-009 | PR #2, #3 |
| 2026-11-09, 18 h 54 – 20 h 22 | Cœur du produit : modèles (DREAM-4), client résilient et coupe-circuit (DREAM-5), transcription (DREAM-7), émotion (DREAM-8), prompt et image (DREAM-9), tâche de fond (DREAM-10), enregistrement audio (DREAM-6) | PR #9 à #14, #16 |
| 2026-11-09, 20 h 46 – 21 h 16 | Tableau de bord, détail, compte RGPD, ambiance sonore, accessibilité (DREAM-11 à 16) | PR #17 à #22 |
| 2026-11-09, 21 h 39 – 22 h 03 | Observabilité (DREAM-17), stratégie de tests (DREAM-18), E2E et **correctif critique MediaRecorder** (DREAM-19), correctif de mesure (DREAM-17), charge Locust (DREAM-20) | PR #23 à #26, #28 |
| 2026-11-09, 22 h 07 – 22 h 12 | README et schémas (DREAM-22) ; performance face aux SLO (DREAM-21, PR #29 ouverte) | PR #27, #29 |
| 2026-11-11 | Rapport de production (DREAM-23), post-mortem (matière), dossier de code review (DREAM-24) ; la vérification en clone propre révèle l'incident n° 12 | PR #30, #31, #32 |
| **À COMPLÉTER** | Création du service Render, premiers appels réels, mesure du coût et des latences | — |

Les horodatages Git sont ceux des **fusions** (*squash*, un commit par PR), pas du début du travail : ils ne mesurent pas le temps passé.

# 2. Prévu et réalisé

## 2.1 Périmètre fonctionnel (user stories du bloc 1)

Source : `docs/preprod/backlog/stories.toml` (MoSCoW, release) et labels du backlog `docs/backlog/jira_production.csv`.

| Release prévue | Stories | Réalisé en production |
|---|---|---|
| MVP (S1–S4, 44 pts) | US-01 à US-13 | toutes livrées ; US-10 : filtre par émotion livré, **pas de frise** dédiée (statistiques à la place) |
| R2 (S5–S6, 18 pts) | US-14, 15, 16, 17, 23 | US-14 à 17 livrées ; **US-23 (lecture vocale, Could) non livrée** |
| R3 (S7–S8, 13 pts) | US-18, 19, 20 | **non livrées** (rappel matinal, style visuel, micro-vidéo — toutes Could) |
| Won't | US-21, US-22 | non livrées, comme prévu |

Toutes les stories **Must** sont livrées, y compris US-15 et US-17 (export, suppression du compte) que le bloc 1 plaçait en R2.

## 2.2 Planning

| | Prévu | Réalisé |
|---|---|---|
| Durée du bloc production | 6 jours (labels `jour-1` à `jour-6`, 77 story points) | code fusionné le 9 novembre ; documentation le 11 novembre |
| Vélocité de référence | 11 points par sprint d'une semaine (hypothèse du bloc 1) | 77 points en 24 tickets ; **temps réel : À COMPLÉTER** |
| Mise en production | automatique depuis `main` (DREAM-2) | pipeline prêt ; service Render **non créé** au 2026-11-11 |

## 2.3 Architecture

Le bloc 1 visait FastAPI, Streamlit puis Next.js, Arq sur Redis et un stockage S3. La production utilise Django 6, HTMX, `django.tasks` avec une file en base, et stocke les fichiers dans PostgreSQL (ADR-008, ADR-010). Le budget passe de 25 $/mois à 20 € au total (ADR-009). Raisons consignées dans les ADR : contraintes du sujet de production et durée de 6 jours.

## 2.4 Registre des risques du bloc 1 : ce qui s'est produit

Source : `docs/preprod/backlog/risks.toml`.

| Risque | P × I prévu | Constat factuel |
|---|---|---|
| R-01 Latence fournisseurs au-delà des SLO | 3 × 3 | **non mesurée** (aucun appel réel) |
| R-02 Transcription médiocre | 3 × 3 | **non mesurée** |
| R-03 DPA / opt-out BFL non obtenus | 3 × 4 | **À COMPLÉTER** par l'auteur |
| R-04 Requalification AI Act | 1 × 4 | émotion inférée du texte uniquement (ADR-001), testé |
| R-05 Image choquante | 3 × 3 | refus de sécurité géré : une reformulation adoucie, sinon pas d'image |
| R-06 Dépendance à Mistral | 2 × 4 | repli à 3 niveaux pour l'émotion seulement ; transcription et prompt restent sans fournisseur de secours |
| R-07 Dépassement du budget | 2 × 3 | coupe-circuit à 15 € appliqué par le code et testé ; aucun appel réel effectué à ce jour ; **dépense en production À COMPLÉTER** |
| R-08 Modèle déprécié | 3 × 2 | identifiants de modèles en variables d'environnement |
| R-09 Retard du travail individuel | 3 × 3 | **À COMPLÉTER** par l'auteur |
| R-10 Fuite du contenu des rêves | 2 × 4 | chiffrement applicatif, journaux et Sentry nettoyés, testé (`test_observability.py`) |
| R-11 Lecture médicale de l'humeur | 2 × 4 | pas d'interprétation (US-22 en Won't) |

# 3. Incidents

12 incidents journalisés dans `docs/incidents.md`, détaillés dans le rapport (§7).

| Catégorie | Incidents | Révélé par |
|---|---|---|
| Comportement implicite d'une bibliothèque | 1 (`normalize_email`), 2 (Axes), 7 (ordre des gabarits), 10 (`run_after`) | relecture des journaux, audit d'accessibilité, test de charge |
| Format de fichier réel ≠ fichier de test | 4 (WAV sur flux), 9 (webm MediaRecorder sans durée) | essai manuel, parcours E2E navigateur |
| Environnement de CI / build / installation neuve ≠ poste local | 5 (ffmpeg absent), 8 (`collectstatic` de production), 12 (`DATABASE_URL` vide) | CI, clone propre |
| Logique métier | 3 (égalité au plafond), 11 (mesure bout en bout) | tests, capture de `/ops` |
| Outillage de test | 6 (simulation trop large, boucle infinie) | isolement test par test |

Un incident est classé **critique** : le n° 9. Sans lui, tout enregistrement au micro sous Chrome et Firefox aurait été refusé. Il a été découvert par le premier test E2E au micro simulé, après la fusion de la fonctionnalité (DREAM-6), et corrigé dans DREAM-19.

# 4. Métriques

| Métrique | Valeur | Source |
|---|---|---|
| Lignes Python applicatives (hors migrations) | 5 034 | `git ls-files` + `wc -l` |
| Lignes de tests | 3 365 | idem |
| Gabarits HTML | 647 lignes | idem |
| Tests | 286 réussis, 5 ignorés + 3 E2E | CI run `42700247218` |
| Couverture globale | 99 % (lignes et branches) | artefact `couverture` |
| Couverture minimale par fonctionnalité critique | 97,3 % (pipeline et reprise) | `scripts/check_coverage.py` |
| Exécutions de la CI | 111, dont 7 en échec | `gh run list` (workflow `ci`) |
| Charge | 0 erreur sur 5 012 requêtes ; bout en bout p95 72,4 s à 50 utilisateurs avec 1 worker, 24,2 s avec 3 | `docs/tests/charge/` |
| ADR | 10 (dont 3 d'évolution en production) | `docs/decisions/` |
| Coût API réel | **À COMPLÉTER** | `/ops` en production |

# 5. Statistiques Git et Jira

| Indicateur | Valeur |
|---|---|
| Commits sur `main` | 25 au 2026-11-14 (*squash*, un par PR) |
| PR fusionnées | 24 ; en revue : #30, #32 |
| PR Dependabot | 5 (#4 à #8), aucune fusionnée, 2 fermées |
| Tickets Jira de production | 24 (12 stories, 12 tâches), 77 story points |
| Tickets de correctif dédiés | 2 PR `fix` (#26, #31) ; les autres correctifs sont dans la PR de la fonctionnalité concernée |
| Plus grosse PR (hors données) | #1, socle Django : 2 106 lignes ajoutées |

# 6. À rédiger par l'auteur

Les questions ci-dessous sont des pistes. Aucune réponse n'est proposée.

## 6.1 Auto-évaluation

- Quelle part du périmètre prévu considères-tu réellement terminée, et selon quel critère ?
- Où le résultat est-il au-dessus de ce que tu attendais ? En dessous ?
- Comment répartirais-tu ton temps réel entre les lots du §2.2 ?

**À rédiger.**

## 6.2 Ce qui a fonctionné

- Quelles décisions du bloc 1 (ports et adapters, idempotence, budget dans le code, ADR) ont tenu en production ? Lesquelles t'ont fait gagner du temps ?
- Quel outil ou quelle pratique referais-tu à l'identique ?

**À rédiger.**

## 6.3 Ce qui n'a pas fonctionné

- Pourquoi la mise en production et les mesures réelles (coût, latences) arrivent-elles en dernier ? Était-ce un choix ou une contrainte ?
- L'incident critique n° 9 est passé à travers les tests unitaires : qu'est-ce que cela dit de la stratégie de tests de départ ?
- Le planning en 6 jours et le rythme réel diffèrent : qu'en retiens-tu pour l'estimation ?

**À rédiger.**

## 6.4 Usage des outils d'IA dans le développement

- Comment as-tu utilisé un assistant de code, et comment as-tu vérifié ce qu'il produisait ?
- Sur quelles parties maîtrises-tu le code au point de l'expliquer en code review ? Sur lesquelles moins ?

**À rédiger.**

## 6.5 Leçons et améliorations

- Trois choses que tu ferais autrement sur un prochain projet, et pourquoi.
- Quelles améliorations du produit prioriserais-tu avec une semaine de plus ?

**À rédiger.**
