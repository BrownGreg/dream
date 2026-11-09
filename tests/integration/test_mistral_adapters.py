"""Adapters Mistral contre une API simulée (respx) — EXF-04, EXF-06, ENF-03.

Aucun appel réseau : les réponses reproduisent la forme documentée des endpoints.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from dreamsynth.domain.emotion import Emotion
from dreamsynth.errors import DreamError, ErrorCode
from dreamsynth.services.mistral import MistralAnalyzer, MistralTranscriber

BASE = "https://api.mistral.ai"
VALID = {
    "title": "Le train",
    "visual_prompt": "A train under the sea, glowing fish",
    "emotion": "étrange",
    "confidence": 0.8,
}


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")


def _chat(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@respx.mock
def test_transcriber_sends_french_and_reads_text() -> None:
    route = respx.post(f"{BASE}/v1/audio/transcriptions").mock(
        return_value=httpx.Response(
            200, json={"text": " Un train sous la mer. ", "usage": {"prompt_audio_seconds": 34}}
        )
    )
    result = MistralTranscriber().transcribe(b"RIFF", "a.wav")
    assert result.text == "Un train sous la mer."
    body = route.calls.last.request.content
    assert b'name="language"' in body and b"fr" in body
    assert route.calls.last.request.headers["Authorization"] == "Bearer test-key"


@respx.mock
@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(503), ErrorCode.STT_UNAVAILABLE),
        (httpx.Response(200, json={"text": ""}), ErrorCode.STT_UNAVAILABLE),
    ],
)
def test_transcriber_errors(response: httpx.Response, code: ErrorCode) -> None:
    respx.post(f"{BASE}/v1/audio/transcriptions").mock(return_value=response)
    with pytest.raises(DreamError) as exc:
        MistralTranscriber().transcribe(b"RIFF", "a.wav")
    assert exc.value.code is code


@respx.mock
def test_transcriber_timeout_maps_to_timeout_code() -> None:
    respx.post(f"{BASE}/v1/audio/transcriptions").mock(side_effect=httpx.ReadTimeout("lent"))
    with pytest.raises(DreamError) as exc:
        MistralTranscriber().transcribe(b"RIFF", "a.wav")
    assert exc.value.code is ErrorCode.TIMEOUT and exc.value.retryable


@respx.mock
def test_transport_error_maps_to_unavailable() -> None:
    respx.post(f"{BASE}/v1/audio/transcriptions").mock(side_effect=httpx.ConnectError("dns"))
    with pytest.raises(DreamError) as exc:
        MistralTranscriber().transcribe(b"RIFF", "a.wav")
    assert exc.value.code is ErrorCode.STT_UNAVAILABLE


def test_missing_key_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY")
    with pytest.raises(DreamError):
        MistralTranscriber().transcribe(b"RIFF", "a.wav")


@respx.mock
def test_analyzer_requests_json_schema_and_validates() -> None:
    route = respx.post(f"{BASE}/v1/chat/completions").mock(return_value=_chat(json.dumps(VALID)))
    analysis = MistralAnalyzer().analyze("un train sous la mer", style="aquarelle")
    assert analysis.emotion is Emotion.ETRANGE
    sent = json.loads(route.calls.last.request.content)
    assert sent["response_format"]["type"] == "json_schema"
    assert "aquarelle" in sent["messages"][1]["content"]


@respx.mock
def test_analyzer_retries_once_on_invalid_output() -> None:
    route = respx.post(f"{BASE}/v1/chat/completions").mock(
        side_effect=[_chat('{"pas": "conforme"}'), _chat(json.dumps(VALID))]
    )
    assert MistralAnalyzer().analyze("texte").title == "Le train"
    assert route.call_count == 2


@respx.mock
def test_analyzer_fails_after_two_invalid_outputs() -> None:
    respx.post(f"{BASE}/v1/chat/completions").mock(return_value=_chat("{}"))
    with pytest.raises(DreamError) as exc:
        MistralAnalyzer().analyze("texte")
    assert exc.value.code is ErrorCode.LLM_INVALID_OUTPUT
