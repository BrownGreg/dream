"""Émotion : Hugging Face zero-shot, repli Mistral JSON, repli lexique (DREAM-8)."""

import json
from decimal import Decimal

import httpx
import pytest
import respx

from dreams.models import ApiCall
from dreams.services import registry
from dreams.services.adapters.fake import FAKE_DREAMS, FakeEmotionClassifier
from dreams.services.adapters.hf_emotion import HuggingFaceEmotionClassifier
from dreams.services.adapters.lexicon import LexiconEmotionClassifier
from dreams.services.adapters.mistral_emotion import MistralEmotionClassifier
from dreams.services.emotion import FallbackEmotionClassifier
from dreams.services.errors import ProviderError
from dreams.services.ports import Caller

pytestmark = pytest.mark.django_db

HF_URL = "https://router.huggingface.co/hf-inference/models/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
TEXT = "J'étais poursuivi dans un couloir noir et j'avais très peur."


@pytest.fixture(autouse=True)
def keys(settings, mocker):
    settings.HF_TOKEN = "hf_test"
    settings.MISTRAL_API_KEY = "cle-de-test"
    mocker.patch("time.sleep")


def _chat(content: str, tokens: int = 420) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}], "usage": {"total_tokens": tokens}})


@respx.mock
def test_hf_zero_shot_etiquettes_francaises_et_mapping():
    route = respx.post(HF_URL).respond(
        200, json=[{"label": "angoissante", "score": 0.874}, {"label": "étrange", "score": 0.08}]
    )
    result = HuggingFaceEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())
    assert (result.emotion, result.confidence, result.provider) == ("stressant", Decimal("0.87"), "huggingface")
    sent = json.loads(route.calls.last.request.content)
    assert sent["inputs"] == TEXT
    assert set(sent["parameters"]["candidate_labels"]) == {
        "joyeuse",
        "paisible",
        "banale",
        "étrange",
        "triste",
        "angoissante",
    }
    assert sent["parameters"]["multi_label"] is False
    assert route.calls.last.request.headers["Authorization"] == "Bearer hf_test"
    call = ApiCall.objects.get()
    assert (call.step, call.provider, call.cost_usd) == ("emotion", "huggingface", 0)


@respx.mock
def test_hf_ancien_format_labels_scores():
    respx.post(HF_URL).respond(200, json={"labels": ["paisible", "banale"], "scores": [0.6, 0.4]})
    assert HuggingFaceEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller()).emotion == "serein"


@pytest.mark.parametrize("payload", [{"error": "x"}, [], [{"label": "inconnue", "score": 1.0}]])
@respx.mock
def test_hf_reponse_inexploitable(payload):
    respx.post(HF_URL).respond(200, json=payload)
    with pytest.raises(ProviderError):
        HuggingFaceEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())


@respx.mock
def test_hf_non_json():
    respx.post(HF_URL).respond(200, text="oops")
    with pytest.raises(ProviderError, match="non JSON"):
        HuggingFaceEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())


def test_hf_sans_jeton(settings):
    settings.HF_TOKEN = ""
    with pytest.raises(ProviderError, match="HF_TOKEN"):
        HuggingFaceEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())


@respx.mock
def test_mistral_sortie_json_validee_et_tokens_factures():
    route = respx.post(CHAT_URL).mock(return_value=_chat('{"emotion": "stressant", "confidence": 0.9}'))
    result = MistralEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())
    assert (result.emotion, result.confidence) == ("stressant", Decimal("0.90"))
    body = json.loads(route.calls.last.request.content)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["messages"][1]["content"] == TEXT
    call = ApiCall.objects.get()
    assert call.billed_units == 420
    assert call.cost_usd == Decimal("0.000063")


@respx.mock
def test_mistral_hors_schema_redemande_une_fois():
    route = respx.post(CHAT_URL).mock(
        side_effect=[
            _chat('{"emotion": "furieux", "confidence": 2}'),
            _chat('{"emotion": "serein", "confidence": 0.7}'),
        ]
    )
    assert MistralEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller()).emotion == "serein"
    assert route.call_count == 2


