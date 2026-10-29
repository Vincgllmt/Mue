"""Exécution des jobs asynchrones (appelés par le worker Huey)."""

import logging
import time
from pathlib import Path

from . import claude_client, documents, github_repo, guard, pdf, profile_service
from .claude_client import ClaudeError
from .github_repo import RepoError
from .models import Application, Audit, GeneratedDoc, Job, Offer, Suggestion
from .pdf import RenderError
from .schemas import (
    AuditResult, CvAdapte, CvDocument, LetterDocument, LettreGeneree, OfferAnalysis, ProfileData, Projet,
    RevisionResult,
)
from .text_extract import UnsupportedFile, extract_text

logger = logging.getLogger(__name__)


class JobError(Exception):
    pass


def _require_profile() -> ProfileData:
    if profile_service.latest() is None:
        raise JobError("Le profil maître est vide : importe un CV ou remplis ton profil d'abord.")
    return profile_service.current_data()


def _read_cv(path: str) -> str:
    text = extract_text(Path(path))
    if len(text) < 50:
        raise JobError("Impossible de lire le texte du CV (PDF scanné ?). Essaie un DOCX ou un PDF texte.")
    return text


# --- F1. Import de CV ----------------------------------------------------------------


def run_extract_profile(job: Job):
    text = _read_cv(job.payload["upload_path"])
    profile, meta = claude_client.run("extract_profile", {"cv_texte": text}, ProfileData)
    # Brouillon : il n'est enregistré qu'après validation par l'utilisateur.
    return {"profile": profile.model_dump()}, meta


# --- F1 bis. Projet depuis un dépôt GitHub ----------------------------------------------


def run_analyze_repo(job: Job):
    depot = github_repo.fetch(job.payload["url"])
    projet, meta = claude_client.run("analyze_repo", {"depot": depot}, Projet)
    projet.url = depot["url"]
    # Brouillon : ajouté au profil seulement quand l'utilisateur enregistre.
    return {"projet": projet.model_dump()}, meta


# --- F2. Analyse d'offre ----------------------------------------------------------------


def run_analyze_offer(job: Job):
    offer = Offer.objects.get(pk=job.payload["offer_id"])
    profile = _require_profile()
    analysis, meta = claude_client.run(
        "analyze_offer", {"profil": profile.model_dump(), "offre": offer.raw_text}, OfferAnalysis
    )
    offer.analysis = analysis.model_dump()
    offer.verdict = analysis.verdict
    offer.score = analysis.score_matching
    offer.save()
    return {"offer_id": offer.id}, meta


# --- F3. CV adapté ------------------------------------------------------------------------


def _application(offer: Offer) -> Application:
    app, _ = Application.objects.get_or_create(offer=offer)
    app.profile_version = profile_service.latest()
    app.save()
    return app


def run_generate_cv(job: Job):
    offer = Offer.objects.get(pk=job.payload["offer_id"])
    profile = _require_profile()
    cv, meta = claude_client.run(
        "generate_cv",
        {"profil": profile.model_dump(), "analyse": offer.analysis or {}, "offre": offer.raw_text},
        CvAdapte,
    )
    content = CvDocument(**cv.model_dump(), identite=profile.identite)
    if offer.job_title:
        content.titre = offer.job_title
    doc = GeneratedDoc(application=_application(offer), kind="cv", content={})
    documents.update_content(doc, content.model_dump(), profile)
    return {"doc_id": doc.id, "offer_id": offer.id}, meta


# --- F4. Lettre de motivation -------------------------------------------------------------


def run_generate_letter(job: Job):
    offer = Offer.objects.get(pk=job.payload["offer_id"])
    profile = _require_profile()
    params = {
        "ton": job.payload.get("ton", "neutre"),
        "longueur": job.payload.get("longueur", "standard"),
        "focus": job.payload.get("focus", ""),
        "version_courte": bool(job.payload.get("short", False)),
    }
    lettre, meta = claude_client.run(
        "generate_letter",
        {"profil": profile.model_dump(), "analyse": offer.analysis or {}, "offre": offer.raw_text, "parametres": params},
        LettreGeneree,
    )
    app = _application(offer)
    content = LetterDocument(
        identite=profile.identite,
        destinataire=(offer.analysis or {}).get("entreprise", ""),
        lieu_date=documents.lieu_date(profile),
        objet=lettre.objet,
        salutation=lettre.salutation,
        paragraphes=lettre.paragraphes,
        formule_politesse=lettre.formule_politesse,
    )
    doc = documents.update_content(GeneratedDoc(application=app, kind="letter", content={}), content.model_dump(), profile)
    result = {"doc_id": doc.id, "offer_id": offer.id}
    if params["version_courte"] and lettre.version_courte:
        short = GeneratedDoc(application=app, kind="letter_short", content={})
        documents.update_content(short, {"texte": lettre.version_courte}, profile)
        result["short_doc_id"] = short.id
    return result, meta


