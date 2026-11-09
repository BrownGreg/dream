# language: fr
# Généré par tools/backlog.py depuis docs/backlog/stories.toml — ne pas éditer
Fonctionnalité: Voir et entendre mon rêve

  # US-07 — En tant que rêveuse, je veux voir une image générée à partir de mon rêve, signalée comme produite par IA afin de redécouvrir mon rêve sous une forme visuelle.
  @US-07 @MVP
  Scénario: Image générée et marquée
    Étant donné que j'ai accepté le consentement
    Et que j'ai soumis un récit valide
    Quand le traitement se termine
    Alors je vois une image accompagnée de la mention « Image générée par IA »

  @US-07 @MVP
  Scénario: Image refusée par le filtre du fournisseur
    Étant donné que le fournisseur d'image refuse le prompt
    Quand je soumets un récit valide
    Alors mon rêve est enregistré sans image
    Et je vois le message « Image non générée : le service a refusé ce contenu »

  # US-08 — En tant que utilisateur pressé le matin, je veux voir l'avancement étape par étape et un message clair en cas d'échec afin de savoir s'il faut attendre, réessayer ou abandonner.
  @US-08 @MVP
  Scénario: Délai dépassé
    Étant donné que j'ai accepté le consentement
    Et que le service de transcription dépasse le délai
    Quand je soumets un récit valide
    Alors je vois le message « Le service met trop de temps à répondre »
    Et je peux relancer le traitement

  # US-11 — En tant que personne sujette aux cauchemars, je veux choisir de ne pas générer d'image pour un rêve afin de ne pas revoir une scène qui m'a angoissée.
  @US-11 @MVP
  Scénario: Rêve sans image
    Étant donné que j'ai accepté le consentement
    Et que j'ai coché « Ne pas générer d'image »
    Quand je soumets un récit valide
    Alors aucun appel au générateur d'image n'est effectué
    Et mon rêve est enregistré avec sa transcription et son émotion

  # US-13 — En tant que rêveuse, je veux écouter une ambiance sonore accordée à l'émotion de mon rêve afin de replonger dans l'atmosphère du rêve.
  @US-13 @MVP
  Scénario: Ambiance associée à l'émotion
    Étant donné un rêve classé « mélancolique »
    Quand j'ouvre le rêve
    Alors une ambiance sonore « mélancolique » est proposée en lecture

  # US-23 — En tant que rêveuse, je veux écouter le titre et le résumé de mon rêve lus par une voix française afin de revivre mon rêve les yeux fermés.
  @US-23 @R2
  Scénario: Lecture vocale du résumé
    Étant donné un rêve classé « serein »
    Quand je demande la lecture vocale
    Alors un fichier audio du résumé est associé au rêve

  # US-19 — En tant que rêveuse créative, je veux choisir un style visuel (aquarelle, photo, croquis) afin de obtenir une image qui me ressemble.
  @US-19 @R3
  Scénario: Style appliqué
    Étant donné que j'ai choisi le style « aquarelle »
    Quand je soumets un récit valide
    Alors le prompt visuel contient le style « aquarelle »

  # US-20 — En tant que rêveuse, je veux obtenir une micro-vidéo de 5 secondes de mon rêve afin de voir mon rêve en mouvement.
  @US-20 @R3
  Scénario: Micro-vidéo à la demande
    Étant donné un rêve avec image
    Quand je demande une micro-vidéo
    Alors une vidéo de 5 secondes maximum est associée au rêve
