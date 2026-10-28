from pathlib import Path

from rest_framework import serializers

from .documents import letter_text
from .models import Application, Audit, GeneratedDoc, Job, Offer, Profile, Suggestion


class ProfileVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["version", "note", "created_at"]


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "kind", "status", "payload", "result", "error", "duration_ms", "cost_usd", "created_at", "updated_at"]


class DocSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedDoc
        fields = ["id", "application", "kind", "content", "warnings", "template", "pdf_url", "text", "created_at", "updated_at"]

    def get_pdf_url(self, doc):
        return f"/api/docs/{doc.id}/pdf?v={int(doc.updated_at.timestamp())}" if doc.pdf_path else None

    def get_text(self, doc):
        return letter_text(doc.content) if doc.kind != "cv" else None


class ApplicationSerializer(serializers.ModelSerializer):
    docs = DocSerializer(many=True, read_only=True)
    profile_version = serializers.SlugRelatedField(slug_field="version", read_only=True)

    class Meta:
        model = Application
        fields = ["id", "status", "profile_version", "docs", "created_at", "updated_at"]
        read_only_fields = ["profile_version", "docs", "created_at", "updated_at"]


class OfferSerializer(serializers.ModelSerializer):
    application = ApplicationSerializer(read_only=True)
    analysis_job = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = ["id", "url", "raw_text", "analysis", "verdict", "score", "created_at", "application", "analysis_job"]
        read_only_fields = ["analysis", "verdict", "score", "created_at"]

    def get_analysis_job(self, offer):
        job = Job.objects.filter(kind="analyze_offer", payload__offer_id=offer.id).order_by("-id").first()
        return {"id": job.id, "status": job.status, "error": job.error} if job else None


class OfferListSerializer(OfferSerializer):
    class Meta(OfferSerializer.Meta):
        fields = ["id", "url", "analysis", "verdict", "score", "created_at", "application", "analysis_job"]


class SuggestionSerializer(serializers.ModelSerializer):
    applied_version = serializers.SlugRelatedField(slug_field="version", read_only=True)

    class Meta:
        model = Suggestion
        fields = ["id", "audit", "kind", "axis", "severity", "target_path", "before", "after", "question",
                  "explanation", "response", "state", "applied_version"]


class AuditSerializer(serializers.ModelSerializer):
    suggestions = SuggestionSerializer(many=True, read_only=True)
    profile_version = serializers.SlugRelatedField(slug_field="version", read_only=True)
    job = serializers.SerializerMethodField()
    revision_job = serializers.SerializerMethodField()
    revision_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Audit
        fields = ["id", "profile_version", "target_role", "source", "created_at", "suggestions", "job",
                  "revision", "revision_job", "revision_pdf_url"]

    @staticmethod
    def _job(kind, audit):
        job = Job.objects.filter(kind=kind, payload__audit_id=audit.id).order_by("-id").first()
        return {"id": job.id, "status": job.status, "error": job.error} if job else None

    def get_job(self, audit):
        return self._job("audit", audit)

    def get_revision_job(self, audit):
        return self._job("revise_cv", audit)

    def get_revision_pdf_url(self, audit):
        path = Path(audit.revision_pdf_path) if audit.revision_pdf_path else None
        if not path or not path.exists():
            return None
        return f"/api/audits/{audit.id}/revision/pdf?v={int(path.stat().st_mtime)}"
