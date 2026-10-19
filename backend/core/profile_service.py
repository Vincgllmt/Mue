"""Profil maître : versions en base, miroir éditable à la main dans data/profile.yaml."""

import yaml
from django.conf import settings
from django.db import transaction
from pydantic import ValidationError

from .models import Profile
from .schemas import ProfileData


class ProfileYamlError(Exception):
    pass


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120)


def write_yaml(data: dict) -> None:
    settings.PROFILE_YAML.write_text(_dump_yaml(data), encoding="utf-8")


def latest() -> Profile | None:
    return Profile.objects.order_by("-version").first()


def current_data() -> ProfileData:
    p = latest()
    return ProfileData.model_validate(p.data) if p else ProfileData()


@transaction.atomic
def save(data: dict, note: str = "") -> Profile:
    """Valide et enregistre une nouvelle version (sauf si rien n'a changé)."""
    clean = ProfileData.model_validate(data).model_dump()
    current = latest()
    if current and current.data == clean:
        return current
    version = (current.version + 1) if current else 1
    profile = Profile.objects.create(version=version, data=clean, note=note[:200])
    write_yaml(clean)
    return profile


def sync_from_yaml() -> Profile | None:
    """Si profile.yaml a été modifié à la main, l'enregistre comme nouvelle version."""
    path = settings.PROFILE_YAML
    current = latest()
    if not path.exists():
        if current:
            write_yaml(current.data)
        return current
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        clean = ProfileData.model_validate(raw).model_dump()
    except (yaml.YAMLError, ValidationError) as e:
        raise ProfileYamlError(f"profile.yaml invalide, ignoré : {e}") from e
    if current is None or current.data != clean:
        return save(clean, note="Édition manuelle de profile.yaml")
    return current


def restore(version: int) -> Profile:
    old = Profile.objects.get(version=version)
    return save(old.data, note=f"Restauration de la v{version}")


# --- Chemins « experiences.0.realisations.2 » -----------------------------------------


def _key(part: str):
    return int(part) if part.isdigit() else part


def get_path(data, path: str):
    node = data
    for part in path.split("."):
        node = node[_key(part)]
    return node


def set_path(data, path: str, value) -> None:
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        node = node[_key(part)]
    last = _key(parts[-1])
    if isinstance(node, list) and isinstance(last, int) and last == len(node):
        node.append(value)
    else:
        node[last] = value
