# ADR-003 — Un appel LLM à sortie structurée : prompt visuel + émotion

- **Statut** : accepté · 2026-11-02
- **Compétence** : C1-2, C1-3 · **Liens** : US-06, US-07, ADR-001, KPI K7, `src/dreamsynth/services/dream_analysis.py`

## Contexte
Le récit brut n'est pas un bon prompt d'image (oralité, hésitations, français) et contient parfois des noms ou détails identifiants. Il faut aussi une émotion (ADR-001).

## Options
| Option | Prompt visuel | Émotion | $/rêve (H2 = 700, H3 = 250 tokens) | Données |
|---|---|---|---|---|
| **Mistral Small 4, sortie JSON validée par schéma** | oui | oui | 0,00026 | UE, DPA |
| OpenAI gpt-4o-mini (page modèle marquée Deprecated) | oui | oui | 0,00026 | US |
| mDeBERTa zero-shot (auto-hébergé) | **non** | oui | coût CPU | aucun transfert |
| Envoyer le texte brut au générateur d'image | — | — | 0 | expose le récit complet au fournisseur d'image |

## Décision
Un seul appel Mistral Small 4 (`mistral-small-2603`, identifiant à confirmer par `--list-models`) avec `response_format` JSON Schema généré depuis le modèle Pydantic `DreamAnalysis` (titre, prompt visuel anglais 60–120 mots, émotion parmi 6, confiance). La consigne interdit noms propres, données identifiantes, contenu graphique et toute interprétation psychologique.

## Conséquences
- **Minimisation** : le fournisseur d'image ne reçoit qu'un prompt anglais reformulé, jamais la transcription.
- Le coût LLM est négligeable (≈ 1,4 % du coût d'un rêve du scénario S1, onglet `Coût 10 rêves-jour`).
- Toute réponse non conforme au schéma est rejetée et rejouée une fois (K7 ≥ 99 %).
- Les jetons réellement consommés (mode `--live`) remplacent H2/H3 dans le modèle de coût.
- Le port `EmotionClassifier` prévu dans `CLAUDE.md` devient `DreamAnalyzer` (prompt visuel + émotion en un appel). Un adapter mDeBERTa peut l'implémenter partiellement (émotion seule, prompt dérivé du texte) en mode dégradé.
