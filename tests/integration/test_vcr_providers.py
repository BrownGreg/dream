"""Réponses réelles des fournisseurs rejouées depuis des cassettes (pytest-recording).

Enregistrement (Jalon B, clés réelles, corpus synthétique du bloc 1) :
    AI_MODE=real uv run pytest tests/integration/test_vcr_providers.py --record-mode=once
Sans cassette, le test est ignoré ; en CI, aucun appel réseau n'est possible (record_mode=none).
"""

from decimal import Decimal
from pathlib import Path

import pytest

from dreams import audio
from dreams.models import ApiCall
from dreams.services.adapters.bfl_image import BflImageGenerator
from dreams.services.adapters.hf_emotion import HuggingFaceEmotionClassifier
from dreams.services.adapters.mistral_prompt import MistralPromptBuilder
from dreams.services.adapters.mistral_stt import MistralTranscriber
from dreams.services.ports import AudioInput, Caller

pytestmark = pytest.mark.django_db
CASSETTES = Path(__file__).parent.parent / "cassettes" / "test_vcr_providers"
CORPUS = Path(__file__).parents[2] / "docs" / "preprod" / "maquette" / "benchmark" / "corpus" / "audio"
TEXT = "Je flottais au-dessus d'un lac immobile au lever du jour, dans une brume rose."


@pytest.fixture(autouse=True)
def keys_or_placeholders(settings, request):
    name = request.node.name
    if not (CASSETTES / f"{name}.yaml").exists() and request.config.getoption("--record-mode") in (None, "none"):
        pytest.skip("cassette absente : à enregistrer au Jalon B avec les clés réelles")
    # Rejeu : les en-têtes sont filtrés, une valeur quelconque suffit.
    settings.MISTRAL_API_KEY = settings.MISTRAL_API_KEY or "rejeu"
    settings.BFL_API_KEY = settings.BFL_API_KEY or "rejeu"
    settings.HF_TOKEN = settings.HF_TOKEN or "rejeu"


@pytest.mark.vcr
def test_voxtral_transcrit_le_corpus_synthetique():
    data = (CORPUS / "03_neutre.mp3").read_bytes()
    result = MistralTranscriber().transcribe(AudioInput(audio.to_mp3(data), audio.probe_duration(data)), Caller())
    assert len(result.text) > 20
    call = ApiCall.objects.get()
    assert call.billed_units > 0
    assert call.cost_usd > 0


@pytest.mark.vcr
def test_hugging_face_zero_shot():
    result = HuggingFaceEmotionClassifier().classify(TEXT, Caller())
    assert 0 <= result.confidence <= 1


@pytest.mark.vcr
def test_mistral_prompt_visuel():
    result = MistralPromptBuilder().build(TEXT, "serein", Caller())
    assert result.title
    assert len(result.prompt.split()) >= 20


@pytest.mark.vcr
def test_flux_klein_image():
    image = BflImageGenerator().generate("A calm lake at dawn, pink mist, painterly, no text.", Caller())
    assert image.data[:3] == b"\xff\xd8\xff"
    assert ApiCall.objects.get().cost_usd > Decimal(0)
