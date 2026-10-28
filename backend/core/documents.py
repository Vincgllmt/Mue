"""Documents générés : validation du contenu, garde-fou, rendu PDF, texte brut."""

from datetime import date

from . import guard, pdf
from .models import GeneratedDoc
from .schemas import DOC_SCHEMAS, CvCompetences, CvDocument, CvExperience, CvFormation, CvProjet, LetterDocument, ProfileData

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


def date_fr(d: date) -> str:
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def lieu_date(profile: ProfileData, d: date | None = None) -> str:
    d = d or date.today()
    ville = profile.identite.ville
    return f"{ville}, le {date_fr(d)}" if ville else f"Le {date_fr(d)}"


def letter_text(content: dict) -> str:
    """Texte brut copiable (formulaires en ligne, e-mails)."""
    if "texte" in content:
        return content["texte"]
    parts = [content.get("salutation", ""), *content.get("paragraphes", []), content.get("formule_politesse", "")]
    name = (content.get("identite") or {}).get("nom_complet", "")
    return "\n\n".join(p for p in [*parts, name] if p)


def profile_to_cv(profile: ProfileData) -> CvDocument:
    """CV complet (non ciblé) tiré du profil, pour l'aperçu PDF d'un profil révisé."""
    categories: dict[str, list[str]] = {}
    for c in profile.competences:
        categories.setdefault(c.categorie or "Compétences", []).append(c.nom)
    return CvDocument(
        identite=profile.identite,
        titre=profile.titre,
        accroche=profile.accroche,
        experiences=[CvExperience(**e.model_dump()) for e in profile.experiences],
        formations=[CvFormation(**f.model_dump()) for f in profile.formations],
        competences=[CvCompetences(categorie=k, items=v) for k, v in categories.items()],
        projets=[CvProjet(**p.model_dump()) for p in profile.projets],
        langues=profile.langues,
        centres_interet=profile.centres_interet,
    )


def check(kind: str, content: dict, profile: ProfileData, offer_text: str = "") -> list[dict]:
    if kind == "cv":
        return guard.check_cv(CvDocument.model_validate(content), profile)
    if kind == "letter":
        return guard.check_letter(LetterDocument.model_validate(content), profile, offer_text)
    return guard.check_text("texte", content.get("texte", ""), profile, offer_text)


def update_content(doc: GeneratedDoc, content: dict, profile: ProfileData) -> GeneratedDoc:
    """Valide, contrôle et re-rend un document (création ou édition manuelle)."""
    clean = DOC_SCHEMAS[doc.kind].model_validate(content).model_dump()
    doc.content = clean
    doc.warnings = check(doc.kind, clean, profile, doc.application.offer.raw_text)
    if doc.kind in pdf.TEMPLATES:
        if not doc.pk:
            doc.save()
        path = pdf.render_to_file(doc.kind, clean, f"{doc.kind}_{doc.pk}.pdf", doc.template)
        doc.pdf_path = str(path)
    doc.save()
    return doc
