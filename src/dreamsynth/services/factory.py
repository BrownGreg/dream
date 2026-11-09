"""Sélection des adapters par variables d'environnement.

L'UI n'importe jamais un SDK fournisseur (CLAUDE.md).

DREAMSYNTH_TRANSCRIBER = mock | mistral
DREAMSYNTH_ANALYZER    = mock | mistral
DREAMSYNTH_IMAGE       = mock            (adapter BFL : Sprint 2, ADR-004)
DREAMSYNTH_MOCK_LATENCY = secondes de latence simulée par étape (défaut 0)
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dreamsynth.services.mistral import MistralAnalyzer, MistralTranscriber
from dreamsynth.services.mock import (
    Failure,
    KeywordAnalyzer,
    LocalAmbianceLibrary,
    MockTranscriber,
    PlaceholderImageGenerator,
)
from dreamsynth.services.ports import DreamAnalyzer, Services, Transcriber

DEFAULT_AMBIANCE_DIR = Path(__file__).resolve().parents[3] / "app" / "assets" / "ambiance"


class ConfigurationError(ValueError):
    """Valeur de variable d'environnement non reconnue."""


def build_services(
    env: Mapping[str, str] | None = None,
    failure: Failure = Failure.NONE,
    ambiance_dir: Path = DEFAULT_AMBIANCE_DIR,
) -> Services:
    """Construit les adapters demandés par l'environnement.

    Args:
        env: variables d'environnement (par défaut `os.environ`).
        failure: panne simulée sur les adapters mock (démonstration).
        ambiance_dir: dossier des boucles d'ambiance.

    Returns:
        Les services prêts à être injectés dans le pipeline.

    Raises:
        ConfigurationError: si une variable désigne un adapter inconnu.
    """
    env = os.environ if env is None else env
    latency = float(env.get("DREAMSYNTH_MOCK_LATENCY", "0") or 0)

    stt_name = env.get("DREAMSYNTH_TRANSCRIBER", "mock")
    transcriber: Transcriber
    if stt_name == "mock":
        transcriber = MockTranscriber(failure, latency)
    elif stt_name == "mistral":
        transcriber = MistralTranscriber()
    else:
        raise ConfigurationError(f"DREAMSYNTH_TRANSCRIBER inconnu : {stt_name}")

    llm_name = env.get("DREAMSYNTH_ANALYZER", "mock")
    analyzer: DreamAnalyzer
    if llm_name == "mock":
        analyzer = KeywordAnalyzer(latency)
    elif llm_name == "mistral":
        analyzer = MistralAnalyzer()
    else:
        raise ConfigurationError(f"DREAMSYNTH_ANALYZER inconnu : {llm_name}")

    image_name = env.get("DREAMSYNTH_IMAGE", "mock")
    if image_name != "mock":
        raise ConfigurationError(f"DREAMSYNTH_IMAGE inconnu ou non implémenté : {image_name}")

    return Services(
        transcriber=transcriber,
        analyzer=analyzer,
        image=PlaceholderImageGenerator(failure, latency),
        ambiance=LocalAmbianceLibrary(ambiance_dir),
    )
