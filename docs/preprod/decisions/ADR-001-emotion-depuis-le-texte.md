# ADR-001 — L'émotion est inférée du texte transcrit, jamais de la voix

- **Statut** : accepté · 2026-11-02
- **Compétence** : C1-3 · **Liens** : US-06, US-14, R-04, section 5 du cadrage

## Contexte
Le produit classe l'ambiance d'un rêve. Deux signaux sont disponibles : le contenu (texte transcrit) et la prosodie de la voix enregistrée. Le règlement (UE) 2024/1689 (AI Act) définit le « système de reconnaissance des émotions » comme un système destiné à identifier ou inférer des émotions **sur la base de données biométriques** (art. 3, point 39) ; ces systèmes relèvent au minimum d'obligations de transparence (art. 50) et, selon le contexte, du haut risque (annexe III). La voix analysée pour ses caractéristiques physiologiques est une donnée biométrique.

## Options
1. Classifier la prosodie (modèle audio) — plus « riche », mais fait entrer le produit dans la définition art. 3(39) et traite une donnée biométrique.
2. Classifier le texte transcrit par LLM à sortie structurée (ADR-003).
3. Classifier le texte par modèle spécialisé auto-hébergé (mDeBERTa zero-shot).

## Décision
Option 2 : l'émotion est produite par le LLM **à partir du texte uniquement**, dans le même appel que le prompt visuel. Aucune caractéristique acoustique n'est extraite ; l'audio brut est supprimé dès la transcription validée (durée de conservation : section 5). L'utilisateur peut corriger l'émotion (US-14) ; la source (`model` / `user`) est stockée.

## Conséquences
- Hors du régime « reconnaissance des émotions » de l'AI Act ; pas de traitement biométrique de la voix.
- Le classement ne capte pas un récit « neutre » dit d'une voix angoissée : limite assumée, compensée par la correction manuelle.
- L'option 3 reste un repli souverain (aucun transfert) si le LLM est indisponible, mais elle ne produit pas le prompt visuel.
