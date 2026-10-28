"""Parcours complets via l'API, avec Claude mocké et Huey synchrone."""

import json

import pytest
import yaml
from django.conf import settings
from rest_framework.test import APIClient

from core import claude_client
from core.claude_client import ClaudeError
from core.models import Profile

from .fixtures import ANALYSIS, AUDIT, CV, LETTER, OFFER_TEXT, PROFILE, REVISION

pytestmark = pytest.mark.django_db

RESPONSES = {
    "analyze_offer": ANALYSIS,
    "generate_cv": CV,
    "generate_letter": LETTER,
    "audit_cv": AUDIT,
    "extract_profile": PROFILE,
    "revise_cv": REVISION,
}


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def fake_claude(monkeypatch):
    """Répond selon le prompt (titre de section propre à chaque tâche)."""
    state = {"responses": dict(RESPONSES), "error": None}
    markers = {
        "Tu analyses une offre": "analyze_offer",
        "CV d'**une page**": "generate_cv",
        "lettre de motivation française": "generate_letter",
        "Tu audites un CV": "audit_cv",
        "texte brut d'un CV": "extract_profile",
        "Tu révises un CV": "revise_cv",
    }

    def fake(prompt, timeout=None):
        if state["error"]:
            raise ClaudeError(state["error"])
        task = next(t for marker, t in markers.items() if marker in prompt)
        return {"result": json.dumps(state["responses"][task]), "total_cost_usd": 0.02, "is_error": False}

    monkeypatch.setattr(claude_client, "call_claude_cli", fake)
    return state


@pytest.fixture
def with_profile(api):
    r = api.put("/api/profile", {"data": PROFILE}, format="json")
    assert r.status_code == 200, r.data
    return r.data


def _create_offer(api) -> tuple[int, int]:
    r = api.post("/api/offers", {"raw_text": OFFER_TEXT, "url": "https://exemple.fr/offre"}, format="json")
    assert r.status_code == 202, r.data
    return r.data["offer"]["id"], r.data["job_id"]


def test_profile_versions_and_yaml(api, with_profile):
    assert with_profile["version"] == 1
    assert yaml.safe_load(settings.PROFILE_YAML.read_text(encoding="utf-8"))["titre"] == PROFILE["titre"]

    # Même contenu : pas de nouvelle version.
    assert api.put("/api/profile", {"data": PROFILE}, format="json").data["version"] == 1

    # Édition à la main du YAML : détectée au GET.
    data = yaml.safe_load(settings.PROFILE_YAML.read_text(encoding="utf-8"))
    data["titre"] = "Lead dev"
    settings.PROFILE_YAML.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    r = api.get("/api/profile")
    assert r.data["version"] == 2 and r.data["data"]["titre"] == "Lead dev"

    # Rollback
    r = api.post("/api/profile/versions/1/restore")
    assert r.data["version"] == 3 and r.data["data"]["titre"] == PROFILE["titre"]
    assert [v["version"] for v in api.get("/api/profile/versions").data] == [3, 2, 1]


def test_invalid_yaml_is_reported(api, with_profile):
    settings.PROFILE_YAML.write_text("experiences: [{poste: 1", encoding="utf-8")
    r = api.get("/api/profile")
    assert r.data["version"] == 1 and "invalide" in r.data["yaml_error"]


def test_offer_cv_letter_flow(api, with_profile, fake_claude):
    offer_id, job_id = _create_offer(api)
    job = api.get(f"/api/jobs/{job_id}").data
    assert job["status"] == "done", job

    offer = api.get(f"/api/offers/{offer_id}").data
    assert offer["verdict"] == "postuler" and offer["score"] == 80

    # CV
    job = api.get(f"/api/jobs/{api.post(f'/api/offers/{offer_id}/generate-cv', {}, format='json').data['job_id']}").data
    assert job["status"] == "done", job
    doc = api.get(f"/api/docs/{job['result']['doc_id']}").data
    assert doc["warnings"] == []
    assert doc["content"]["identite"]["nom_complet"] == "Camille Martin"
    pdf = api.get(f"/api/docs/{doc['id']}/pdf")
    assert pdf.status_code == 200 and b"".join(pdf.streaming_content).startswith(b"%PDF")

    # Édition manuelle : re-rendu + garde-fou
    content = doc["content"]
    content["experiences"][0]["entreprise"] = "Inventée"
    r = api.put(f"/api/docs/{doc['id']}", {"content": content}, format="json")
    assert r.status_code == 200
    assert r.data["warnings"][0]["niveau"] == "erreur"

    # Lettre + version courte
    r = api.post(f"/api/offers/{offer_id}/generate-letter", {"ton": "direct", "longueur": "courte", "short": True}, format="json")
    job = api.get(f"/api/jobs/{r.data['job_id']}").data
    assert job["status"] == "done", job
    letter = api.get(f"/api/docs/{job['result']['doc_id']}").data
    assert letter["content"]["destinataire"] == "Acme"
    assert "Camille Martin" in letter["text"]
    short = api.get(f"/api/docs/{job['result']['short_doc_id']}").data
    assert short["pdf_url"] is None and short["text"].startswith("Bonjour")

    # Historique et statut
    listing = api.get("/api/offers").data
    app = listing[0]["application"]
    assert len(app["docs"]) == 3 and app["profile_version"] == 1
    assert api.patch(f"/api/applications/{app['id']}", {"status": "envoyee"}, format="json").data["status"] == "envoyee"
    assert api.patch(f"/api/applications/{app['id']}", {"status": "nimporte"}, format="json").status_code == 400


