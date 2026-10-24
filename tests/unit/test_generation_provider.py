import json

import pytest

from app.services.generation_service import GeneratedAnswer, OpenAIProvider

VALID_OUTPUT = {
    "answer": "Example evidence summary.",
    "claims": [
        {
            "text": "Example evidence summary.",
            "source_ids": ["chunk-1"],
            "support_status": "supported",
        }
    ],
    "disclaimer": "Educational information only.",
    "needs_professional_help": True,
}


def test_provider_parses_strict_structured_output_without_network(monkeypatch):
    provider = object.__new__(OpenAIProvider)
    provider._model = "test-model"
    calls = []

    def fake_post(payload):
        calls.append(payload)
        return json.dumps(VALID_OUTPUT)

    monkeypatch.setattr(provider, "_post", fake_post)
    result = provider.generate(
        "What is this?", [{"chunk_id": "chunk-1", "content": "Synthetic evidence."}]
    )
    assert isinstance(result, GeneratedAnswer)
    assert result.claims[0].source_ids == ["chunk-1"]
    assert len(calls) == 1
    assert "Synthetic evidence." in calls[0]["messages"][1]["content"]


def test_provider_retries_malformed_output_once_only(monkeypatch):
    provider = object.__new__(OpenAIProvider)
    provider._model = "test-model"
    attempts = iter(["not-json", json.dumps(VALID_OUTPUT)])
    calls = []

    def one_retry(payload):
        calls.append(payload)
        return next(attempts)

    monkeypatch.setattr(provider, "_post", one_retry)
    assert provider.generate("Question", []).answer == VALID_OUTPUT["answer"]
    assert len(calls) == 2

    monkeypatch.setattr(provider, "_post", lambda payload: "not-json")
    with pytest.raises(ValueError, match="malformed structured output"):
        provider.generate("Question", [])


def test_structured_output_rejects_unexpected_fields():
    invalid = {**VALID_OUTPUT, "unsupported_extra": "discarded"}
    with pytest.raises(ValueError):
        GeneratedAnswer.model_validate_json(json.dumps(invalid))
