# language: fr
# Généré par tools/backlog.py depuis docs/backlog/stories.toml — ne pas éditer
Fonctionnalité: Garder le contrôle

  # US-12 — En tant que utilisateur, je veux supprimer définitivement un rêve et tous ses fichiers afin de exercer mon droit à l'effacement.
  @US-12 @MVP
  Scénario: Suppression en cascade
    Étant donné un rêve avec transcription, émotion et image
    Quand je le supprime
    Alors le rêve n'apparaît plus dans « Mes rêves »
    Et aucun fichier associé ne subsiste

  # US-15 — En tant que utilisateur, je veux exporter tous mes rêves dans un format ouvert afin de exercer mon droit à la portabilité.
  @US-15 @R2
  Scénario: Export JSON
    Étant donné que j'ai enregistré 2 rêves
    Quand je demande l'export
    Alors je reçois un fichier JSON valide contre « dream.schema.json » contenant 2 rêves

  # US-17 — En tant que utilisateur, je veux supprimer mon compte et l'ensemble de mes données afin de quitter le service sans laisser de trace.
  @US-17 @R2
  Scénario: Suppression du compte
    Étant donné un compte avec 3 rêves
    Quand je supprime mon compte
    Alors aucun rêve, fichier ni consentement rattaché ne subsiste hors journal d'audit anonymisé
