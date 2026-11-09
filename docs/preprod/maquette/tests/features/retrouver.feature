# language: fr
# Généré par tools/backlog.py depuis docs/backlog/stories.toml — ne pas éditer
Fonctionnalité: Retrouver mes rêves

  # US-09 — En tant que utilisateur régulier, je veux retrouver la liste de mes rêves passés, du plus récent au plus ancien afin de relire mes rêves de la semaine.
  @US-09 @MVP
  Scénario: Historique trié
    Étant donné que j'ai enregistré 3 rêves
    Quand j'ouvre « Mes rêves »
    Alors je vois 3 rêves du plus récent au plus ancien

  # US-10 — En tant que utilisateur régulier, je veux filtrer mes rêves par émotion et les voir sur une frise afin de repérer des périodes de rêves stressants.
  @US-10 @MVP
  Scénario: Filtre par émotion
    Étant donné que j'ai enregistré 2 rêves « heureux » et 1 rêve « stressant »
    Quand je filtre sur « stressant »
    Alors je vois 1 rêve

  # US-16 — En tant que utilisateur qui suit son humeur, je veux voir la répartition mensuelle de mes émotions afin de observer une tendance sans interprétation médicale.
  @US-16 @R2
  Scénario: Répartition mensuelle
    Étant donné que j'ai enregistré des rêves sur 2 mois
    Quand j'ouvre la vue « Tendances »
    Alors je vois une répartition des émotions par mois
    Et je vois la mention « Indicateur personnel, sans valeur médicale »

  # US-18 — En tant que utilisateur qui oublie, je veux recevoir un rappel matinal optionnel afin de penser à raconter mon rêve au réveil.
  @US-18 @R3
  Scénario: Rappel désactivé par défaut
    Étant donné un nouveau compte
    Alors aucun rappel n'est programmé
