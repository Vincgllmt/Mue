"""Schémas Pydantic : profil maître et sorties de l'IA.

Les dates sont des chaînes « AAAA-MM » ou « AAAA » ; `date_fin` vide = en cours.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- Profil maître -----------------------------------------------------------


class Identite(Schema):
    nom_complet: str = ""
    email: str = ""
    telephone: str = ""
    ville: str = ""
    linkedin: str = ""
    github: str = ""
    site: str = ""


class Experience(Schema):
    poste: str
    entreprise: str
    lieu: str = ""
    date_debut: str = ""
    date_fin: str = ""
    contexte: str = ""
    realisations: list[str] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)


class Formation(Schema):
    diplome: str
    etablissement: str
    lieu: str = ""
    date_debut: str = ""
    date_fin: str = ""
    details: str = ""


class Competence(Schema):
    nom: str
    categorie: str = ""
    niveau: str = ""


class Projet(Schema):
    nom: str
    description: str = ""
    realisations: list[str] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)
    url: str = ""
    date: str = ""


class Langue(Schema):
    langue: str
    niveau: str = ""


class ProfileData(Schema):
    identite: Identite = Field(default_factory=Identite)
    titre: str = ""
    accroche: str = ""
    experiences: list[Experience] = Field(default_factory=list)
    formations: list[Formation] = Field(default_factory=list)
    competences: list[Competence] = Field(default_factory=list)
    projets: list[Projet] = Field(default_factory=list)
    langues: list[Langue] = Field(default_factory=list)
    centres_interet: list[str] = Field(default_factory=list)


# --- F2. Analyse d'offre -------------------------------------------------------

Verdict = Literal["postuler", "postuler_avec_reserve", "ne_pas_postuler"]


class OfferAnalysis(Schema):
    entreprise: str = ""
    poste: str = ""
    lieu: str = ""
    contrat: str = ""
    teletravail: str = ""
    stack_requise: list[str] = Field(default_factory=list)
    stack_bonus: list[str] = Field(default_factory=list)
    seniorite: Literal["junior", "confirmé", "senior", ""] = ""
    mots_cles_ats: list[str] = Field(default_factory=list)
    score_matching: int = Field(ge=0, le=100)
    points_forts: list[str] = Field(default_factory=list)
    ecarts: list[str] = Field(default_factory=list)
    verdict: Verdict
    justification: str


# --- F3. CV adapté -----------------------------------------------------------------


class CvExperience(Schema):
    poste: str
    entreprise: str
    lieu: str = ""
    date_debut: str = ""
    date_fin: str = ""
    realisations: list[str] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)


class CvFormation(Schema):
    diplome: str
    etablissement: str
    date_debut: str = ""
    date_fin: str = ""
    details: str = ""


class CvCompetences(Schema):
    categorie: str
    items: list[str] = Field(default_factory=list)


class CvProjet(Schema):
    nom: str
    description: str = ""
    stack: list[str] = Field(default_factory=list)


class CvAdapte(Schema):
    """Ce que l'IA produit. L'identité est ajoutée par le code depuis le profil."""

    titre: str
    accroche: str = ""
    experiences: list[CvExperience] = Field(default_factory=list)
    formations: list[CvFormation] = Field(default_factory=list)
    competences: list[CvCompetences] = Field(default_factory=list)
    projets: list[CvProjet] = Field(default_factory=list)
    langues: list[Langue] = Field(default_factory=list)
    centres_interet: list[str] = Field(default_factory=list)


class CvDocument(CvAdapte):
    """Contenu complet d'un document CV, tel que stocké et rendu."""

    identite: Identite = Field(default_factory=Identite)


# --- F4. Lettre de motivation ----------------------------------------------------------


class LettreGeneree(Schema):
    objet: str
    salutation: str = "Madame, Monsieur,"
    paragraphes: list[str] = Field(min_length=2)
    formule_politesse: str
    version_courte: str = ""


class LetterDocument(Schema):
    identite: Identite = Field(default_factory=Identite)
    destinataire: str = ""
    lieu_date: str = ""
    objet: str
    salutation: str = "Madame, Monsieur,"
    paragraphes: list[str] = Field(default_factory=list)
    formule_politesse: str = ""


class ShortLetterDocument(Schema):
    texte: str


# --- F5. Audit ---------------------------------------------------------------------------

Axe = Literal["impact", "clarte", "coherence", "ats", "langue", "ciblage"]
Gravite = Literal["critique", "important", "mineur"]


class AuditSuggestion(Schema):
    id: str
    axe: Axe
    gravite: Gravite
    cible: str = Field(description="Chemin du champ, ex. experiences.0.realisations.2")
    avant: str = ""
    apres: str = ""
    explication: str = ""


class AuditQuestion(Schema):
    id: str
    cible: str
    avant: str = ""
    question: str


class AuditResult(Schema):
    suggestions: list[AuditSuggestion] = Field(default_factory=list)
    questions: list[AuditQuestion] = Field(default_factory=list)


# Contenu stocké par type de GeneratedDoc
DOC_SCHEMAS: dict[str, type[Schema]] = {
    "cv": CvDocument,
    "letter": LetterDocument,
    "letter_short": ShortLetterDocument,
}
