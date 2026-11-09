"""Transcription : adapter Voxtral (HTTP simulé avec respx) et adapter fake."""

from decimal import Decimal

import httpx
import pytest
import respx

from dreams.models import ApiCall
from dreams.services import registry
from dreams.services.adapters.fake import FAKE_DREAMS, FakeTranscriber
from dreams.services.adapters.mistral_stt import MistralTranscriber
from dreams.services.errors import ProviderError, ProviderTimeoutError
from dreams.services.ports import AudioInput, Caller

pytestmark = pytest.mark.django_db

URL = "https://api.mistral.ai/v1/audio/transcriptions"
AUDIO = AudioInput(data=b"ID3-faux-mp3", duration_s=Decimal(90))


@pytest.fixture(autouse=True)
def mistral_key(settings, mocker):
    settings.MISTRAL_API_KEY = "cle-de-test"
    mocker.patch("time.sleep")


@pytest.fixture
def transcriber():
    return MistralTranscriber(client=httpx.Client())


@respx.mock
def test_transcription_envoie_mp3_francais_et_facture_la_duree_mesuree(transcriber):
    route = respx.post(URL).respond(200, json={"text": "  Je volais.  ", "usage": {"prompt_audio_seconds": 60}})
    result = transcriber.transcribe(AUDIO, Caller())
    assert result.text == "Je volais."
    assert (result.provider, result.model) == ("mistral", "voxtral-mini-transcribe-3")
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer cle-de-test"
    body = request.content
    assert b'name="language"\r\n\r\nfr' in body
    assert b'name="model"\r\n\r\nvoxtral-mini-transcribe-3' in body
    assert b"audio/mpeg" in body
    call = ApiCall.objects.get()
    assert call.billed_units == Decimal(1)
    assert call.cost_usd == Decimal("0.003500")


@respx.mock
def test_sans_usage_la_duree_mesuree_sert_de_base(transcriber):
    respx.post(URL).respond(200, json={"text": "ok"})
    transcriber.transcribe(AUDIO, Caller())
    assert ApiCall.objects.get().billed_units == Decimal("1.5")


@respx.mock
def test_429_puis_succes(transcriber):
    respx.post(URL).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "1"}), httpx.Response(200, json={"text": "ok"})]
    )
    assert transcriber.transcribe(AUDIO, Caller()).text == "ok"
    assert list(ApiCall.objects.order_by("attempt").values_list("http_status", flat=True)) == [429, 200]


@respx.mock
def test_500_persistant_epuise_les_tentatives(transcriber, settings):
    settings.AI_MAX_ATTEMPTS = 3
    route = respx.post(URL).respond(500)
    with pytest.raises(ProviderError) as exc:
        transcriber.transcribe(AUDIO, Caller())
    assert exc.value.status == 500
    assert route.call_count == 3


@respx.mock
def test_400_jamais_rejoue(transcriber):
    route = respx.post(URL).respond(400, json={"message": "bad"})
    with pytest.raises(ProviderError):
        transcriber.transcribe(AUDIO, Caller())
    assert route.call_count == 1


@respx.mock
def test_delai_depasse_puis_succes(transcriber):
    respx.post(URL).mock(side_effect=[httpx.ReadTimeout("lent"), httpx.Response(200, json={"text": "ok"})])
    transcriber.transcribe(AUDIO, Caller())
    assert ApiCall.objects.filter(outcome="timeout").count() == 1


@respx.mock
def test_coupure_reseau_persistante(transcriber, settings):
    settings.AI_MAX_ATTEMPTS = 2
    respx.post(URL).mock(side_effect=httpx.ConnectError("dns"))
    with pytest.raises(ProviderTimeoutError):
        transcriber.transcribe(AUDIO, Caller())


@respx.mock
def test_transcription_vide_non_rejouee(transcriber):
    route = respx.post(URL).respond(200, json={"text": "   "})
    with pytest.raises(ProviderError, match="vide"):
        transcriber.transcribe(AUDIO, Caller())
    assert route.call_count == 1


@respx.mock
def test_reponse_non_json(transcriber):
    respx.post(URL).respond(200, text="<html>")
    with pytest.raises(ProviderError, match="non JSON"):
        transcriber.transcribe(AUDIO, Caller())


@respx.mock
def test_reponse_json_liste(transcriber):
    respx.post(URL).respond(200, json=["x"])
    with pytest.raises(ProviderError, match="inattendue"):
        transcriber.transcribe(AUDIO, Caller())


@respx.mock
def test_retry_after_en_date_http_ignore(transcriber):
    respx.post(URL).mock(
        side_effect=[
            httpx.Response(503, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
            httpx.Response(200, json={"text": "ok"}),
        ]
    )
    assert transcriber.transcribe(AUDIO, Caller()).text == "ok"


def test_cle_absente_erreur_non_passagere_sans_appel_reseau(settings):
    settings.MISTRAL_API_KEY = ""
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(URL)
        with pytest.raises(ProviderError, match="MISTRAL_API_KEY"):
            MistralTranscriber(client=httpx.Client()).transcribe(AUDIO, Caller())
        assert route.call_count == 0


def test_fake_deterministe_et_journalise(user):
    fake = FakeTranscriber()
    first = fake.transcribe(AUDIO, Caller(user_id=user.id))
    assert first.text in FAKE_DREAMS
    assert fake.transcribe(AUDIO, Caller()).text == first.text
    assert ApiCall.objects.filter(provider="fake", cost_usd=0).count() == 2


def test_fake_panne_simulee(settings):
    settings.AI_FAKE_FAIL_STEPS = ["stt"]
    settings.AI_MAX_ATTEMPTS = 2
    with pytest.raises(ProviderError):
        FakeTranscriber().transcribe(AUDIO, Caller())
    assert ApiCall.objects.filter(outcome="error").count() == 2


def test_fake_latence_simulee(settings, mocker):
    settings.AI_FAKE_LATENCY_MS = 250
    sleep = mocker.patch("time.sleep")
    FakeTranscriber().transcribe(AudioInput(b"x", Decimal(0)), Caller())
    sleep.assert_called_with(0.25)


def test_registry_selon_ai_mode(settings):
    settings.AI_MODE = "fake"
    assert isinstance(registry.transcriber(), FakeTranscriber)
    settings.AI_MODE = "real"
    assert isinstance(registry.transcriber(), MistralTranscriber)
