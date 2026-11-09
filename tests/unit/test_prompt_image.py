"""Prompt visuel (Mistral) et image (BFL FLUX.2 [klein]) — DREAM-9."""

import itertools
import json
from decimal import Decimal

import httpx
import pytest
import respx

from dreams.models import ApiCall
from dreams.services import registry
from dreams.services.adapters import bfl_image
from dreams.services.adapters.bfl_image import BflImageGenerator
from dreams.services.adapters.fake import FakeImageGenerator, FakePromptBuilder
from dreams.services.adapters.mistral_prompt import MistralPromptBuilder
from dreams.services.errors import ProviderError, ProviderTimeoutError, SafetyRejectionError
from dreams.services.ports import Caller

pytestmark = pytest.mark.django_db

CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
BFL_URL = "https://api.eu.bfl.ai/v1/flux-2-klein-4b"
POLL_URL = "https://api.eu.bfl.ai/v1/get_result?id=abc"
SAMPLE_URL = "https://delivery.bfl.ai/abc/sample.jpeg?sig=x"
JPEG = b"\xff\xd8\xff\xe0fake-jpeg"
TEXT = "J'étais poursuivi par mon voisin Marc dans un couloir noir."


@pytest.fixture(autouse=True)
def keys(settings, mocker):
    settings.MISTRAL_API_KEY = "cle-de-test"
    settings.BFL_API_KEY = "bfl-test"
    mocker.patch("time.sleep")


def _chat(content: dict) -> httpx.Response:
    return httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(content)}}], "usage": {"total_tokens": 800}}
    )


@respx.mock
def test_prompt_mistral_envoie_emotion_et_recit_et_consigne_de_securite():
    route = respx.post(CHAT_URL).mock(
        return_value=_chat({"title": "Le couloir noir", "visual_prompt": "A long dim corridor, soft fog, no text."})
    )
    result = MistralPromptBuilder(client=httpx.Client()).build(TEXT, "stressant", Caller())
    assert (result.title, result.provider) == ("Le couloir noir", "mistral")
    body = json.loads(route.calls.last.request.content)
    system, user = body["messages"][0]["content"], body["messages"][1]["content"]
    for rule in ("aucun texte", "aucun nom propre", "évocateur"):
        assert rule in system
    assert "Émotion dominante : stressant" in user
    assert ApiCall.objects.get().step == "prompt"


@respx.mock
def test_prompt_adouci_apres_refus():
    route = respx.post(CHAT_URL).mock(
        return_value=_chat({"title": "Brume", "visual_prompt": "Abstract soft landscape."})
    )
    MistralPromptBuilder(client=httpx.Client()).build(TEXT, "stressant", Caller(), softer=True)
    assert "refusée par le filtre de sécurité" in json.loads(route.calls.last.request.content)["messages"][0]["content"]


def _bfl(*poll_responses, cost=1.2):
    respx.post(BFL_URL).respond(200, json={"id": "abc", "polling_url": POLL_URL, "cost": cost})
    respx.get(POLL_URL).mock(side_effect=list(poll_responses))
    return respx.get(SAMPLE_URL).respond(200, content=JPEG)


@respx.mock
def test_image_bfl_polling_puis_telechargement_et_cout_mesure():
    download = _bfl(
        httpx.Response(200, json={"status": "Pending"}),
        httpx.Response(200, json={"status": "Generating"}),
        httpx.Response(200, json={"status": "Ready", "result": {"sample": SAMPLE_URL}}),
    )
    image = BflImageGenerator(client=httpx.Client()).generate("A soft corridor", Caller())
    assert image.data == JPEG
    assert (image.extension, image.provider, image.model) == ("jpg", "bfl", "flux-2-klein-4b")
    assert download.called
    submit = respx.calls[0].request
    assert submit.headers["x-key"] == "bfl-test"
    assert json.loads(submit.content) == {
        "prompt": "A soft corridor",
        "width": 1024,
        "height": 1024,
        "output_format": "jpeg",
        "safety_tolerance": 2,
    }
    call = ApiCall.objects.get()
    assert (call.unit, call.billed_units, call.cost_usd) == ("credit", Decimal("1.2"), Decimal("0.012000"))


