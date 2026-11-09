"""Fixtures communes : audios synthétiques, services simulés, dépôt vide."""

from __future__ import annotations

import io
import math
import struct
import wave
from collections.abc import Callable
from pathlib import Path

import pytest

from dreamsynth.domain.models import ConsentScope
from dreamsynth.pipeline import GenerationOptions
from dreamsynth.repository import DreamRepository
from dreamsynth.services.factory import build_services
from dreamsynth.services.mock import Failure
from dreamsynth.services.ports import Services

ROOT = Path(__file__).resolve().parents[1]
CORPUS_MP3 = ROOT / "benchmark" / "corpus" / "audio" / "01_heureux.mp3"
ALL_CONSENTS = frozenset(ConsentScope)


def make_wav(seconds: float, rate: int = 8000) -> bytes:
    """WAV mono 16 bits contenant une sinusoïde de la durée demandée."""
    buffer = io.BytesIO()
    frames = int(seconds * rate)
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
                for i in range(frames)
            )
        )
    return buffer.getvalue()


@pytest.fixture
def wav() -> Callable[[float], bytes]:
    """Fabrique de WAV synthétiques."""
    return make_wav


@pytest.fixture
def mp3_bytes() -> bytes:
    """MP3 réel du corpus (≈ 34 s, généré par benchmark/make_corpus.py)."""
    return CORPUS_MP3.read_bytes()


@pytest.fixture
def services() -> Services:
    """Adapters simulés, sans latence."""
    return build_services(env={})


@pytest.fixture
def failing_services() -> Callable[[Failure], Services]:
    """Adapters simulés avec une panne donnée."""
    return lambda failure: build_services(env={}, failure=failure)


@pytest.fixture
def options() -> GenerationOptions:
    """Tous les consentements, image activée."""
    return GenerationOptions(consents=ALL_CONSENTS)


@pytest.fixture
def repo() -> DreamRepository:
    """Dépôt vide."""
    return DreamRepository()


def _not_implemented() -> dict[str, str]:
    import tomllib

    with (ROOT / "docs" / "backlog" / "stories.toml").open("rb") as fh:
        stories = tomllib.load(fh)["story"]
    return {s["id"]: f"release {s['release']}" for s in stories if not s.get("implemented", True)}


NOT_IMPLEMENTED = _not_implemented()


def pytest_bdd_apply_tag(tag: str, function: Callable[..., object]) -> bool | None:
    """Scénarios de stories non implémentées en pré-production : ignorés, et signalés."""
    if tag in NOT_IMPLEMENTED:
        reason = f"{tag} ({NOT_IMPLEMENTED[tag]}) : non implémentée en pré-production"
        marker = pytest.mark.skip(reason=reason)
        marker(function)
        return True
    return None


def pytest_configure(config: pytest.Config) -> None:
    """Déclare les étiquettes Gherkin (@US-xx, @MVP, @R2, @R3) comme marqueurs pytest."""
    import tomllib

    with (ROOT / "docs" / "backlog" / "stories.toml").open("rb") as fh:
        stories = tomllib.load(fh)["story"]
    for tag in [s["id"] for s in stories] + ["MVP", "R2", "R3"]:
        config.addinivalue_line("markers", f"{tag}: étiquette Gherkin")
