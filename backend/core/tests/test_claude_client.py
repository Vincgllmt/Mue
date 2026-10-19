import json

import pytest

from core import claude_client
from core.claude_client import ClaudeError, extract_json, render_prompt
from core.schemas import OfferAnalysis

from .fixtures import ANALYSIS


class TestExtractJson:
    def test_plain(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_fenced(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_fence_without_language(self):
        assert extract_json('```\n{"a": [1, 2]}\n```') == {"a": [1, 2]}

    def test_text_around(self):
        assert extract_json('Voici le résultat :\n{"a": {"b": "c"}}\nBonne chance !') == {"a": {"b": "c"}}

    def test_invalid(self):
        with pytest.raises(ValueError):
            extract_json("pas de JSON ici")


def test_render_prompt_injects_context_and_schema():
    prompt = render_prompt("analyze_offer", {"profil": {"titre": "Dév"}, "offre": "Offre {{schema}}"}, {"type": "object"})
    assert "titre: Dév" in prompt
    assert '"type": "object"' in prompt
    # Le contenu injecté n'est pas ré-interprété comme un placeholder.
    assert "Offre {{schema}}" in prompt
    assert "{{profil}}" not in prompt


def _envelope(result: str) -> dict:
    return {"type": "result", "is_error": False, "result": result, "total_cost_usd": 0.01, "duration_ms": 10}


def test_run_validates_output(monkeypatch):
    monkeypatch.setattr(claude_client, "call_claude_cli", lambda p, timeout=None: _envelope(json.dumps(ANALYSIS)))
    obj, meta = claude_client.run("analyze_offer", {"profil": {}, "offre": "x"}, OfferAnalysis)
    assert obj.verdict == "postuler"
    assert meta["attempts"] == 1


def test_run_retries_once_with_error(monkeypatch):
    prompts = []
    responses = iter([_envelope('{"verdict": "peut-être"}'), _envelope(f"```json\n{json.dumps(ANALYSIS)}\n```")])

    def fake(prompt, timeout=None):
        prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr(claude_client, "call_claude_cli", fake)
    obj, meta = claude_client.run("analyze_offer", {"profil": {}, "offre": "x"}, OfferAnalysis)
    assert obj.score_matching == 80
    assert meta["attempts"] == 2
    assert "Ta réponse précédente était invalide" in prompts[1]


def test_run_fails_after_second_invalid(monkeypatch):
    monkeypatch.setattr(claude_client, "call_claude_cli", lambda p, timeout=None: _envelope("toujours pas"))
    with pytest.raises(ClaudeError, match="invalide"):
        claude_client.run("analyze_offer", {"profil": {}, "offre": "x"}, OfferAnalysis)


@pytest.mark.parametrize(
    "output, expected",
    [
        ("Claude AI usage limit reached", "Limite d'usage"),
        ("OAuth token has expired", "Authentification"),
        ("Unexpected crash", "Erreur de la CLI"),
    ],
)
def test_classify_error(output, expected):
    assert expected in claude_client._classify_error(output)
