from django.db import models


class Profile(models.Model):
    """Une version du profil maître. La plus récente est la version courante."""

    version = models.PositiveIntegerField(unique=True)
    data = models.JSONField()
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Profil v{self.version}"


class Offer(models.Model):
    url = models.URLField(max_length=1000, blank=True)
    raw_text = models.TextField()
    analysis = models.JSONField(null=True, blank=True)
    verdict = models.CharField(max_length=30, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        a = self.analysis or {}
        return f"{a.get('poste', 'Offre')} – {a.get('entreprise', '?')}"


class Application(models.Model):
    STATUSES = [("brouillon", "Brouillon"), ("envoyee", "Envoyée"), ("entretien", "Entretien"), ("refus", "Refus")]

    offer = models.OneToOneField(Offer, on_delete=models.CASCADE, related_name="application")
    profile_version = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="brouillon")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GeneratedDoc(models.Model):
    KINDS = [("cv", "CV"), ("letter", "Lettre"), ("letter_short", "Lettre courte")]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="docs")
    kind = models.CharField(max_length=20, choices=KINDS)
    content = models.JSONField()
    warnings = models.JSONField(default=list, blank=True)  # garde-fou anti-invention
    pdf_path = models.CharField(max_length=500, blank=True)
    template = models.CharField(max_length=50, default="default")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Audit(models.Model):
    SOURCES = [("profile", "Profil maître"), ("file", "CV importé")]

    profile_version = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    target_role = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=10, choices=SOURCES, default="profile")
    # CV révisé à partir des réponses : {"profil", "changements", "warnings", "applied_version"}
    revision = models.JSONField(null=True, blank=True)
    revision_pdf_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Suggestion(models.Model):
    STATES = [("pending", "En attente"), ("accepted", "Acceptée"), ("rejected", "Rejetée"), ("edited", "Modifiée")]
    KINDS = [("suggestion", "Suggestion"), ("question", "Question de complétion")]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="suggestions")
    kind = models.CharField(max_length=20, choices=KINDS, default="suggestion")
    axis = models.CharField(max_length=20)
    severity = models.CharField(max_length=20)
    target_path = models.CharField(max_length=200)
    before = models.TextField(blank=True)
    after = models.TextField(blank=True)
    question = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    response = models.TextField(blank=True)  # réponse libre de l'utilisateur à la remarque
    state = models.CharField(max_length=20, choices=STATES, default="pending")
    applied_version = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")


class Job(models.Model):
    STATUSES = [("pending", "En attente"), ("running", "En cours"), ("done", "Terminé"), ("error", "Erreur")]

    kind = models.CharField(max_length=30)
    status = models.CharField(max_length=10, choices=STATUSES, default="pending")
    payload = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    cost_usd = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
