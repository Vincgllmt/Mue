import io

import pytest
from pypdf import PdfReader

from core import pdf
from core.schemas import CvDocument, LetterDocument, ProfileData

from .fixtures import CV, PROFILE


def _pages(data: bytes) -> PdfReader:
    assert data.startswith(b"%PDF")
    return PdfReader(io.BytesIO(data))


def test_render_cv_one_page_with_content():
    content = CvDocument(**CV, identite=ProfileData.model_validate(PROFILE).identite).model_dump()
    reader = _pages(pdf.render("cv", content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "Camille Martin" in text
    assert "depuis mars 2021" in text


def test_render_escapes_typst_markup():
    content = CvDocument(**{**CV, "accroche": "C# et *gras* #pas-une-commande $x$"}).model_dump()
    text = _pages(pdf.render("cv", content)).pages[0].extract_text()
    assert "*gras*" in text and "#pas-une-commande" in text


def test_render_letter():
    content = LetterDocument(
        objet="Candidature", paragraphes=["Premier paragraphe.", "Second paragraphe."], formule_politesse="Cordialement."
    ).model_dump()
    text = _pages(pdf.render("letter", content)).pages[0].extract_text()
    assert "Objet : Candidature" in text


def test_missing_template():
    with pytest.raises(pdf.RenderError):
        pdf.render("cv", {}, template="inexistant")
