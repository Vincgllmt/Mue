"""Rendu PDF déterministe : contenu JSON injecté dans un template Typst."""

import json
from pathlib import Path

import typst
from django.conf import settings

TEMPLATES = {"cv": "cv.typ", "letter": "letter.typ"}
DEFAULT_TEMPLATE = "default"


class RenderError(Exception):
    pass


def template_path(kind: str, template: str = DEFAULT_TEMPLATE) -> Path:
    path = Path(settings.TYPST_DIR) / template / TEMPLATES[kind]
    if not path.exists():
        raise RenderError(f"Template Typst introuvable : {path}")
    return path


def render(kind: str, content: dict, template: str = DEFAULT_TEMPLATE) -> bytes:
    path = template_path(kind, template)
    try:
        return typst.compile(
            str(path),
            root=str(settings.TYPST_DIR),
            sys_inputs={"data": json.dumps(content, ensure_ascii=False)},
        )
    except Exception as e:  # typst lève des erreurs de compilation génériques
        raise RenderError(f"Échec du rendu Typst : {e}") from e


def render_to_file(kind: str, content: dict, filename: str, template: str = DEFAULT_TEMPLATE) -> Path:
    out = Path(settings.PDF_DIR) / filename
    out.write_bytes(render(kind, content, template))
    return out
