// Fonctions partagées par les templates Mue.
#let mois = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")

// "2021-03" -> "mars 2021" ; "2021" -> "2021" ; autre -> inchangé
#let fdate(s) = {
  if s == none or s == "" { return "" }
  let parts = s.split("-")
  if parts.len() >= 2 and parts.at(1).match(regex("^\d{1,2}$")) != none {
    let m = int(parts.at(1))
    if m >= 1 and m <= 12 { return mois.at(m - 1) + " " + parts.at(0) }
  }
  s
}

#let periode(debut, fin) = {
  if debut == "" and fin == "" { "" }
  else if debut == "" { fdate(fin) }
  else if fin == "" { "depuis " + fdate(debut) }
  else if debut == fin { fdate(debut) }
  else { fdate(debut) + " – " + fdate(fin) }
}

#let nonvide(xs) = xs.filter(x => x != none and x != "")

#let polices = ("Calibri", "Arial", "Liberation Sans", "DejaVu Sans")
#let accent = rgb("#1f4e79")
