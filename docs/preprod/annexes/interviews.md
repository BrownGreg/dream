# Annexe — Interviews éclair (SIMULÉES)

> **Avertissement** : ces deux entretiens sont **fictifs**, rédigés pour illustrer la démarche de découverte en pré-production. Ils ne constituent pas une preuve empirique. Le plan de validation réel est prévu au Sprint 3 (5 entretiens de 20 min avec la maquette, cf. section 6).

Format : 20 minutes, questions ouvertes, pas de démonstration du produit avant la question 8.

## Entretien 1 — Léa, 27 ans, designer UX (Lyon)

| # | Question | Réponse (verbatim court) |
|---|---|---|
| 1 | Racontez-moi la dernière fois que vous vous êtes souvenue d'un rêve. | « Ce matin. Un train qui roulait dans l'eau. À 9 h je ne savais plus où il allait. » |
| 2 | Qu'avez-vous fait de ce souvenir ? | « Rien. J'ai pensé “faut que je le note”, puis le café, puis Slack. » |
| 3 | Avez-vous déjà tenu un journal de rêves ? | « Deux semaines, sur Notes. J'ai arrêté : écrire au réveil, les yeux collés, c'est pénible. » |
| 4 | Qu'est-ce qui vous plaisait dans ce journal ? | « Relire après coup. Il y a des motifs qui reviennent, c'est fascinant. » |
| 5 | Dans quel état êtes-vous quand vous voulez raconter un rêve ? | « Au lit, téléphone à la main, la voix pâteuse, mon copain dort à côté. » |
| 6 | Qu'est-ce qui vous ferait abandonner un tel outil ? | « Si ça met une minute à charger. Ou s'il faut créer un compte avec 12 champs. » |
| 7 | Que penseriez-vous d'une image de votre rêve ? | « Si elle ressemble au rêve, j'adore. Si c'est du générique “fantasy violet”, ça m'agace. » |
| 8 | Qui peut voir vos rêves, selon vous ? | « Personne. C'est plus intime que mes photos. » |
| 9 | Si l'application vous disait ce que votre rêve signifie ? | « Je n'y croirais pas. Ça ferait horoscope. » |

**Insights → conséquences produit**

| Insight | Conséquence |
|---|---|
| La fenêtre de mémoire est de quelques minutes après le réveil | Enregistrement en **un geste**, consentement donné une seule fois (US-01, US-03) |
| Voix basse et pâteuse, environnement silencieux à préserver | Le STT doit tenir sur voix chuchotée : critère « qualité FR » du benchmark, corpus avec 1 récit chuchoté ; transcription **corrigeable** (US-05) |
| La valeur est dans la relecture, pas dans la capture | Historique et frise dès le MVP (US-09, US-10) |
| Une image générique déçoit plus qu'aucune image | Réécriture du récit en prompt visuel par LLM avant génération (ADR-003) ; style choisi en R3 (US-19) |
| L'interprétation est perçue comme non crédible | US-22 en *Won't* ; aucune promesse de sens |

## Entretien 2 — Karim, 41 ans, infirmier en horaires décalés (Lille)

| # | Question | Réponse (verbatim court) |
|---|---|---|
| 1 | Racontez-moi la dernière fois que vous vous êtes souvenu d'un rêve. | « Après une garde de nuit. Je cherchais un patient dans un couloir sans fin. » |
| 2 | Ces rêves de travail, ils reviennent ? | « Les semaines chargées, oui. C'est un peu mon thermomètre. » |
| 3 | Comment suivez-vous aujourd'hui votre fatigue ou votre humeur ? | « Je ne suis rien. Ma montre compte mes pas, c'est tout. » |
| 4 | À quel moment de la journée auriez-vous le temps de raconter un rêve ? | « En rentrant, à 8 h, avant de dormir. Ou dans le bus. » |
| 5 | Comment préférez-vous enregistrer ? | « J'ai déjà le dictaphone du téléphone. Si je peux envoyer le fichier, c'est bien. » |
| 6 | Qu'attendez-vous de voir après coup ? | « Savoir si j'ai fait plus de rêves stressants ce mois-ci que le mois dernier. » |
| 7 | Si l'appli se trompe sur l'émotion ? | « Je veux pouvoir dire “non, c'était plutôt neutre”. » |
| 8 | À qui confieriez-vous ces enregistrements ? | « Pas à un Américain qui revend mes données. Si c'est hébergé en France, ça me rassure. » |
| 9 | Qu'est-ce qui vous ferait payer ? | « Rien pour l'instant. Peut-être un bilan mensuel propre. » |

**Insights → conséquences produit**

| Insight | Conséquence |
|---|---|
| Usage asynchrone : le fichier existe déjà sur le téléphone | Import .wav/.mp3 au même niveau que le micro (US-02) |
| Le rêve est vécu comme un indicateur d'humeur | Émotion + icône au MVP (US-06), tendance mensuelle en R2 (US-16) avec mention « sans valeur médicale » |
| Le classement automatique doit rester corrigeable | Correction de l'émotion (US-14) ; la source de l'émotion (modèle / utilisateur) est stockée |
| La localisation des données conditionne la confiance | Critère « localisation UE » pondéré dans le scoring ; préférence fournisseurs UE (ADR-002 à ADR-004) |
| Faible disposition à payer au départ | Coût par rêve contraint (CS-03 ≤ 0,05 $) |
