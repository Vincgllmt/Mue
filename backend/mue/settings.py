import os
from pathlib import Path

from dotenv import load_dotenv
from huey import SqliteHuey

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
ROOT_DIR = BASE_DIR.parent  # racine du dépôt

load_dotenv(ROOT_DIR / ".env")

DATA_DIR = Path(os.environ.get("MUE_DATA_DIR", ROOT_DIR / "data"))
PDF_DIR = DATA_DIR / "pdfs"
UPLOAD_DIR = DATA_DIR / "uploads"
PROFILE_YAML = DATA_DIR / "profile.yaml"
PROMPTS_DIR = ROOT_DIR / "prompts"
TYPST_DIR = ROOT_DIR / "typst"
CLAUDE_LOG_DIR = Path(os.environ.get("MUE_LOG_DIR", ROOT_DIR / "logs" / "claude"))
CLAUDE_SANDBOX_DIR = DATA_DIR / "claude_sandbox"

for d in (DATA_DIR, PDF_DIR, UPLOAD_DIR, CLAUDE_LOG_DIR, CLAUDE_SANDBOX_DIR):
    d.mkdir(parents=True, exist_ok=True)

CLAUDE_CODE_OAUTH_TOKEN = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
CLAUDE_MODEL = os.environ.get("MUE_CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.environ.get("MUE_CLAUDE_TIMEOUT", "120"))

# Application locale et mono-utilisateur : la clé n'a pas besoin d'être secrète.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "mue-local-dev-only")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "huey.contrib.djhuey",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "mue.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mue.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "mue.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

# Un seul worker : un seul appel Claude à la fois (limites de l'abonnement).
HUEY = SqliteHuey(
    name="mue",
    filename=str(DATA_DIR / "huey.sqlite3"),
    immediate=os.environ.get("MUE_HUEY_IMMEDIATE", "0") == "1",
)
