import copy
import uuid
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from . import documents, profile_service
from .models import Application, Audit, GeneratedDoc, Job, Offer, Profile, Suggestion
from .pdf import RenderError
from .schemas import ProfileData
from .serializers import (
    ApplicationSerializer, AuditSerializer, DocSerializer, JobSerializer, OfferListSerializer,
    OfferSerializer, ProfileVersionSerializer, SuggestionSerializer,
)
from .tasks import enqueue, retry

ALLOWED_UPLOADS = {".pdf", ".docx"}


def _error(message: str, code=status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"detail": message}, status=code)


def _validation_message(e: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, err['loc']))} : {err['msg']}" for err in e.errors()[:5])


def _save_upload(file) -> Path | Response:
    suffix = Path(file.name).suffix.lower()
    if suffix not in ALLOWED_UPLOADS:
        return _error("Format non pris en charge : dépose un PDF ou un DOCX.")
    path = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    with path.open("wb") as out:
        for chunk in file.chunks():
            out.write(chunk)
    return path


# --- Profil -------------------------------------------------------------------------------


def _profile_payload(profile: Profile | None, yaml_error: str = "") -> dict:
    return {
        "version": profile.version if profile else None,
        "note": profile.note if profile else "",
        "created_at": profile.created_at if profile else None,
        "data": profile.data if profile else ProfileData().model_dump(),
        "yaml_error": yaml_error,
    }


@api_view(["GET", "PUT"])
def profile(request):
    if request.method == "GET":
        try:
            return Response(_profile_payload(profile_service.sync_from_yaml()))
        except profile_service.ProfileYamlError as e:
            return Response(_profile_payload(profile_service.latest(), str(e)))
    try:
        saved = profile_service.save(request.data.get("data", {}), note=request.data.get("note") or "Édition dans l'app")
    except ValidationError as e:
        return _error(_validation_message(e))
    return Response(_profile_payload(saved))


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def profile_import(request):
    file = request.FILES.get("file")
    if not file:
        return _error("Aucun fichier reçu.")
    path = _save_upload(file)
    if isinstance(path, Response):
        return path
    job = enqueue("extract_profile", {"upload_path": str(path), "filename": file.name})
    return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
def profile_versions(request):
    return Response(ProfileVersionSerializer(Profile.objects.all(), many=True).data)


@api_view(["GET"])
def profile_version_detail(request, version):
    p = get_object_or_404(Profile, version=version)
    return Response(_profile_payload(p))


@api_view(["POST"])
def profile_version_restore(request, version):
    get_object_or_404(Profile, version=version)
    return Response(_profile_payload(profile_service.restore(version)))


# --- Offres -------------------------------------------------------------------------------


