// CV sobre, compatible ATS : une colonne, pas de tableau.
#import "../common.typ": *

#let d = json(bytes(sys.inputs.data))
#let id = d.identite

#set document(title: "CV – " + id.nom_complet, author: id.nom_complet)
#set page(paper: "a4", margin: (x: 1.6cm, y: 1.3cm))
#set text(font: polices, size: 9.5pt, lang: "fr")
#set par(leading: 0.5em, spacing: 0.6em)
#set list(indent: 0.4em, body-indent: 0.5em, spacing: 0.45em)

#let section(titre) = {
  v(0.5em)
  block(below: 0.45em, {
    text(size: 10.5pt, weight: "bold", fill: accent, upper(titre))
    v(-0.5em)
    line(length: 100%, stroke: 0.5pt + accent)
  })
}

#let entete(gauche, droite) = block(below: 0.3em, {
  gauche
  h(1fr)
  text(fill: luma(90), droite)
})

// --- En-tête ---
#align(center)[
  #text(size: 18pt, weight: "bold", id.nom_complet) \
  #if d.titre != "" { text(size: 11pt, fill: accent, d.titre) } \
  #text(size: 8.5pt, nonvide((id.ville, id.email, id.telephone, id.linkedin, id.github, id.site)).join("  ·  "))
]

#if d.accroche != "" {
  v(0.3em)
  par(justify: true, d.accroche)
}

// --- Expériences ---
#if d.experiences.len() > 0 {
  section("Expériences professionnelles")
  for e in d.experiences {
    entete(
      [*#e.poste* — #e.entreprise#if e.lieu != "" [, #e.lieu]],
      periode(e.date_debut, e.date_fin),
    )
    if e.realisations.len() > 0 { list(..e.realisations) }
    if e.stack.len() > 0 {
      block(above: 0.35em, below: 0.7em, text(size: 8.5pt, fill: luma(80))[_Stack :_ #e.stack.join(", ")])
    } else { v(0.4em) }
  }
}

// --- Projets ---
#if d.projets.len() > 0 {
  section("Projets")
  for p in d.projets {
    block(below: 0.45em)[
      *#p.nom*#if p.description != "" [ — #p.description]
      #if p.stack.len() > 0 { text(size: 8.5pt, fill: luma(80))[ (#p.stack.join(", "))] }
    ]
  }
}

// --- Compétences ---
#if d.competences.len() > 0 {
  section("Compétences")
  for c in d.competences {
    block(below: 0.35em)[*#c.categorie :* #c.items.join(", ")]
  }
}

// --- Formation ---
#if d.formations.len() > 0 {
  section("Formation")
  for f in d.formations {
    entete([*#f.diplome* — #f.etablissement], periode(f.date_debut, f.date_fin))
    if f.details != "" { block(above: 0em, below: 0.5em, text(size: 9pt, f.details)) }
  }
}

// --- Langues et centres d'intérêt ---
#if d.langues.len() > 0 or d.centres_interet.len() > 0 {
  section("Langues et centres d'intérêt")
  if d.langues.len() > 0 {
    block(below: 0.35em)[*Langues :* #d.langues.map(l => if l.niveau != "" { l.langue + " (" + l.niveau + ")" } else { l.langue }).join(", ")]
  }
  if d.centres_interet.len() > 0 {
    block[*Centres d'intérêt :* #d.centres_interet.join(", ")]
  }
}