# --- F5. Audit -----------------------------------------------------------------------------


def _resolvable(data: dict, path: str) -> bool:
    """Seuls les champs texte existants sont applicables ; le reste devient une remarque globale."""
    if not path:
        return False
    try:
        return isinstance(profile_service.get_path(data, path), str)
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def run_audit(job: Job):
    audit = Audit.objects.get(pk=job.payload["audit_id"])
    role = audit.target_role or "Aucun poste cible précisé : ignore l'axe ciblage."
    if audit.source == "file":
        context = {"source": "cv_importe", "contenu": _read_cv(job.payload["file_path"]), "poste_cible": role}
        data = None
    else:
        data = _require_profile().model_dump()
        context = {"source": "profil", "contenu": data, "poste_cible": role}
    result, meta = claude_client.run("audit_cv", context, AuditResult)

    for q in result.questions:
        path = q.cible if data is not None and _resolvable(data, q.cible) else ""
        Suggestion.objects.create(
            audit=audit, kind="question", axis="impact", severity="important", target_path=path,
            before=profile_service.get_path(data, path) if path else q.avant,
            after=profile_service.get_path(data, path) if path else q.avant,
            question=q.question,
        )
    for s in result.suggestions:
        path = s.cible if data is not None and _resolvable(data, s.cible) else ""
        current = profile_service.get_path(data, path) if path else s.avant
        Suggestion.objects.create(
            audit=audit, axis=s.axe, severity=s.gravite, target_path=path,
            before=current if isinstance(current, str) else s.avant,
            after=s.apres, explanation=s.explication,
        )
    return {"audit_id": audit.id}, meta


# --- F5 bis. CV révisé avec les réponses à l'audit ---------------------------------------------

DECISIONS = {"pending": "en_attente", "accepted": "acceptee", "edited": "acceptee", "rejected": "rejetee"}


def _remark(s: Suggestion, source: str) -> dict:
    decision = DECISIONS[s.state]
    if source == "profile" and s.applied_version_id:
        decision = "deja_appliquee"
    return {
        "type": s.kind,
        "axe": s.axis,
        "cible": s.target_path,
        "texte_concerne": s.before,
        "proposition": s.after if s.kind == "suggestion" else "",
        "remarque": s.question if s.kind == "question" else s.explanation,
        "decision": decision,
        "reponse": s.response,
    }


def run_revise_cv(job: Job):
    audit = Audit.objects.get(pk=job.payload["audit_id"])
    remarks = [_remark(s, audit.source) for s in audit.suggestions.order_by("id")]
    answers = "\n".join(s.response for s in audit.suggestions.all() if s.response)
    if audit.source == "file":
        source_text = _read_cv(job.payload["file_path"])
        context = {"source": "cv_importe", "contenu": source_text}
    else:
        reference = _require_profile()
        context = {"source": "profil", "contenu": reference.model_dump()}
    context |= {"poste_cible": audit.target_role or "Aucun poste cible précisé.", "remarques": remarks}

    result, meta = claude_client.run("revise_cv", context, RevisionResult)
    cv = documents.profile_to_cv(result.profil)
    if audit.source == "file":
        warnings = guard.check_against_text(result.profil, f"{source_text}\n{answers}")
    else:
        warnings = guard.check_cv(cv, reference, extra_text=answers)

    path = pdf.render_to_file("cv", cv.model_dump(), f"audit_{audit.id}_revise.pdf")
    audit.revision = {
        "profil": result.profil.model_dump(),
        "changements": result.changements,
        "warnings": warnings,
        "applied_version": None,
    }
    audit.revision_pdf_path = str(path)
    audit.save()
    return {"audit_id": audit.id}, meta


RUNNERS = {
    "extract_profile": run_extract_profile,
    "analyze_repo": run_analyze_repo,
    "analyze_offer": run_analyze_offer,
    "generate_cv": run_generate_cv,
    "generate_letter": run_generate_letter,
    "audit": run_audit,
    "revise_cv": run_revise_cv,
}

EXPECTED_ERRORS = (ClaudeError, JobError, RenderError, RepoError, UnsupportedFile)


def execute(job_id: int) -> Job:
    job = Job.objects.get(pk=job_id)
    job.status, job.error = "running", ""
    job.save()
    start = time.monotonic()
    try:
        result, meta = RUNNERS[job.kind](job)
        job.status, job.result = "done", result
        job.cost_usd = meta.get("cost_usd")
    except EXPECTED_ERRORS as e:
        job.status, job.error = "error", str(e)
    except Exception as e:
        logger.exception("Job %s (%s) en échec", job.id, job.kind)
        job.status, job.error = "error", f"Erreur interne : {e}"
    job.duration_ms = int((time.monotonic() - start) * 1000)
    job.save()
    return job
