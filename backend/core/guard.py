"""Garde-fou anti-invention : compare un document généré au profil maître.

Chaque avertissement : {"niveau": "erreur" | "avertissement", "champ": str, "message": str}.
- erreur : entreprise, diplôme ou date absents du profil (le CV ment) ;
- avertissement : compétence ou chiffre absents du profil (à vérifier).
"""

import re
import unicodedata
from typing import Any, Iterable

from .schemas import CvDocument, LetterDocument, ProfileData

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^\w+#]+", " ", text)
    return " ".join(text.split())


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER.findall(text or "")}


def profile_numbers(profile: ProfileData, extra_text: str = "") -> set[str]:
    nums: set[str] = set()
    for s in _strings(profile.model_dump()):
        nums |= _numbers(s)
    return nums | _numbers(extra_text)


def profile_skills(profile: ProfileData) -> set[str]:
    skills = {normalize(c.nom) for c in profile.competences}
    for item in [*profile.experiences, *profile.projets]:
        skills |= {normalize(s) for s in item.stack}
    return skills - {""}


def _skill_known(skill: str, known: set[str], corpus: str) -> bool:
    n = normalize(skill)
    if not n or n in known:
        return True
    # Toléré si le terme apparaît mot pour mot dans le profil (ex. dans une réalisation).
    return re.search(rf"(?<!\w){re.escape(n)}(?!\w)", corpus) is not None


def _err(champ: str, message: str) -> dict:
    return {"niveau": "erreur", "champ": champ, "message": message}


def _warn(champ: str, message: str) -> dict:
    return {"niveau": "avertissement", "champ": champ, "message": message}


def _check_numbers(fields: list[tuple[str, str]], allowed: set[str]) -> list[dict]:
    out = []
    for champ, text in fields:
        for n in sorted(_numbers(text) - allowed):
            out.append(_warn(champ, f"Le chiffre « {n} » n'apparaît pas dans le profil maître."))
    return out


def check_cv(cv: CvDocument, profile: ProfileData) -> list[dict]:
    warnings: list[dict] = []
    corpus = normalize(" ".join(_strings(profile.model_dump())))

    exps = {normalize(e.entreprise): e for e in profile.experiences}
    for i, e in enumerate(cv.experiences):
        champ = f"experiences.{i}"
        src = exps.get(normalize(e.entreprise))
        if src is None:
            warnings.append(_err(champ, f"L'entreprise « {e.entreprise} » n'existe pas dans le profil maître."))
            continue
        same_company = [p for p in profile.experiences if normalize(p.entreprise) == normalize(e.entreprise)]
        if not any(p.date_debut == e.date_debut and p.date_fin == e.date_fin for p in same_company):
            warnings.append(_err(champ, f"Dates {e.date_debut} – {e.date_fin or 'en cours'} chez {e.entreprise} absentes du profil."))

    for i, f in enumerate(cv.formations):
        champ = f"formations.{i}"
        matches = [
            p for p in profile.formations
            if normalize(p.diplome) == normalize(f.diplome) and normalize(p.etablissement) == normalize(f.etablissement)
        ]
        if not matches:
            warnings.append(_err(champ, f"Le diplôme « {f.diplome} » ({f.etablissement}) n'existe pas dans le profil maître."))
        elif not any(p.date_debut == f.date_debut and p.date_fin == f.date_fin for p in matches):
            warnings.append(_err(champ, f"Dates du diplôme « {f.diplome} » absentes du profil."))

    known = profile_skills(profile)
    cv_skills = [(f"competences.{i}", s) for i, c in enumerate(cv.competences) for s in c.items]
    cv_skills += [(f"experiences.{i}.stack", s) for i, e in enumerate(cv.experiences) for s in e.stack]
    cv_skills += [(f"projets.{i}.stack", s) for i, p in enumerate(cv.projets) for s in p.stack]
    seen = set()
    for champ, s in cv_skills:
        if normalize(s) in seen or _skill_known(s, known, corpus):
            continue
        seen.add(normalize(s))
        warnings.append(_warn(champ, f"La compétence « {s} » est absente du profil maître."))

    # Chiffres : on ignore les champs de dates, contrôlés plus haut.
    text_fields = [("titre", cv.titre), ("accroche", cv.accroche)]
    for i, e in enumerate(cv.experiences):
        text_fields += [(f"experiences.{i}.realisations.{j}", r) for j, r in enumerate(e.realisations)]
    for i, p in enumerate(cv.projets):
        text_fields.append((f"projets.{i}.description", p.description))
    warnings += _check_numbers(text_fields, profile_numbers(profile))
    return warnings


def check_letter(letter: LetterDocument, profile: ProfileData, offer_text: str = "") -> list[dict]:
    fields = [("objet", letter.objet)] + [(f"paragraphes.{i}", p) for i, p in enumerate(letter.paragraphes)]
    return _check_numbers(fields, profile_numbers(profile, offer_text))


def check_text(champ: str, text: str, profile: ProfileData, offer_text: str = "") -> list[dict]:
    return _check_numbers([(champ, text)], profile_numbers(profile, offer_text))
