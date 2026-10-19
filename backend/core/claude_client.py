"""Appels à Claude Code en mode headless (`claude -p`).

Un seul appel à la fois, sortie JSON validée par Pydantic, 1 retry correctif.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

import yaml
from django.conf import settings
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

DISALLOWED_TOOLS = "Bash,Edit,Write,WebFetch,WebSearch"

_lock = threading.Lock()


class ClaudeError(Exception):
    """Erreur affichable telle quelle dans l'UI."""


# --- Prompt ---------------------------------------------------------------------


def _yaml(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000).strip()


def render_prompt(task: str, context: dict, json_schema: dict) -> str:
    """Charge `prompts/<task>.md` et remplace {{context}} et {{schema}}.

    Les autres clés du contexte sont aussi disponibles en {{cle}}.
    """
    template = (Path(settings.PROMPTS_DIR) / f"{task}.md").read_text(encoding="utf-8")
    values = {key: _yaml(val) if not isinstance(val, str) else val for key, val in context.items()}
    values["context"] = _yaml(context)
    values["schema"] = json.dumps(json_schema, ensure_ascii=False, indent=2)
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: values.get(m.group(1), m.group(0)), template)


# --- Extraction JSON -----------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Extrait l'objet JSON d'une réponse, en tolérant ```json ... ``` et du texte autour."""
    text = text.strip()
    candidates = [text]
    candidates += [m.strip() for m in _FENCE.findall(text)]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("Aucun JSON valide dans la réponse du modèle.")


# --- Appel CLI ------------------------------------------------------------------------


def _classify_error(output: str) -> str:
    low = output.lower()
    if any(k in low for k in ("usage limit", "rate limit", "limit reached", "5-hour limit", "quota")):
        return "Limite d'usage de l'abonnement Claude atteinte. Réessaie plus tard."
    if any(k in low for k in ("oauth", "401", "unauthorized", "invalid api key", "not logged in", "/login", "authentication")):
        return "Authentification Claude refusée : token expiré ou invalide (CLAUDE_CODE_OAUTH_TOKEN dans .env)."
    return "Erreur de la CLI Claude : " + (output.strip()[:300] or "réponse vide")


def call_claude_cli(prompt: str, timeout: int | None = None) -> dict:
    """Lance `claude -p` (prompt via stdin) et renvoie l'enveloppe JSON."""
    exe = shutil.which("claude")
    if not exe:
        raise ClaudeError("CLI Claude introuvable : installe-la avec `npm install -g @anthropic-ai/claude-code`.")
    cmd = [
        exe, "-p",
        "--output-format", "json",
        "--model", settings.CLAUDE_MODEL,
        "--max-turns", "1",
        "--disallowedTools", DISALLOWED_TOOLS,
    ]
    env = os.environ.copy()
    if settings.CLAUDE_CODE_OAUTH_TOKEN:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = settings.CLAUDE_CODE_OAUTH_TOKEN
    timeout = timeout or settings.CLAUDE_TIMEOUT
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env=env,
            # Dossier vide : pas de CLAUDE.md ni de fichiers du projet chargés.
            cwd=settings.CLAUDE_SANDBOX_DIR,
        )
    except subprocess.TimeoutExpired:
        raise ClaudeError(f"Claude n'a pas répondu en {timeout} s (timeout). Relance le job.")

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise ClaudeError(_classify_error(proc.stderr + proc.stdout))
    if envelope.get("is_error") or proc.returncode != 0:
        raise ClaudeError(_classify_error(str(envelope.get("result", "")) + proc.stderr))
    return envelope


def _log(task: str, entry: dict) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = Path(settings.CLAUDE_LOG_DIR) / f"{stamp}_{task}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")


# --- Point d'entrée -------------------------------------------------------------------


def run(task: str, context: dict, schema: type[T], timeout: int | None = None) -> tuple[T, dict]:
    """Rend le prompt, appelle Claude, valide la sortie. Renvoie (objet, méta)."""
    prompt = render_prompt(task, context, schema.model_json_schema())
    meta = {"task": task, "attempts": 0, "cost_usd": 0.0, "duration_ms": 0}

    with _lock:
        for attempt in (1, 2):
            meta["attempts"] = attempt
            start = time.monotonic()
            entry: dict[str, Any] = {"task": task, "attempt": attempt, "prompt": prompt}
            try:
                raw = call_claude_cli(prompt, timeout=timeout)
            except ClaudeError as e:
                entry["error"] = str(e)
                _log(task, entry)
                raise
            elapsed = int((time.monotonic() - start) * 1000)
            meta["duration_ms"] += elapsed
            meta["cost_usd"] += float(raw.get("total_cost_usd") or 0)
            result = raw.get("result", "")
            entry.update(response=result, duration_ms=elapsed, cost_usd=raw.get("total_cost_usd"))

            try:
                data = extract_json(result)
                obj = schema.model_validate(data)
            except (ValueError, ValidationError) as e:
                entry["validation_error"] = str(e)
                _log(task, entry)
                if attempt == 2:
                    raise ClaudeError(f"Réponse de Claude invalide après correction : {str(e)[:300]}")
                prompt = (
                    f"{prompt}\n\n---\n\nTa réponse précédente était invalide :\n\n{result[:4000]}\n\n"
                    f"Erreur : {e}\n\nRenvoie UNIQUEMENT le JSON corrigé, conforme au schéma."
                )
                continue
            _log(task, entry)
            return obj, meta
    raise AssertionError("inaccessible")
