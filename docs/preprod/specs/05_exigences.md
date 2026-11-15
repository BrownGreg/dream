# 5. Exigences : fonctionnelles, performance, SLO, budget API

Source unique : `docs/backlog/requirements.toml`. Le tableau ci-dessous et la matrice `tracabilite.csv` (exigence → story → test → composant C4) en sont générés ; la génération échoue si une story cite une exigence inexistante ou si une exigence fonctionnelle n'est portée par aucune story.

{{include _gen/requirements.md}}

Composants C4 de chaque exigence et tests qui la couvrent : annexe `tracabilite.csv`.

## SLO (ADR-006)
| SLI | Cible p95 / taux | Fenêtre |
|---|---|---|
| Accusé de réception `POST /dreams` | ≤ 1 s | 7 j |
| Transcription · Analyse · Image | ≤ 8 s · ≤ 4 s · ≤ 15 s | 7 j |
| **Première image affichée** (fin d'envoi → image visible) | **≤ 30 s** | 7 j |
| Rêves en échec | ≤ 2 % | 30 j |
| Disponibilité API | ≥ 99,5 % (budget d'erreur : 3 h 36 min/mois) | 30 j |

Ces cibles sont des objectifs de conception. La campagne `run_latency.py --live` du 15/11/2026 (10 appels par modèle Mistral) les confirme : transcription p95 1,44 s (Voxtral Mini), analyse LLM p95 1,56 s (Mistral Small 4) ; la latence de l'image n'est pas mesurée par ce benchmark (pas de clé T2I à l'époque).

## Budget API (ADR-007)
Coût du scénario MVP : 0,0185 $ par rêve, 5,54 $ par mois à 10 rêves/jour, 8,30 $ à l'usage estimé de la bêta (15 rêves/jour ; contient un prix ESTIMÉ). Budget bêta **25 $/mois**, alerte à 20 $, coupe-circuit de la génération d'image à 25 $ (le reste du service continue), quota de 5 rêves/jour par utilisateur, 2 générations d'image maximum par rêve.