def test_no_go_verdict_blocks_generation(api, with_profile, fake_claude):
    fake_claude["responses"]["analyze_offer"] = {**ANALYSIS, "verdict": "ne_pas_postuler", "score_matching": 20}
    offer_id, _ = _create_offer(api)
    assert api.post(f"/api/offers/{offer_id}/generate-cv", {}, format="json").status_code == 409
    assert api.post(f"/api/offers/{offer_id}/generate-cv", {"force": True}, format="json").status_code == 202


def test_claude_error_then_retry(api, with_profile, fake_claude):
    fake_claude["error"] = "Limite d'usage de l'abonnement Claude atteinte."
    _, job_id = _create_offer(api)
    job = api.get(f"/api/jobs/{job_id}").data
    assert job["status"] == "error" and "Limite" in job["error"]

    fake_claude["error"] = None
    assert api.post(f"/api/jobs/{job_id}/retry").status_code == 202
    assert api.get(f"/api/jobs/{job_id}").data["status"] == "done"


def test_offer_requires_profile(api):
    assert api.post("/api/offers", {"raw_text": OFFER_TEXT}, format="json").status_code == 400


def test_audit_accept_reject_edit(api, with_profile, fake_claude):
    r = api.post("/api/audits", {"target_role": "dev back-end Python"}, format="json")
    assert r.status_code == 202
    job = api.get(f"/api/jobs/{r.data['job_id']}").data
    assert job["status"] == "done", job

    audit = api.get(f"/api/audits/{r.data['audit']['id']}").data
    by_kind = {(s["kind"], s["target_path"]): s for s in audit["suggestions"]}
    question = by_kind[("question", "experiences.0.realisations.1")]
    suggestion = by_kind[("suggestion", "experiences.0.realisations.1")]
    global_remark = next(s for s in audit["suggestions"] if s["explanation"] == "Global.")
    assert global_remark["target_path"] == ""  # chemin inexistant → remarque globale
    on_list = next(s for s in audit["suggestions"] if s["explanation"] == "Liste.")
    assert on_list["target_path"] == ""  # pas un champ texte → remarque globale
    no_rewrite = by_kind[("suggestion", "accroche")]
    assert suggestion["before"] == "Maintenance de la TMA"

    # Accepter une remarque sans réécriture ne vide pas le champ.
    r = api.patch(f"/api/suggestions/{no_rewrite['id']}", {"state": "accepted"}, format="json")
    assert r.data["applied_version"] is None and Profile.objects.count() == 1

    r = api.patch(f"/api/suggestions/{suggestion['id']}", {"state": "accepted"}, format="json")
    assert r.data["applied_version"] == 2
    assert Profile.objects.get(version=2).data["experiences"][0]["realisations"][1].startswith("Assuré")

    r = api.patch(f"/api/suggestions/{question['id']}", {"state": "edited", "after": "Traité 40 tickets TMA par mois"}, format="json")
    assert r.data["applied_version"] == 3

    r = api.patch(f"/api/suggestions/{global_remark['id']}", {"state": "rejected"}, format="json")
    assert r.data["state"] == "rejected" and r.data["applied_version"] is None
    assert Profile.objects.count() == 3


def test_audit_responses_and_revised_cv(api, with_profile, fake_claude):
    r = api.post("/api/audits", {"target_role": ""}, format="json")
    audit_id = r.data["audit"]["id"]
    question = next(s for s in api.get(f"/api/audits/{audit_id}").data["suggestions"] if s["kind"] == "question")

    # Répondre sans changer l'état de la remarque.
    r = api.patch(f"/api/suggestions/{question['id']}", {"response": " 40 tickets par mois "}, format="json")
    assert r.status_code == 200 and r.data["response"] == "40 tickets par mois" and r.data["state"] == "pending"

    r = api.post(f"/api/audits/{audit_id}/revise")
    assert r.status_code == 202
    job = api.get(f"/api/jobs/{r.data['job_id']}").data
    assert job["status"] == "done", job

    audit = api.get(f"/api/audits/{audit_id}").data
    assert audit["revision_job"]["status"] == "done"
    assert audit["revision"]["changements"] and audit["revision"]["applied_version"] is None
    # Le 40 vient de la réponse : toléré ; le 5 n'a aucune source.
    flagged = [w["message"] for w in audit["revision"]["warnings"]]
    assert any("« 5 »" in m for m in flagged) and not any("« 40 »" in m for m in flagged)
    pdf = api.get(audit["revision_pdf_url"])
    assert pdf.status_code == 200 and b"".join(pdf.streaming_content).startswith(b"%PDF")
    assert Profile.objects.count() == 1  # rien n'est appliqué sans validation

    r = api.post(f"/api/audits/{audit_id}/revision/apply")
    assert r.data["revision"]["applied_version"] == 2
    assert Profile.objects.get(version=2).data["experiences"][0]["realisations"][1] == "Traité 40 tickets de TMA par mois"


def test_import_cv_returns_draft(api, fake_claude, tmp_path):
    import docx

    path = tmp_path / "cv.docx"
    document = docx.Document()
    document.add_paragraph("Camille Martin — Développeuse back-end Python chez Exemple SAS depuis 2021")
    document.save(path)
    with path.open("rb") as f:
        r = api.post("/api/profile/import", {"file": f}, format="multipart")
    assert r.status_code == 202
    job = api.get(f"/api/jobs/{r.data['job_id']}").data
    assert job["status"] == "done", job
    assert job["result"]["profile"]["identite"]["nom_complet"] == "Camille Martin"
    assert Profile.objects.count() == 0  # rien n'est enregistré avant validation


def test_import_rejects_other_formats(api):
    from django.core.files.uploadedfile import SimpleUploadedFile

    r = api.post("/api/profile/import", {"file": SimpleUploadedFile("cv.png", b"x")}, format="multipart")
    assert r.status_code == 400