@respx.mock
def test_image_sans_cout_dans_la_reponse_utilise_l_estimation():
    _bfl(httpx.Response(200, json={"status": "Ready", "result": {"sample": SAMPLE_URL}}), cost=None)
    BflImageGenerator(client=httpx.Client()).generate("p", Caller())
    assert ApiCall.objects.get().billed_units == Decimal("1.4")


@pytest.mark.parametrize("status", ["Request Moderated", "Content Moderated"])
@respx.mock
def test_moderation_donne_un_refus_de_securite_non_rejoue(status):
    _bfl(httpx.Response(200, json={"status": status}))
    with pytest.raises(SafetyRejectionError):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())
    assert respx.routes[0].call_count == 1
    assert ApiCall.objects.get().outcome == "rejected"


@respx.mock
def test_echec_fournisseur_rejoue_une_fois():
    _bfl(
        httpx.Response(200, json={"status": "Error"}),
        httpx.Response(200, json={"status": "Ready", "result": {"sample": SAMPLE_URL}}),
    )
    BflImageGenerator(client=httpx.Client()).generate("p", Caller())
    assert respx.routes[0].call_count == 2


@respx.mock
def test_pret_sans_url():
    _bfl(httpx.Response(200, json={"status": "Ready", "result": {}}))
    with pytest.raises(ProviderError, match="sans URL"):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())


@respx.mock
def test_reponse_sans_polling_url():
    respx.post(BFL_URL).respond(200, json={"id": "abc"})
    with pytest.raises(ProviderError, match="polling_url"):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())


@respx.mock
def test_image_jamais_prete(mocker):
    clock = itertools.count(0.0, 20.0)  # chaque lecture de l'horloge avance de 20 s
    mocker.patch.object(bfl_image.time, "monotonic", side_effect=lambda: next(clock))
    respx.post(BFL_URL).respond(200, json={"id": "abc", "polling_url": POLL_URL, "cost": 1})
    respx.get(POLL_URL).respond(200, json={"status": "Pending"})
    with pytest.raises(ProviderTimeoutError):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())
    assert ApiCall.objects.filter(outcome="timeout").count() == 2  # max_attempts=2 pour l'image


@respx.mock
def test_image_telechargee_vide():
    respx.post(BFL_URL).respond(200, json={"id": "abc", "polling_url": POLL_URL, "cost": 1})
    respx.get(POLL_URL).respond(200, json={"status": "Ready", "result": {"sample": SAMPLE_URL}})
    respx.get(SAMPLE_URL).respond(200, content=b"")
    with pytest.raises(ProviderError, match="vide"):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())


@respx.mock
def test_402_credits_epuises_non_rejoue():
    route = respx.post(BFL_URL).respond(402)
    with pytest.raises(ProviderError):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())
    assert route.call_count == 1


def test_bfl_sans_cle(settings):
    settings.BFL_API_KEY = ""
    with pytest.raises(ProviderError, match="BFL_API_KEY"):
        BflImageGenerator(client=httpx.Client()).generate("p", Caller())


def test_fakes_et_registry(settings):
    prompt = FakePromptBuilder().build("Je volais au-dessus de la mer calme.", "serein", Caller())
    assert prompt.title == "Au-dessus de la mer calme"
    assert "serein" in prompt.prompt
    assert "abstract" in FakePromptBuilder().build("x", "stressant", Caller(), softer=True).prompt
    image = FakeImageGenerator().generate(prompt.prompt, Caller())
    assert image.extension == "svg"
    assert image.data.startswith(b"<svg")
    assert b"<script" not in image.data
    assert FakeImageGenerator().generate(prompt.prompt, Caller()).data == image.data
    settings.AI_MODE = "real"
    assert isinstance(registry.prompt_builder(), MistralPromptBuilder)
    assert isinstance(registry.image_generator(), BflImageGenerator)
    settings.AI_MODE = "fake"
    assert isinstance(registry.image_generator(), FakeImageGenerator)
