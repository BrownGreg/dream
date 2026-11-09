# Annexe — Matrice de Kano

Classement établi à partir des entretiens simulés et des personae (méthode qualitative ; un questionnaire Kano fonctionnel/dysfonctionnel est prévu en bêta pour le confirmer). La colonne MoSCoW est **reprise** de `docs/backlog/stories.toml` ; `tools/backlog.py` vérifie la règle « un basique n'est jamais en *Could* ».

Légende : **B** basique (son absence mécontente, sa présence passe inaperçue) · **P** performance (satisfaction proportionnelle) · **E** enthousiasmante (surprise positive) · **I** indifférente · **R** inverse (sa présence mécontente une partie des utilisateurs).

| Fonctionnalité | Kano | Justification (1 ligne) | Stories | MoSCoW |
|---|---|---|---|---|
| Enregistrement micro en un geste | B | Sans capture immédiate, le rêve est perdu (Léa, Q1). | US-01 | Must |
| Import .wav / .mp3 | B | Karim enregistre déjà avec son dictaphone ; exigence du sujet. | US-02 | Must |
| Consentement explicite et granulaire | B | Inès n'utilise pas un service qui ne dit pas où part sa voix. | US-03 | Must |
| Transcription affichée | B | Preuve que le rêve a été « entendu » ; base de tout le reste. | US-04 | Must |
| Correction de la transcription | P | Plus la correction est simple, plus l'image est fidèle. | US-05 | Should |
| Émotion + icône + couleur | P | Valeur croissante avec la justesse du classement (Karim, Q6). | US-06 | Must |
| Correction de l'émotion | P | Restitue le contrôle quand le modèle se trompe (Karim, Q7). | US-14 | Should |
| Image générée (fidélité) | P | Satisfaction proportionnelle à la ressemblance (Léa, Q7). | US-07 | Must |
| Progression visible + erreurs claires | B | Une attente muette est vécue comme une panne (Léa, Q6). | US-08 | Must |
| Option « ne pas générer d'image » | B | Pour le segment vulnérable, l'image imposée est un motif d'abandon. | US-11 | Must |
| Historique des rêves | B | La relecture est la raison d'être du journal (Léa, Q4). | US-09 | Must |
| Filtre par émotion + frise | P | Rend l'historique exploitable à mesure qu'il grossit. | US-10 | Should |
| Suppression d'un rêve en cascade | B | Droit à l'effacement attendu par tous, critique pour Inès. | US-12 | Must |
| Suppression du compte | B | Idem, à l'échelle du compte. | US-17 | Must |
| Export de mes données | B | Portabilité attendue dès qu'il y a des données personnelles. | US-15 | Must |
| Ambiance sonore | E | Non demandée spontanément ; effet « waouh » attendu. | US-13 | Should |
| Lecture vocale du résumé | E | Prolonge l'immersion ; jamais demandée. | US-23 | Could |
| Tendance mensuelle des émotions | E | Personne ne l'exige, Karim y voit son « thermomètre ». | US-16 | Could |
| Choix du style visuel | E | Personnalisation appréciée, jamais réclamée. | US-19 | Could |
| Micro-vidéo | E | Promesse forte mais coût et latence élevés (cf. section 4). | US-20 | Could |
| Rappel matinal | I | Ni attendu ni rejeté ; risque d'intrusion au réveil. | US-18 | Could |
| Partage public sur les réseaux | R | Rêves jugés « plus intimes que mes photos » (Léa, Q8). | US-21 | Won't |
| Interprétation psychologique | R | Perçue comme non crédible (Léa, Q9) et risquée (prétention diagnostique). | US-22 | Won't |

**Lecture** : les 10 basiques sont tous en *Must* ; les fonctionnalités enthousiasmantes sont repoussées en R2/R3 sauf l'ambiance (*Should*, exigée par le sujet) ; les deux inverses sont exclues et tracées pour que le jury voie la décision.
