"""Adapters simulés, fabrique et dépôt — EXF-06, EXF-15, EXF-16, EXF-19, EXF-21."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import AssetKind, Dream, EmotionAnalysis, GeneratedAsset
from dreamsynth.repository import DreamRepository
from dreamsynth.services.factory import ConfigurationError, build_services
from dreamsynth.services.mistral import MistralAnalyzer, MistralTranscriber
from dreamsynth.services.mock import (
    KeywordAnalyzer,
    MockTranscriber,
    PlaceholderImageGenerator,
    classify,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("je tombais dans le vide et personne ne m'entendait", Emotion.STRESSANT),
        ("un gâteau avec toute la famille au soleil", Emotion.HEUREUX),
        ("je faisais mes courses au supermarché", Emotion.NEUTRE),
        ("une girafe jouait du piano devant des pingouins", Emotion.ETRANGE),
    ],
)
def test_keyword_classifier(text: str, expected: Emotion) -> None:
    assert classify(text)[0] is expected


def test_mock_transcriber_is_deterministic() -> None:
    stt = MockTranscriber()
    assert stt.transcribe(b"abc", "a.wav") == stt.transcribe(b"abc", "a.wav")


def test_placeholder_url_is_stable_and_prompt_dependent() -> None:
    gen = PlaceholderImageGenerator()
    a, b = gen.generate("un train"), gen.generate("un train")
    assert a.uri == b.uri and a.uri.startswith("https://picsum.photos/seed/")
    assert gen.generate("un bateau").uri != a.uri


def test_keyword_analyzer_respects_contract() -> None:
    analysis = KeywordAnalyzer().analyze("je tombais dans le vide")
    assert analysis.emotion is Emotion.STRESSANT
    assert 0 <= analysis.confidence <= 1


def test_factory_selects_adapters() -> None:
    mock = build_services(env={})
    assert isinstance(mock.transcriber, MockTranscriber)
    real = build_services(
        env={"DREAMSYNTH_TRANSCRIBER": "mistral", "DREAMSYNTH_ANALYZER": "mistral"}
    )
    assert isinstance(real.transcriber, MistralTranscriber)
    assert isinstance(real.analyzer, MistralAnalyzer)


@pytest.mark.parametrize(
    "env",
    [
        {"DREAMSYNTH_TRANSCRIBER": "inconnu"},
        {"DREAMSYNTH_ANALYZER": "inconnu"},
        {"DREAMSYNTH_IMAGE": "bfl"},
    ],
)
def test_factory_rejects_unknown_adapter(env: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError):
        build_services(env=env)


def _dream(emotion: Emotion, days_ago: int = 0) -> Dream:
    return Dream(
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
        emotion=EmotionAnalysis(emotion=emotion),
        assets=(
            GeneratedAsset(
                kind=AssetKind.IMAGE, uri=f"s3://{emotion}-{days_ago}", provider="p", model="m"
            ),
        ),
    )


def test_history_is_newest_first_and_filterable(repo: DreamRepository) -> None:  # EXF-15/16
    for days, emo in [(3, Emotion.HEUREUX), (1, Emotion.STRESSANT), (2, Emotion.HEUREUX)]:
        repo.save(_dream(emo, days))
    dates = [d.created_at for d in repo.history()]
    assert dates == sorted(dates, reverse=True)
    assert len(repo.history({Emotion.STRESSANT})) == 1


def test_delete_cascades_to_files(repo: DreamRepository) -> None:  # EXF-19
    dream = _dream(Emotion.NEUTRE)
    repo.save(dream)
    assert repo.files_of(dream.id)
    assert repo.delete(dream.id)
    assert repo.get(dream.id) is None and repo.files_of(dream.id) == []
    assert not repo.delete(dream.id)
    assert repo.audit[-1].action == "dream.delete"


def test_delete_all_keeps_only_audit(repo: DreamRepository) -> None:  # EXF-21
    for days in range(3):
        repo.save(_dream(Emotion.SEREIN, days))
    repo.delete_all()
    assert len(repo) == 0 and repo.history() == []
    assert [a.action for a in repo.audit] == ["account.delete"]


def test_monthly_emotions(repo: DreamRepository) -> None:  # EXF-17
    repo.save(_dream(Emotion.HEUREUX, 0))
    repo.save(_dream(Emotion.STRESSANT, 40))
    months = repo.monthly_emotions()
    assert len(months) == 2
    assert sum(sum(c.values()) for c in months.values()) == 2
