import copy

from core.guard import check_cv, check_letter, normalize
from core.schemas import CvDocument, LetterDocument, ProfileData

from .fixtures import CV, PROFILE

profile = ProfileData.model_validate(PROFILE)


def _cv(**changes) -> CvDocument:
    data = copy.deepcopy(CV)
    data.update(changes)
    return CvDocument.model_validate(data)


def _levels(warnings):
    return [(w["niveau"], w["champ"]) for w in warnings]


def test_normalize():
    assert normalize("  Université  de NANTES ") == "universite de nantes"
    assert normalize("C#") == "c#"


def test_clean_cv_has_no_warning():
    assert check_cv(_cv(), profile) == []


def test_company_case_and_accents_tolerated():
    cv = _cv()
    cv.experiences[0].entreprise = "exemple sas"
    assert check_cv(cv, profile) == []


def test_invented_company_is_an_error():
    cv = _cv()
    cv.experiences[0].entreprise = "Google"
    assert ("erreur", "experiences.0") in _levels(check_cv(cv, profile))


def test_wrong_dates_are_an_error():
    cv = _cv()
    cv.experiences[0].date_debut = "2020-01"
    warnings = check_cv(cv, profile)
    assert ("erreur", "experiences.0") in _levels(warnings)
    assert "Dates" in warnings[0]["message"]


def test_invented_diploma_is_an_error():
    cv = _cv()
    cv.formations[0].diplome = "Doctorat"
    assert ("erreur", "formations.0") in _levels(check_cv(cv, profile))


def test_unknown_skill_is_a_warning():
    cv = _cv()
    cv.competences[0].items.append("Kubernetes")
    assert ("avertissement", "competences.0") in _levels(check_cv(cv, profile))


def test_skill_mentioned_in_text_is_tolerated():
    cv = _cv()
    cv.competences[0].items.append("Symfony")  # dans la stack d'une expérience
    cv.competences[0].items.append("API")  # mot présent dans une réalisation
    assert check_cv(cv, profile) == []


def test_invented_number_is_a_warning():
    cv = _cv()
    cv.experiences[0].realisations.append("Réduit la latence de 40 %")
    assert ("avertissement", "experiences.0.realisations.1") in _levels(check_cv(cv, profile))


def test_letter_numbers_may_come_from_offer():
    letter = LetterDocument(objet="Candidature", paragraphes=["Votre équipe de 15 personnes", "J'ai livré 3 applications"])
    assert check_letter(letter, profile, offer_text="Équipe de 15 développeurs") == []
    assert len(check_letter(letter, profile)) == 1
