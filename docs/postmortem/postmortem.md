> **Mode d'emploi.** Les §1 à 5 réunissent la **matière factuelle** du post-mortem : chronologie, écarts entre le prévu et le réalisé, incidents, métriques, statistiques Git et Jira. Chaque chiffre vient d'un fichier du dépôt ou de GitHub, cité. Le §6 est mon retour d'expérience : il s'appuie uniquement sur ces faits.

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
| 2026-11-14 | Premier essai en mode réel : clés Mistral, Hugging Face et BFL valides, mais Mistral refuse les appels (HTTP 429, quota de 0 requête/min) et BFL est à 0 crédit ; le rêve de test échoue proprement, 0 $ facturé. Service Render toujours non créé | `ApiCall` local |
| 2026-11-15, matin | Base Neon (UE) créée ; premier déploiement Render en échec (`DATABASE_URL` collée avec ses guillemets, incident n° 13), puis en ligne ; CI branchée sur le deploy hook. Le test de fumée valide l'ancienne instance (incident n° 14, PR #36) | Render, GitHub Actions |
| 2026-11-15, 10 h 42 – 11 h 08 | Premiers rêves réels : 9 refus 429 de Mistral, organisation repassée sur le plan Free (incident n° 15) ; plan API activé, transcription réussie ; le quota bloque l'utilisateur à cause des échecs (incident n° 16, PR #34) | `docs/tests/production/apicall_2026-11-15.json` |
| 2026-11-15, 11 h 42 – 11 h 48 | Image refusée (BFL 402, compte non crédité), puis générée après achat de crédits : premier rêve complet en production, 14,6 s, 0,0158 $ | même fichier |
| 2026-11-15 | Backlog de production créé dans Jira (clés DREAM-42 à 65, epic DREAM-41, bugs DREAM-40, 66, 67 ; PR #35) | `docs/backlog/README.md` |

Les horodatages Git sont ceux des **fusions** (*squash*, un commit par PR), pas du début du travail. Le rythme du 9 novembre (22 PR fusionnées en un peu plus de 6 heures) n'est pas celui d'un développement à la main : le code a été écrit en grande partie par un assistant de code (§6.4).

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
| Vélocité de référence | 11 points par sprint d'une semaine (hypothèse du bloc 1) | 77 points en 24 tickets ; environ **6 h** de travail de ma part (estimation, non chronométré), avec un assistant de code (§6.4) |
| Mise en production | automatique depuis `main` (DREAM-2), jour 1 | en ligne le **15/11/2026**, dernier jour ; déploiement automatique depuis `main` vérifié |

## 2.3 Architecture

Le bloc 1 visait FastAPI, Streamlit puis Next.js, Arq sur Redis et un stockage S3. La production utilise Django 6, HTMX, `django.tasks` avec une file en base, et stocke les fichiers dans PostgreSQL (ADR-008, ADR-010). Le budget passe de 25 $/mois à 20 € au total (ADR-009). Raisons consignées dans les ADR : contraintes du sujet de production et durée de 6 jours.

## 2.4 Registre des risques du bloc 1 : ce qui s'est produit

Source : `docs/preprod/backlog/risks.toml`.

| Risque | P × I prévu | Constat factuel |
|---|---|---|
| R-01 Latence fournisseurs au-delà des SLO | 3 × 3 | **ne s'est pas produit** sur le petit échantillon de production : transcription ≤ 0,91 s, LLM ≤ 1,96 s, image 8,7 s, rêve complet 14,6 s (`docs/tests/production/apicall_2026-11-15.json`) |
| R-02 Transcription médiocre | 3 × 3 | taux d'erreur (WER) **non mesuré** ; 3 transcriptions réelles réussies, une transcription vide sur un enregistrement quasi muet |
| R-03 DPA / opt-out BFL non obtenus | 3 × 4 | statut du DPA non documenté dans le dépôt ; depuis le 15/11/2026, BFL reçoit le prompt reformulé (sans nom), une image générée à ce jour |
| R-04 Requalification AI Act | 1 × 4 | émotion inférée du texte uniquement (ADR-001), testé |
| R-05 Image choquante | 3 × 3 | refus de sécurité géré : une reformulation adoucie, sinon pas d'image |
| R-06 Dépendance à Mistral | 2 × 4 | **s'est produit** (incident n° 15) : sans accès Mistral, aucun rêve n'aboutit, faute de secours pour la transcription. Inversement, Hugging Face étant sans crédit (402), l'émotion passe toujours par Mistral |
| R-07 Dépassement du budget | 2 × 3 | coupe-circuit à 15 € appliqué par le code et testé ; dépense réelle au 15/11/2026 : **0,019 $** (`docs/tests/production/apicall_2026-11-15.json`) |
| R-08 Modèle déprécié | 3 × 2 | identifiants de modèles en variables d'environnement |
| R-09 Retard du travail individuel | 3 × 3 | survenu en partie : le déploiement (prévu jour 1) et les mesures réelles (prévues jour 5) ne sont faits que le 15/11/2026, jour du rendu, sur un petit échantillon |
| R-10 Fuite du contenu des rêves | 2 × 4 | chiffrement applicatif, journaux et Sentry nettoyés, testé (`test_observability.py`) |
| R-11 Lecture médicale de l'humeur | 2 × 4 | pas d'interprétation (US-22 en Won't) |

# 3. Incidents

16 incidents journalisés dans `docs/incidents.md`, détaillés dans le rapport (§7).

| Catégorie | Incidents | Révélé par |
|---|---|---|
| Comportement implicite d'une bibliothèque | 1 (`normalize_email`), 2 (Axes), 7 (ordre des gabarits), 10 (`run_after`) | relecture des journaux, audit d'accessibilité, test de charge |
| Format de fichier réel ≠ fichier de test | 4 (WAV sur flux), 9 (webm MediaRecorder sans durée) | essai manuel, parcours E2E navigateur |
| Environnement de CI / build / installation neuve ≠ poste local | 5 (ffmpeg absent), 8 (`collectstatic` de production), 12 (`DATABASE_URL` vide) | CI, clone propre |
| Logique métier | 3 (égalité au plafond), 11 (mesure bout en bout), 16 (quota consommé par les échecs du service) | tests, capture de `/ops`, production |
| Configuration de plateforme ou de compte fournisseur | 13 (`DATABASE_URL` avec guillemets sur Render), 15 (plan Free Mistral : 0 requête/min) | premier déploiement, premiers rêves réels |
| Test de déploiement trompeur | 14 (le test de fumée interrogeait l'ancienne instance) | relecture du temps de réponse du job |
| Outillage de test | 6 (simulation trop large, boucle infinie) | isolement test par test |

Un incident est classé **critique** : le n° 9. Sans lui, tout enregistrement au micro sous Chrome et Firefox aurait été refusé. Il a été découvert par le premier test E2E au micro simulé, après la fusion de la fonctionnalité (DREAM-6), et corrigé dans DREAM-19.

# 4. Métriques

| Métrique | Valeur | Source |
|---|---|---|
| Lignes Python applicatives (hors migrations) | 5 034 | `git ls-files` + `wc -l` |
| Lignes de tests | 3 365 | idem |
| Gabarits HTML | 647 lignes | idem |
| Tests | 297 réussis, 5 ignorés + 3 E2E | CI run `43707491282` (`main`, 15/11/2026) |
| Couverture globale | 99 % (lignes et branches) | artefact `couverture` |
| Couverture minimale par fonctionnalité critique | 97,3 % (pipeline et reprise) | `scripts/check_coverage.py` |
| Exécutions de la CI | 157 au 15/11/2026 : 126 réussies, 8 en échec, 23 annulées | `gh run list` (workflow `ci`) |
| Charge | 0 erreur sur 5 012 requêtes ; bout en bout p95 72,4 s à 50 utilisateurs avec 1 worker, 24,2 s avec 3 | `docs/tests/charge/` |
| ADR | 10 (dont 3 d'évolution en production) | `docs/decisions/` |
| Coût API réel | **0,019 $** au 15/11/2026 (25 appels) ; rêve complet : 0,0158 $ | `docs/tests/production/apicall_2026-11-15.json` |
| Latences réelles | transcription 0,86–0,91 s ; émotion 0,44–0,48 s ; prompt 1,28–1,96 s ; image 8,7 s ; bout en bout 4,1 s sans image, 14,6 s avec | même fichier |

# 5. Statistiques Git et Jira

| Indicateur | Valeur |
|---|---|
| Commits sur `main` | 34 au 2026-11-15 (*squash*, un par PR) |
| PR fusionnées | 33 au 2026-11-15, avant la PR de mise à jour du post-mortem |
| PR Dependabot | 5 (#4 à #8), toutes fermées : 2 écartées (Django 6.1, Python 3.15 ; règle de la PR #15), 3 appliquées ensemble par la PR #38 |
| Tickets Jira de production | 24 (12 stories, 12 tâches), 77 story points, + 6 bugs (DREAM-40, 66 à 70) ; sprint « Production » de 31 tickets, tous terminés au 15/11/2026 ; clés DREAM-42 à 65 (référence dépôt DREAM-1 à 24, voir `docs/backlog/README.md`) |
| Tickets de correctif dédiés | 4 PR `fix` (#26, #31, et en production #34, #36) ; les autres correctifs sont dans la PR de la fonctionnalité concernée |
| Plus grosse PR (hors données) | #1, socle Django : 2 106 lignes ajoutées |

# 6. Retour d'expérience

## 6.1 Auto-évaluation

Je considère le périmètre **Must** comme terminé, selon un critère simple : la fonctionnalité est testée en CI **et** elle a tourné en production avec les vrais fournisseurs. Toutes les stories Must du bloc 1 passent ce critère depuis le 15 novembre, y compris l'export et la suppression du compte, que le bloc 1 avait placés en R2. En revanche, je n'ai livré ni la lecture vocale (US-23), ni le rappel matinal, le style visuel ou la micro-vidéo (R3), ni la frise de l'historique prévue dans US-10 : je les ai sacrifiés pour tenir le socle.

Le résultat est **au-dessus** de ce que j'attendais sur la qualité vérifiable : 297 tests, 99 % de couverture globale, entre 97,3 % et 100 % sur chacune des 12 fonctionnalités critiques, une CI qui bloque toute fusion, un test de charge jusqu'à 50 utilisateurs. Il est **en dessous** sur la confrontation au réel : la production n'est en ligne que depuis le dernier jour, et mes mesures réelles reposent sur 25 appels et 2 rêves. Je peux dire que les SLO sont tenus sur cet échantillon, pas qu'ils le sont en général.

J'estime mon temps de travail à environ 6 heures sur le bloc production, sans l'avoir chronométré. C'est très loin de la capacité de 25 h prévue au bloc 1, et ce n'est pas comparable : je n'ai pas écrit le code à la main, j'ai piloté un assistant de code (§6.4). Ce temps a surtout servi à cadrer, décider, relire et vérifier. La mise en production, avec les comptes fournisseurs et les correctifs du dernier jour, en a pris une part bien plus grande que ce que le plan lui accordait : le déploiement n'était qu'une partie du ticket DREAM-2, estimé à 3 story points pour toute la CI/CD.

## 6.2 Ce qui a fonctionné

La décision du bloc 1 qui m'a le plus servi, ce sont les **ports et adapters avec un mode `fake`**. Comme les adapters simulés passent par le même client résilient que les vrais, j'ai pu tester les retries, le journal des coûts, le coupe-circuit et tout le pipeline sans dépenser un centime. Le test de charge Locust a tourné sur le même principe. Sans ce choix, je n'aurais pas pu avancer tant que les comptes Mistral et BFL n'étaient pas actifs.

Le **client résilient et le budget appliqué par le code** ont tenu face au réel. Le premier jour en production, Mistral a renvoyé neuf 429 et Hugging Face et BFL des 402. Chaque fois, l'application a fait ce qui était prévu : trois tentatives au plus, aucun coût journalisé à tort, un repli Mistral pour l'émotion et un message clair pour l'utilisateur. La dépense réelle est restée à 0,019 $.

L'**idempotence avec reprise par étape** et la règle « jamais d'IA dans la requête HTTP » ont rendu l'application prévisible : la page répond tout de suite et le worker reprend là où il s'est arrêté. Le test de charge a d'ailleurs montré que le goulot était la file d'attente, pas le serveur web.

Les **ADR** m'ont permis de changer d'architecture sans perdre le fil. Le bloc 1 visait FastAPI, Redis et S3 ; l'ADR-008 explique pourquoi la production est en Django avec une file en base, et l'ADR-009 pourquoi le budget passe à 20 € avec un coupe-circuit à 15 €. Quand je devrai justifier ces choix devant le jury, ils sont écrits et datés.

Je referais à l'identique la **CI bloquante** avec un seuil de couverture par fonctionnalité critique, et le **journal des incidents tenu au fil de l'eau**. Ce journal, écrit au moment où les bugs arrivaient, est devenu tel quel la section « difficultés » du rapport et la matière du dossier de code review.

## 6.3 Ce qui n'a pas fonctionné

La mise en production et les mesures réelles arrivent en dernier, et c'est **surtout un choix de ma part**, même s'il s'est appuyé sur une contrainte. Le mode `fake` me permettait d'avancer sans clés ; j'ai donc priorisé les fonctionnalités et les tests, et repoussé tout ce qui touchait aux comptes et à la plateforme. Le déploiement était pourtant prévu dès le jour 1. Le premier essai réel, le 14 novembre, a montré que le compte Mistral n'avait pas d'accès API et que BFL n'avait aucun crédit. Le 15, le premier jour en ligne, a révélé quatre incidents (n° 13 à 16) qu'aucun test ne pouvait voir : des guillemets dans `DATABASE_URL` sur Render, un test de fumée qui validait l'ancienne instance, l'organisation Mistral repassée sur le plan Free, et un quota qui comptait les échecs du fournisseur. J'ai sous-estimé tout ce qui n'est pas du code.

L'incident critique n° 9 m'a appris que mes premiers tests vérifiaient **mes hypothèses** plutôt que le monde réel. Mes fichiers de test étaient des webm complets produits par ffmpeg, avec une durée dans les métadonnées. Un vrai MediaRecorder écrit en flux, sans durée. Tous les tests unitaires passaient, alors qu'aucun enregistrement micro sous Chrome ou Firefox n'aurait été accepté. Seul le parcours E2E avec un vrai navigateur l'a révélé. L'incident n° 10 relève de la même erreur : la fixture reproduisait la supposition fausse sur `run_after`.

Sur l'estimation, le plan du bloc 1 ne m'a pas servi. Il prévoyait une vélocité hypothétique de 11 points par sprint et une capacité de 25 h pour un développement à la main ; avec un assistant de code, 77 points ont été fusionnés le 9 novembre en un peu plus de 6 heures. Les story points mesuraient l'effort d'écriture, alors que mon effort réel portait sur la relecture, les décisions et le déploiement, que le plan ne chiffrait presque pas. Comme je n'ai suivi ni mon temps ni le backlog dans Jira au fil de l'eau, je ne peux pas le démontrer ticket par ticket. Le backlog de production n'a d'ailleurs été créé dans Jira que le 15 novembre, ce qui a produit un décalage entre les clés citées dans Git (DREAM-1 à 24) et les clés Jira (DREAM-42 à 65).

## 6.4 Usage des outils d'IA dans le développement

J'ai développé ce projet avec un **assistant de code** (Claude Code), piloté par un prompt de départ et par un fichier de règles du projet (`CLAUDE.md`). Ce fichier fixait l'architecture, les conventions et des interdits explicites : pas d'IA dans la requête HTTP, pas de retry sur une erreur 4xx, pas d'appel réel en CI, pas de fusion sans CI verte. L'assistant écrivait le code, les tests et une grande partie de la documentation ; je fixais les objectifs, je relisais les diffs dans les PR et je prenais les décisions d'architecture et de fournisseurs. C'est ce qui explique le rythme visible dans l'historique Git : 22 PR fusionnées le 9 novembre en un peu plus de 6 heures, pour environ 6 heures de travail de ma part sur tout le bloc.

Pour vérifier, je me suis appuyé sur des contrôles qui ne dépendent pas de l'assistant : la CI bloquante (ruff, mypy strict, tests sur PostgreSQL, couverture par fonctionnalité, E2E navigateur, image Docker), puis le passage en production avec les vrais fournisseurs. Le projet montre aussi les limites de cette vérification : quand le même outil écrit le code et ses tests, ils peuvent partager la même hypothèse fausse. C'est ce qui s'est passé pour les incidents n° 9 et 10, et pour le script de benchmark du bloc 1, qui n'avait jamais tourné en réel et lisait mal les réponses compressées de Mistral. Les tests ne remplacent pas un essai dans les vraies conditions.

Je maîtrise assez pour l'expliquer en code review ce qui porte les décisions du projet : l'architecture et ses ADR, le client résilient et le coupe-circuit, le pipeline idempotent, et les correctifs trouvés en production (quota, test de fumée). Je suis moins à l'aise sur ce qui relève de l'outillage : la chaîne de génération des documents (pandoc, Eisvogel, Typst), la configuration fine de Tailwind et de HTMX dans les gabarits, et le fonctionnement interne de `django-tasks-db`. Avant la soutenance, je dois relire ces parties pour ne pas présenter du code que je ne saurais pas défendre.

## 6.5 Leçons et améliorations

Trois choses que je ferais autrement :

1. **Mettre en production dès le premier jour**, même une page vide, avec les vraies clés et la vraie base. Quatre des seize incidents ne pouvaient apparaître qu'en production ; découverts le jour 1, ils auraient coûté une heure au lieu de remplir la dernière journée.
2. **Tester les comptes fournisseurs avant d'écrire le code qui les appelle** : un appel d'un jeton suffit à voir un plan désactivé ou un compte sans crédit. J'aurais su dès le départ que Mistral était sur le plan Free et que Hugging Face et BFL n'avaient pas de crédit.
3. **Tenir le suivi en même temps que le travail** : importer le backlog dans Jira avant de créer la première branche, et noter mon temps par ticket. J'aurais évité le décalage des clés et je pourrais aujourd'hui comparer le prévu et le réel au lieu d'estimer.

Avec une semaine de plus, je prioriserais :

- **un fournisseur de secours pour la transcription** : sans Mistral, aucun rêve n'aboutit (risque R-06, survenu le 15 novembre) ;
- **assez de rêves réels pour un vrai p95**, et la décision de créditer Hugging Face ou de faire de Mistral le premier choix pour l'émotion, par un ADR ;
- **plusieurs workers** si l'usage le demande : le test de charge montre qu'un seul worker ne tient pas 30 s au-delà de 5 utilisateurs simultanés ;
- côté produit, **la frise de l'historique** prévue dans US-10, puis **la lecture vocale** (US-23), dont la latence Voxtral TTS est déjà mesurée (p95 de 3,99 s).