@respx.mock
def test_mistral_hors_schema_deux_fois_abandonne():
    route = respx.post(CHAT_URL).mock(return_value=_chat("pas du json"))
    with pytest.raises(ProviderError, match="schéma"):
        MistralEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())
    assert route.call_count == 2


@respx.mock
def test_mistral_sans_choices():
    respx.post(CHAT_URL).respond(200, json={"choices": []})
    with pytest.raises(ProviderError):
        MistralEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())


def test_mistral_sans_cle(settings):
    settings.MISTRAL_API_KEY = ""
    with pytest.raises(ProviderError, match="MISTRAL_API_KEY"):
        MistralEmotionClassifier(client=httpx.Client()).classify(TEXT, Caller())


@respx.mock
def test_chaine_hf_en_panne_bascule_sur_mistral():
    respx.post(HF_URL).respond(402)  # pas de crédit HF
    respx.post(CHAT_URL).mock(return_value=_chat('{"emotion": "stressant", "confidence": 0.8}'))
    chain = FallbackEmotionClassifier(
        [HuggingFaceEmotionClassifier(client=httpx.Client()), MistralEmotionClassifier(client=httpx.Client())]
    )
    result = chain.classify(TEXT, Caller())
    assert result.provider == "mistral"
    assert list(ApiCall.objects.order_by("id").values_list("provider", "http_status")) == [
        ("huggingface", 402),
        ("mistral", 200),
    ]


@respx.mock
def test_chaine_tout_en_panne_finit_sur_le_lexique(settings):
    settings.AI_MAX_ATTEMPTS = 1
    respx.post(HF_URL).respond(503)
    respx.post(CHAT_URL).respond(503)
    chain = FallbackEmotionClassifier(
        [HuggingFaceEmotionClassifier(client=httpx.Client()), MistralEmotionClassifier(client=httpx.Client())]
    )
    result = chain.classify(TEXT, Caller())
    assert (result.emotion, result.provider) == ("stressant", "local")


def test_chaine_budget_epuise_finit_sur_le_lexique(settings):
    settings.AI_BUDGET_EUR = 0
    chain = FallbackEmotionClassifier([MistralEmotionClassifier(client=httpx.Client())])
    assert chain.classify(TEXT, Caller()).provider == "local"
    assert ApiCall.objects.get().outcome == "blocked"


@pytest.mark.parametrize(
    ("text", "emotion"),
    list(zip(FAKE_DREAMS, ["heureux", "stressant", "serein", "etrange", "melancolique"], strict=True)),
)
def test_lexique_sur_le_corpus_synthetique(text, emotion):
    result = LexiconEmotionClassifier().classify(text, Caller())
    assert result.emotion == emotion
    assert result.confidence <= Decimal("0.50")


def test_lexique_sans_indice_donne_neutre():
    result = LexiconEmotionClassifier().classify("Je suis allé au travail.", Caller())
    assert (result.emotion, result.confidence) == ("neutre", Decimal("0.30"))


def test_lexique_ignore_accents_et_casse():
    assert LexiconEmotionClassifier().classify("ANGOISSÉ, PANIQUÉ", Caller()).emotion == "stressant"


def test_fake_et_registry(settings):
    result = FakeEmotionClassifier().classify(FAKE_DREAMS[0], Caller())
    assert (result.emotion, result.confidence, result.provider) == ("heureux", Decimal("0.80"), "fake")
    settings.AI_MODE = "fake"
    assert registry.emotion_classifier().classify(FAKE_DREAMS[2], Caller()).provider == "fake"
    settings.AI_MODE = "real"
    kinds = [type(c).__name__ for c in registry.emotion_classifier().chain]
    assert kinds == ["HuggingFaceEmotionClassifier", "MistralEmotionClassifier", "LexiconEmotionClassifier"]


def test_fake_en_panne_bascule_sur_le_lexique(settings):
    settings.AI_FAKE_FAIL_STEPS = ["emotion"]
    settings.AI_MAX_ATTEMPTS = 1
    assert registry.emotion_classifier().classify(FAKE_DREAMS[1], Caller()).provider == "local"
