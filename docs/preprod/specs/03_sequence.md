```{=typst}
#page(flipped: true, margin: (x: 1.2cm, top: 1.5cm, bottom: 1.3cm))[
  = 3. Séquence clé : traitement complet d'un rêve
  #grid(columns: (1fr, 6.4cm), gutter: 0.5cm,
    figure(
      image("{{root}}/docs/diagrams/sequence_reve.svg", width: 100%, height: 15.2cm, fit: "contain"),
      caption: [Diagramme de séquence UML — traitement d'un rêve, branches d'erreur incluses],
    ),
    [
      #set text(size: 9pt)
      #set par(justify: false)
      *Points de conception*

      - *Validation avant tout stockage* (3–6) : fichier invalide, consentement absent ou quota atteint ne déclenchent aucun appel payant.
      - *Audio éphémère* (21) : supprimé dès la transcription enregistrée ; en cas d'échec définitif, conservé 24 h au plus pour « Relancer », puis purgé.
      - *Retries comptés* (16) : 2 nouvelles tentatives après 0,5 s puis 1 s (backoff exponentiel), sur timeout, `429` et `5xx` ; une ligne `api_calls` par tentative.
      - *Sortie LLM contrôlée* (24) : validée contre `DreamAnalysis`, un second essai, puis échec explicite.
      - *Image ∥ ambiance* (bloc `par`) : sautée si l'utilisateur l'a refusée, sans consentement « image » ou budget épuisé (ADR-007).
      - *Rejet du filtre de sécurité* (28–29) : le rêve aboutit sans image, motif `safety`, sans nouvelle tentative avec un prompt modifié.
      - *Copie immédiate* (31) : l'URL fournisseur expire en 10 min et n'est jamais exposée au navigateur.
    ],
  )
]
```
