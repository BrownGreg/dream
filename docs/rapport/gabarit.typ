// Gabarit du rapport de production, dérivé de docs/preprod/templates/dossier.typ (même mise en page que le bloc 1).
// Taille de police fixée ici une fois pour toutes.

#let horizontalrule = line(length: 100%, stroke: 0.5pt + luma(180))

#let dossier(title: "", body) = {
  set document(title: title, author: "Gregory Hery")
  set text(lang: "fr", font: "Liberation Sans", size: 10.5pt)
  set par(justify: true, leading: 0.55em, spacing: 0.8em)
  set page(
    paper: "a4",
    margin: (x: 1.8cm, top: 1.8cm, bottom: 1.8cm),
    header: context {
      if counter(page).get().first() > 1 [
        #set text(size: 8pt, fill: luma(110))
        Synthétiseur de rêves — #title #h(1fr) Production · Bloc 3
      ]
    },
    footer: context {
      if counter(page).get().first() > 1 [
        #set text(size: 8pt, fill: luma(110))
        #h(1fr) #counter(page).display("1 / 1", both: true)
      ]
    },
  )
  set heading(numbering: none)
  show heading.where(level: 1): it => {
    set text(size: 15pt, fill: rgb("#4B3F72"))
    block(above: 1.1em, below: 0.6em, it.body)
  }
  show heading.where(level: 2): it => {
    set text(size: 12pt, fill: rgb("#4B3F72"))
    block(above: 0.9em, below: 0.45em, it.body)
  }
  show heading.where(level: 3): it => block(above: 0.7em, below: 0.35em, text(size: 10.5pt, it.body))
  set table(stroke: 0.4pt + luma(190), inset: (x: 4pt, y: 3pt), align: left)
  show table: set text(size: 8.5pt)
  show table: set par(justify: false)
  show table.cell.where(y: 0): set text(weight: "bold")
  show figure.where(kind: table): set block(breakable: true)
  show figure.caption: set text(size: 8.5pt, style: "italic")
  set image(width: 100%, fit: "contain")
  show raw: set text(font: "DejaVu Sans Mono", size: 8pt)
  // Identifiants longs (noms de tests, chemins) : coupure permise après « _ », « . » et « / ».
  show raw.where(block: false): it => { show regex("[_./]"): c => c + sym.zws; it }
  show link: set text(fill: rgb("#2B6CB0"))

  // Page de garde
  page(header: none, footer: none)[
    #v(5cm)
    #text(size: 11pt, fill: luma(100))[Projet « Synthétiseur de rêves » · Bloc 3 · Production]
    #v(0.4cm)
    #text(size: 26pt, weight: "bold", fill: rgb("#4B3F72"))[#title]
    #v(1.2cm)
    #grid(columns: (auto, 1fr), gutter: 0.5em,
      [*Auteur*], [Gregory Hery],
      [*École*], [HETIC],
      [*Date de rendu*], [à compléter],
      [*Dépôt*], [#link("https://github.com/BrownGreg/dream")[github.com/BrownGreg/dream]],
    )
    #v(1fr)
    #outline(title: [Sommaire], depth: 1, indent: 1em)
  ]
  counter(page).update(2)
  body
}
