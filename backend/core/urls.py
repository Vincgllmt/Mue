from django.urls import path

from . import views

urlpatterns = [
    path("profile", views.profile),
    path("profile/import", views.profile_import),
    path("profile/versions", views.profile_versions),
    path("profile/versions/<int:version>", views.profile_version_detail),
    path("profile/versions/<int:version>/restore", views.profile_version_restore),
    path("offers", views.offers),
    path("offers/<int:pk>", views.offer_detail),
    path("offers/<int:pk>/generate-cv", views.offer_generate_cv),
    path("offers/<int:pk>/generate-letter", views.offer_generate_letter),
    path("docs/<int:pk>", views.doc_detail),
    path("docs/<int:pk>/pdf", views.doc_pdf),
    path("audits", views.audits),
    path("audits/<int:pk>", views.audit_detail),
    path("suggestions/<int:pk>", views.suggestion_detail),
    path("jobs/<int:pk>", views.job_detail),
    path("jobs/<int:pk>/retry", views.job_retry),
    path("applications/<int:pk>", views.application_detail),
]
