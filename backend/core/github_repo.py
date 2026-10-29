"""Lecture d'un dépôt GitHub public via l'API REST (sans dépendance externe).

Collecte de quoi décrire le projet : métadonnées, langages, README, arborescence racine
et fichiers de dépendances. Un `GITHUB_TOKEN` facultatif relève la limite de 60 appels/heure.
"""

import base64
import json
import re
import urllib.error
import urllib.request

from django.conf import settings

API = "https://api.github.com"
URL_RE = re.compile(r"^(?:https?://)?(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:[/#?].*)?$", re.IGNORECASE)

# Fichiers qui révèlent la stack, lus s'ils sont à la racine.
MANIFESTS = [
    "package.json", "requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "composer.json", "Cargo.toml",
    "go.mod", "Gemfile", "pom.xml", "build.gradle", "build.gradle.kts", "pubspec.yaml", "mix.exs",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "Makefile",
]
README_MAX = 12000
MANIFEST_MAX = 3000


class RepoError(Exception):
    """Erreur affichable telle quelle dans l'UI."""


def parse_url(url: str) -> tuple[str, str]:
    m = URL_RE.match((url or "").strip())
    if not m:
        raise RepoError("Lien GitHub invalide : attendu https://github.com/<propriétaire>/<dépôt>.")
    return m.group(1), m.group(2)


def _get(path: str, raw: bool = False):
    headers = {
        "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
        "User-Agent": "Mue",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{API}{path}", headers=headers), timeout=20) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code in (403, 429):
            raise RepoError("Limite de l'API GitHub atteinte : réessaie plus tard ou renseigne GITHUB_TOKEN dans .env.")
        raise RepoError(f"GitHub a répondu {e.code} pour {path}.")
    except urllib.error.URLError as e:
        raise RepoError(f"GitHub injoignable : {e.reason}")
    return body if raw else json.loads(body)


def _file(owner: str, repo: str, path: str, limit: int) -> str:
    data = _get(f"/repos/{owner}/{repo}/contents/{path}")
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return ""
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:limit]


def fetch(url: str) -> dict:
    """Résumé du dépôt, prêt à être passé au prompt."""
    owner, repo = parse_url(url)
    meta = _get(f"/repos/{owner}/{repo}")
    if meta is None:
        raise RepoError(f"Dépôt {owner}/{repo} introuvable : vérifie le lien et qu'il est bien public.")
    if meta.get("private"):
        raise RepoError("Ce dépôt est privé : seuls les dépôts publics peuvent être analysés.")
    owner, repo = meta["owner"]["login"], meta["name"]

    root = _get(f"/repos/{owner}/{repo}/contents/") or []
    names = {item["name"] for item in root if isinstance(item, dict)}
    readme = _get(f"/repos/{owner}/{repo}/readme", raw=True) or ""
    return {
        "url": meta["html_url"],
        "nom": meta["name"],
        "description": meta.get("description") or "",
        "site": meta.get("homepage") or "",
        "topics": meta.get("topics") or [],
        "fork": meta.get("fork", False),
        "cree_le": (meta.get("created_at") or "")[:10],
        "dernier_push": (meta.get("pushed_at") or "")[:10],
        "langages": _get(f"/repos/{owner}/{repo}/languages") or {},
        "arborescence_racine": sorted(f"{i['name']}/" if i.get("type") == "dir" else i["name"]
                                      for i in root if isinstance(i, dict)),
        "fichiers_dependances": {n: _file(owner, repo, n, MANIFEST_MAX) for n in MANIFESTS if n in names},
        "readme": readme[:README_MAX],
    }