@api_view(["GET", "POST"])
def offers(request):
    if request.method == "GET":
        qs = Offer.objects.select_related("application").prefetch_related("application__docs")
        return Response(OfferListSerializer(qs, many=True).data)
    raw_text = (request.data.get("raw_text") or "").strip()
    if len(raw_text) < 100:
        return _error("Colle le texte complet de l'offre (au moins 100 caractères).")
    if profile_service.latest() is None:
        return _error("Le profil maître est vide : importe un CV ou remplis ton profil d'abord.")
    offer = Offer.objects.create(raw_text=raw_text, url=(request.data.get("url") or "").strip())
    Application.objects.create(offer=offer, profile_version=profile_service.latest())
    job = enqueue("analyze_offer", {"offer_id": offer.id})
    return Response({"offer": OfferSerializer(offer).data, "job_id": job.id}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET", "DELETE"])
def offer_detail(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == "DELETE":
        offer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(OfferSerializer(offer).data)


def _check_generable(offer: Offer, force: bool) -> Response | None:
    if not offer.analysis:
        return _error("L'analyse de l'offre n'est pas terminée.", status.HTTP_409_CONFLICT)
    if offer.verdict == "ne_pas_postuler" and not force:
        return _error("Verdict « ne pas postuler » : confirme avec « Générer quand même ».", status.HTTP_409_CONFLICT)
    return None


@api_view(["POST"])
def offer_generate_cv(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if blocked := _check_generable(offer, bool(request.data.get("force"))):
        return blocked
    job = enqueue("generate_cv", {"offer_id": offer.id})
    return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
def offer_generate_letter(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if blocked := _check_generable(offer, bool(request.data.get("force"))):
        return blocked
    ton = request.data.get("ton", "neutre")
    longueur = request.data.get("longueur", "standard")
    if ton not in ("formel", "neutre", "direct") or longueur not in ("courte", "standard"):
        return _error("Paramètres invalides (ton : formel/neutre/direct, longueur : courte/standard).")
    payload = {
        "offer_id": offer.id, "ton": ton, "longueur": longueur,
        "focus": (request.data.get("focus") or "")[:1000], "short": bool(request.data.get("short")),
    }
    job = enqueue("generate_letter", payload)
    return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)


# --- Documents ------------------------------------------------------------------------------


@api_view(["GET", "PUT", "DELETE"])
def doc_detail(request, pk):
    doc = get_object_or_404(GeneratedDoc.objects.select_related("application__offer"), pk=pk)
    if request.method == "DELETE":
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method == "PUT":
        try:
            documents.update_content(doc, request.data.get("content", {}), profile_service.current_data())
        except ValidationError as e:
            return _error(_validation_message(e))
        except RenderError as e:
            return _error(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(DocSerializer(doc).data)


@api_view(["GET"])
def doc_pdf(request, pk):
    doc = get_object_or_404(GeneratedDoc.objects.select_related("application__offer"), pk=pk)
    path = Path(doc.pdf_path) if doc.pdf_path else None
    if not path or not path.exists():
        raise Http404("PDF absent")
    analysis = doc.application.offer.analysis or {}
    name = "CV" if doc.kind == "cv" else "Lettre"
    company = "".join(c for c in analysis.get("entreprise", "") if c.isalnum() or c in "-_") or str(doc.id)
    download = request.GET.get("download") == "1"
    return FileResponse(path.open("rb"), content_type="application/pdf", as_attachment=download,
                        filename=f"{name}_{company}.pdf")


# --- Audit ------------------------------------------------------------------------------------


@api_view(["GET", "POST"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def audits(request):
    if request.method == "GET":
        return Response(AuditSerializer(Audit.objects.prefetch_related("suggestions")[:20], many=True).data)
    role = (request.data.get("target_role") or "").strip()[:200]
    file = request.FILES.get("file")
    payload = {}
    if file:
        path = _save_upload(file)
        if isinstance(path, Response):
            return path
        audit = Audit.objects.create(target_role=role, source="file", profile_version=profile_service.latest())
        payload["file_path"] = str(path)
    else:
        if profile_service.latest() is None:
            return _error("Le profil maître est vide : rien à auditer.")
        audit = Audit.objects.create(target_role=role, source="profile", profile_version=profile_service.latest())
    payload["audit_id"] = audit.id
    job = enqueue("audit", payload)
    return Response({"audit": AuditSerializer(audit).data, "job_id": job.id}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
def audit_detail(request, pk):
    return Response(AuditSerializer(get_object_or_404(Audit, pk=pk)).data)


@api_view(["POST"])
def audit_revise(request, pk):
    audit = get_object_or_404(Audit, pk=pk)
    if not audit.suggestions.exists():
        return _error("L'audit n'a encore produit aucune remarque.", status.HTTP_409_CONFLICT)
    payload = {"audit_id": audit.id}
    if audit.source == "file":
        audit_job = Job.objects.filter(kind="audit", payload__audit_id=audit.id).order_by("-id").first()
        if not audit_job or not Path(audit_job.payload.get("file_path", "")).exists():
            return _error("Le fichier du CV audité est introuvable.", status.HTTP_409_CONFLICT)
        payload["file_path"] = audit_job.payload["file_path"]
    elif profile_service.latest() is None:
        return _error("Le profil maître est vide.")
    job = enqueue("revise_cv", payload)
    return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
def audit_revision_apply(request, pk):
    audit = get_object_or_404(Audit, pk=pk)
    if not audit.revision:
        return _error("Aucun CV révisé à appliquer.", status.HTTP_409_CONFLICT)
    try:
        saved = profile_service.save(audit.revision["profil"], note=f"CV révisé (audit #{audit.id})")
    except ValidationError as e:
        return _error(_validation_message(e))
    audit.revision["applied_version"] = saved.version
    audit.save()
    return Response(AuditSerializer(audit).data)


@api_view(["GET"])
def audit_revision_pdf(request, pk):
    audit = get_object_or_404(Audit, pk=pk)
    path = Path(audit.revision_pdf_path) if audit.revision_pdf_path else None
    if not path or not path.exists():
        raise Http404("PDF absent")
    return FileResponse(path.open("rb"), content_type="application/pdf",
                        as_attachment=request.GET.get("download") == "1", filename="CV_revise.pdf")


@api_view(["PATCH"])
def suggestion_detail(request, pk):
    s = get_object_or_404(Suggestion.objects.select_related("audit"), pk=pk)
    if "response" in request.data:
        s.response = (request.data.get("response") or "").strip()[:2000]
    state = request.data.get("state")
    if state is None:
        s.save()
        return Response(SuggestionSerializer(s).data)
    if state not in ("accepted", "rejected", "edited", "pending"):
        return _error("État invalide.")
    if state == "edited":
        s.after = request.data.get("after", s.after)

    # Sans réécriture, accepter revient à marquer la remarque comme traitée.
    if state in ("accepted", "edited") and s.target_path and s.after.strip() and s.audit.source == "profile":
        data = copy.deepcopy(profile_service.current_data().model_dump())
        try:
            profile_service.set_path(data, s.target_path, s.after)
            saved = profile_service.save(data, note=f"Audit #{s.audit_id} : {s.axis} ({s.target_path})")
        except (KeyError, IndexError, TypeError, ValueError):
            return _error(f"Le champ « {s.target_path} » n'existe plus dans le profil.", status.HTTP_409_CONFLICT)
        except ValidationError as e:
            return _error(_validation_message(e))
        s.applied_version = saved
    s.state = state
    s.save()
    return Response(SuggestionSerializer(s).data)


# --- Jobs et candidatures ------------------------------------------------------------------------


@api_view(["GET"])
def job_detail(request, pk):
    return Response(JobSerializer(get_object_or_404(Job, pk=pk)).data)


@api_view(["POST"])
def job_retry(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if job.status not in ("error", "done"):
        return _error("Ce job est encore en cours.", status.HTTP_409_CONFLICT)
    return Response(JobSerializer(retry(job)).data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET", "PATCH"])
def application_detail(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if request.method == "PATCH":
        serializer = ApplicationSerializer(app, data={"status": request.data.get("status")}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(ApplicationSerializer(app).data)
