// Lettre de motivation : en-tête, date, objet, signature.
#import "../common.typ": *

#let d = json(bytes(sys.inputs.data))
#let id = d.identite

#set document(title: "Lettre de motivation – " + id.nom_complet, author: id.nom_complet)
#set page(paper: "a4", margin: (x: 2.3cm, y: 2cm))
#set text(font: polices, size: 10.5pt, lang: "fr")
#set par(justify: true, leading: 0.65em, spacing: 1.1em)

#block(below: 1.5em)[
  #text(weight: "bold", size: 12pt, id.nom_complet) \
  #nonvide((id.ville, id.telephone, id.email)).join(linebreak())
]

#if d.destinataire != "" {
  align(right, block(below: 1.5em, d.destinataire))
}

#if d.lieu_date != "" { align(right, block(below: 2em, d.lieu_date)) }

#block(below: 1.5em)[*Objet :* #d.objet]

#d.salutation

#for p in d.paragraphes { par(p) }

#d.formule_politesse

#v(1.5em)
#align(right, id.nom_complet)
