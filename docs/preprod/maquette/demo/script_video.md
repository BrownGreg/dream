# Script de la vidéo de démonstration (≤ 3 min)

Préparation : `DREAMSYNTH_MOCK_LATENCY=0.8 streamlit run app/streamlit_app.py`, navigateur en 1280 × 720, journal vide, fichier `benchmark/corpus/audio/02_cauchemar.mp3` à portée, un faux `.mp3` (texte renommé) pour l'erreur.

| Temps | À l'écran | Voix off |
|---|---|---|
| 0:00–0:12 | Accueil, titre | « Le Synthétiseur de rêves transforme un rêve raconté au réveil en image, ambiance et humeur. Voici la maquette de pré-production. » |
| 0:12–0:30 | Les 3 cases de consentement, on coche les trois, « Enregistrer mes choix » | « Le consentement est explicite et séparé : transcription, image, suivi des émotions. Chaque sous-traitant et son pays sont nommés. » |
| 0:30–0:55 | « Raconter un rêve », enregistrement micro de ~8 s, « Créer mon rêve », progression étape par étape | « J'enregistre au micro. Le traitement avance étape par étape : vérification, transcription, analyse, image, ambiance. » |
| 0:55–1:20 | Résultat : titre, transcription modifiable, émotion avec icône, image avec mention « Image générée par IA », lecture de l'ambiance | « L'émotion est déduite du texte, jamais de la voix. L'image porte toujours la mention IA. L'ambiance vient d'une bibliothèque : zéro coût, zéro transfert. » |
| 1:20–1:35 | Sélecteur « Corriger l'émotion » : passage à « serein » | « Si le classement se trompe, je le corrige : l'historique garde mon choix. » |
| 1:35–1:55 | Import de `02_cauchemar.mp3`, case « Ne pas générer d'image » cochée, résultat sans image | « Pour un cauchemar, je peux refuser l'image : aucun appel n'est fait au générateur. » |
| 1:55–2:15 | Import du faux `.mp3` → message « Format non pris en charge » ; Mode démonstration « Service de transcription indisponible » → message + bouton « Relancer » | « Les erreurs sont claires et proposent une action. En cas de panne, l'audio est conservé pour relancer. » |
| 2:15–2:40 | « Mes rêves » : frise, filtre « stressant », tendances avec mention « sans valeur médicale » | « Mes rêves se retrouvent sur une frise, filtrables par émotion, avec une tendance mensuelle sans interprétation médicale. » |
| 2:40–2:55 | Export JSON puis « Supprimer définitivement » | « J'exporte mes données dans un format ouvert, et je supprime un rêve avec tous ses fichiers. » |
| 2:55–3:00 | Retour accueil | « Code, benchmark et dossiers sont dans le dépôt. » |

Durée totale : 3:00. L'enregistrement (OBS ou capture navigateur) reste à faire par l'auteur : il nécessite un micro réel, que les tests automatisés ne peuvent pas simuler.
