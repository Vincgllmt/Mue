from django.contrib import admin

from .models import Application, Audit, GeneratedDoc, Interview, Job, Offer, Profile, Suggestion

for model in (Profile, Offer, Application, GeneratedDoc, Interview, Audit, Suggestion):
    admin.site.register(model)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "duration_ms", "cost_usd", "created_at")
    list_filter = ("kind", "status")
