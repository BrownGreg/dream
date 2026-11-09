"""Pipeline : chemins nominaux et dégradés — EXF-03 à EXF-12, ENF-09."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from dreamsynth.audio import AudioUpload
from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import AssetKind, ConsentScope, DreamStatus, EmotionSource
from dreamsynth.pipeline import (
    DreamRequest,
    GenerationOptions,
    Step,
    correct_emotion,
    process_dream,
    regenerate_from_text,
)
from dreamsynth.services.mock import Failure, PlaceholderImageGenerator
from dreamsynth.services.ports import Services
from tests.conftest import ALL_CONSENTS, make_wav


def _request(options: GenerationOptions, seconds: float = 5.0) -> DreamRequest:
    return DreamRequest(AudioUpload("micro.wav", make_wav(seconds)), options)


def test_nominal_path_produces_complete_dream(
    services: Services, options: GenerationOptions
) -> None:
    steps: list[Step] = []
    result = process_dream(_request(options), services, steps.append)
    assert result.ok and result.message is None
    dream = result.dream
    assert dream.status is DreamStatus.DONE
    assert dream.transcription and dream.transcription.text
    assert dream.emotion and dream.emotion.source is EmotionSource.MODEL
    kinds = {a.kind for a in dream.assets}
    assert kinds == {AssetKind.IMAGE, AssetKind.AMBIANCE}
    assert all(a.ai_generated for a in dream.assets)
    assert steps == list(Step)


def test_no_consent_means_no_call(services: Services) -> None:  # EXF-03
    result = process_dream(_request(GenerationOptions(consents=frozenset())), services)
    assert not result.ok
    assert result.message == "Consentement requis avant tout traitement"
    assert result.dream.audio is None


def test_invalid_audio_is_not_retained(services: Services, options: GenerationOptions) -> None:
    result = process_dream(_request(options, seconds=1.0), services)
    assert result.message == "Enregistrement trop court (minimum 3 s)"
    assert not result.audio_retained and not result.retryable


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (Failure.STT_UNAVAILABLE, "Transcription indisponible, réessayez dans un instant"),
        (Failure.STT_TIMEOUT, "Le service met trop de temps à répondre"),
    ],
)
def test_stt_failure_keeps_audio_for_retry(
    failing_services: Callable[[Failure], Services],
    options: GenerationOptions,
    failure: Failure,
    message: str,
) -> None:  # EXF-10, ENF-03
    result = process_dream(_request(options), failing_services(failure))
    assert result.dream.status is DreamStatus.FAILED
    assert result.message == message
    assert result.retryable and result.audio_retained


def test_image_rejection_still_saves_dream(
    failing_services: Callable[[Failure], Services], options: GenerationOptions
) -> None:  # US-07
    result = process_dream(_request(options), failing_services(Failure.IMAGE_REJECTED))
    assert result.ok
    assert result.message == "Image non générée : le service a refusé ce contenu"
    assert AssetKind.IMAGE not in {a.kind for a in result.dream.assets}


@pytest.mark.parametrize(
    "opts",
    [
        GenerationOptions(consents=ALL_CONSENTS, image_disabled=True),
        GenerationOptions(consents=frozenset({ConsentScope.TRANSCRIPTION})),
    ],
)
def test_image_skipped_without_wish_or_consent(services: Services, opts: GenerationOptions) -> None:
    image = services.image
    assert isinstance(image, PlaceholderImageGenerator)
    result = process_dream(_request(opts), services)
    assert result.ok
    assert image.calls == 0  # EXF-11 : aucun appel au générateur
    assert result.dream.image_disabled is opts.image_disabled


def test_emotion_not_stored_without_tracking_consent(services: Services) -> None:
    opts = GenerationOptions(consents=frozenset({ConsentScope.TRANSCRIPTION}))
    assert process_dream(_request(opts), services).dream.emotion is None


def test_analyzer_receives_text_never_audio(services: Services, options: GenerationOptions) -> None:
    """ENF-09 : la signature du port n'accepte que du texte ; on vérifie l'appel effectif."""
    seen: list[object] = []
    original = services.analyzer.analyze

    def spy(text: str, style: str | None = None) -> object:
        seen.append(text)
        return original(text, style)

    object.__setattr__(services.analyzer, "analyze", spy)
    process_dream(_request(options), services)
    assert seen and all(isinstance(x, str) for x in seen)


def test_regenerate_uses_corrected_text(services: Services, options: GenerationOptions) -> None:
    first = process_dream(_request(options), services).dream
    result = regenerate_from_text(first, "un chat noir dans la neige", options, services)
    assert result.dream.transcription is not None
    assert result.dream.transcription.text == "un chat noir dans la neige"
    assert result.dream.transcription.edited_by_user
    assert result.dream.visual_prompt and "un chat noir" in result.dream.visual_prompt


def test_correct_emotion_records_user_source(
    services: Services, options: GenerationOptions
) -> None:  # US-14
    dream = process_dream(_request(options), services).dream
    corrected = correct_emotion(dream, Emotion.HEUREUX)
    assert corrected.emotion is not None
    assert corrected.emotion.emotion is Emotion.HEUREUX
    assert corrected.emotion.source is EmotionSource.USER


def test_style_is_passed_to_prompt(services: Services) -> None:  # US-19
    opts = GenerationOptions(consents=ALL_CONSENTS, style="aquarelle")
    dream = process_dream(_request(opts), services).dream
    assert dream.visual_prompt and "aquarelle" in dream.visual_prompt
