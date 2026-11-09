"""Validation audio — EXF-01, EXF-02 (US-01, US-02)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dreamsynth.audio import MAX_BYTES, AudioUpload, sniff_format, validate_audio
from dreamsynth.errors import DreamError, ErrorCode
from tests.conftest import make_wav


def test_accepts_valid_wav(wav: Callable[[float], bytes]) -> None:
    meta = validate_audio(AudioUpload("micro.wav", wav(4.0)))
    assert meta.mime_type == "audio/wav"
    assert meta.duration_s == pytest.approx(4.0, abs=0.01)


def test_accepts_real_mp3(mp3_bytes: bytes) -> None:
    meta = validate_audio(AudioUpload("reve.mp3", mp3_bytes))
    assert meta.mime_type == "audio/mpeg"
    assert 29 < meta.duration_s < 40


@pytest.mark.parametrize(
    ("filename", "data", "code"),
    [
        ("reve.ogg", b"OggS" + b"\0" * 100, ErrorCode.AUDIO_UNSUPPORTED),
        ("reve.mp3", b"ceci n'est pas un mp3", ErrorCode.AUDIO_UNSUPPORTED),
        ("reve.wav", b"ID3" + b"\0" * 100, ErrorCode.AUDIO_UNSUPPORTED),  # extension ≠ contenu
        ("reve.wav", b"\0" * (MAX_BYTES + 1), ErrorCode.AUDIO_TOO_LARGE),
        ("reve.wav", b"RIFF\0\0\0\0WAVEcorrompu", ErrorCode.AUDIO_INVALID),
    ],
)
def test_rejects_invalid_files(filename: str, data: bytes, code: ErrorCode) -> None:
    with pytest.raises(DreamError) as exc:
        validate_audio(AudioUpload(filename, data))
    assert exc.value.code is code
    assert exc.value.user_message


def test_size_checked_before_format() -> None:
    with pytest.raises(DreamError) as exc:
        validate_audio(AudioUpload("reve.ogg", b"\0" * (MAX_BYTES + 1)))
    assert exc.value.code is ErrorCode.AUDIO_TOO_LARGE


def test_too_short_and_too_long() -> None:
    with pytest.raises(DreamError) as short:
        validate_audio(AudioUpload("a.wav", make_wav(1.0)))
    assert short.value.user_message == "Enregistrement trop court (minimum 3 s)"
    with pytest.raises(DreamError) as long:
        validate_audio(AudioUpload("a.wav", make_wav(301.0, rate=1000)))
    assert long.value.code is ErrorCode.AUDIO_TOO_LONG


@settings(max_examples=25, deadline=None)
@given(seconds=st.floats(min_value=0.2, max_value=12.0))
def test_duration_rule_holds_for_any_length(seconds: float) -> None:
    """Propriété : accepté si et seulement si la durée est ≥ 3 s."""
    upload = AudioUpload("a.wav", make_wav(seconds, rate=1000))
    if seconds >= 3.0:
        assert validate_audio(upload).duration_s >= 3.0
    else:
        with pytest.raises(DreamError):
            validate_audio(upload)


def test_sniff_format() -> None:
    assert sniff_format(make_wav(0.1)) == "wav"
    assert sniff_format(b"ID3\x04") == "mp3"
    assert sniff_format(b"\xff\xfb\x90") == "mp3"
    assert sniff_format(b"OggS") is None
