# language: fr
# Généré par tools/backlog.py depuis docs/backlog/stories.toml — ne pas éditer
Fonctionnalité: Raconter mon rêve

  # US-01 — En tant que rêveuse au réveil, je veux enregistrer mon rêve au micro en un seul geste afin de le capturer avant qu'il ne s'efface.
  @US-01 @MVP
  Scénario: Enregistrement micro valide
    Étant donné que j'ai accepté le consentement
    Quand j'enregistre un récit de 45 secondes au micro
    Alors l'audio est accepté pour traitement

  @US-01 @MVP
  Scénario: Enregistrement trop court
    Étant donné que j'ai accepté le consentement
    Quand j'enregistre un récit de 1 seconde au micro
    Alors je vois le message « Enregistrement trop court (minimum 3 s) »

  # US-02 — En tant que utilisateur ayant déjà un mémo vocal, je veux importer un fichier .wav ou .mp3 afin de réutiliser un enregistrement fait avec mon dictaphone.
  @US-02 @MVP
  Scénario: Import d'un fichier mp3 valide
    Étant donné que j'ai accepté le consentement
    Quand j'importe le fichier « reve.mp3 » de 2 Mo
    Alors l'audio est accepté pour traitement

  @US-02 @MVP
  Scénario: Import d'un format refusé
    Étant donné que j'ai accepté le consentement
    Quand j'importe le fichier « reve.ogg » de 2 Mo
    Alors je vois le message « Format non pris en charge : utilisez .wav ou .mp3 »

  @US-02 @MVP
  Scénario: Import d'un fichier trop lourd
    Étant donné que j'ai accepté le consentement
    Quand j'importe le fichier « reve.wav » de 30 Mo
    Alors je vois le message « Fichier trop volumineux (maximum 20 Mo) »

  # US-03 — En tant que utilisateur, je veux donner un consentement explicite et séparé pour l'envoi de ma voix et de mon récit aux services d'IA afin de savoir précisément ce qui sort de l'application et pouvoir le retirer.
  @US-03 @MVP
  Scénario: Traitement bloqué sans consentement
    Étant donné que je n'ai pas accepté le consentement
    Quand j'importe le fichier « reve.mp3 » de 2 Mo
    Alors je vois le message « Consentement requis avant tout traitement »
