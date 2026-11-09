# language: fr
# Généré par tools/backlog.py depuis docs/backlog/stories.toml — ne pas éditer
Fonctionnalité: Comprendre mon rêve

  # US-04 — En tant que rêveuse, je veux lire la transcription de mon récit afin de vérifier que l'application a bien compris mon rêve.
  @US-04 @MVP
  Scénario: Transcription affichée
    Étant donné que j'ai accepté le consentement
    Et que j'ai soumis un récit valide
    Quand le traitement se termine
    Alors je vois une transcription non vide

  @US-04 @MVP
  Scénario: Service de transcription indisponible
    Étant donné que j'ai accepté le consentement
    Et que le service de transcription est indisponible
    Quand je soumets un récit valide
    Alors je vois le message « Transcription indisponible, réessayez dans un instant »
    Et mon audio n'est pas perdu

  # US-05 — En tant que rêveuse, je veux corriger la transcription avant la génération afin de que l'image corresponde à mon rêve et pas à une erreur de reconnaissance.
  @US-05 @MVP
  Scénario: Correction prise en compte
    Étant donné une transcription « un shat noir »
    Quand je la corrige en « un chat noir »
    Alors la génération utilise « un chat noir »

  # US-06 — En tant que utilisateur qui suit son humeur, je veux voir l'émotion dominante de mon rêve avec une icône et une couleur afin de repérer d'un coup d'œil l'ambiance de mes nuits.
  @US-06 @MVP
  Scénario: Émotion affichée avec icône
    Étant donné la transcription « je tombais dans le vide et personne ne m'entendait »
    Quand l'émotion est classée
    Alors je vois l'émotion « stressant » avec son icône et sa couleur

  # US-14 — En tant que utilisateur, je veux corriger l'émotion proposée afin de mon historique reflète mon ressenti et non celui du modèle.
  @US-14 @R2
  Scénario: Émotion corrigée par l'utilisateur
    Étant donné un rêve classé « neutre »
    Quand je choisis l'émotion « heureux »
    Alors le rêve est enregistré avec l'émotion « heureux » et la source « utilisateur »
