"""Domaine : émotions, modèles, schéma généré — EXF-06, EXF-09, EXF-20."""

from __future__ import annotations

import json
import subprocess
import sys

import jsonschema
import pytest
from pydantic import ValidationError

from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import AssetKind, Dream, DreamExport, GeneratedAsset
from dreamsynth.errors import MESSAGES, ErrorCode
from tests.conftest import DOCS, ROOT

SCHEMA = DOCS / "schemas" / "dream.schema.json"


def test_every_emotion_has_icon_and_color() -> None:
    for emotion in Emotion:
        assert emotion.icon
        assert emotion.color.startswith("#") and len(emotion.color) == 7


def test_generated_asset_is_always_marked_ai() -> None:  # EXF-09
    asset = GeneratedAsset(kind=AssetKind.IMAGE, uri="s3://x", provider="p", model="m")
    assert asset.ai_generated is True
    with pytest.raises(ValidationError):
        GeneratedAsset(
            kind=AssetKind.IMAGE,
            uri="s3://x",
            provider="p",
            model="m",
            ai_generated=False,  # type: ignore[arg-type]
        )


def test_dream_is_immutable() -> None:
    dream = Dream()
    with pytest.raises(ValidationError):
        dream.title = "x"  # type: ignore[misc]


def test_export_validates_against_committed_schema() -> None:  # EXF-20
    export = DreamExport(dreams=(Dream(title="Le train"),))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(json.loads(export.model_dump_json()))


def test_committed_schema_is_up_to_date() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "tools" / "export_schema.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_every_error_code_has_a_message() -> None:
    assert set(MESSAGES) == set(ErrorCode)
