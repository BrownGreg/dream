"""Mesure et conversion audio (ffprobe / ffmpeg) sur les formats des navigateurs."""

import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from dreams import audio

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.mark.parametrize(
    ("name", "duration"),
    [("reve_court.wav", Decimal("3.00")), ("reve_court.webm", Decimal("2.01")), ("reve_court.m4a", Decimal("2.00"))],
)
def test_formats_navigateurs_mesures_et_convertis_en_mp3(name, duration):
    data = (FIXTURES / name).read_bytes()
    assert audio.probe_duration(data) == duration
    mp3 = audio.to_mp3(data)
    assert mp3[:3] == b"ID3" or mp3[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xe3")
    assert abs(audio.probe_duration(mp3) - duration) < Decimal("0.2")


def test_fichier_vide():
    with pytest.raises(audio.AudioError) as exc:
        audio.probe_duration(b"")
    assert exc.value.code == "audio_empty"


def test_fichier_corrompu():
    data = (FIXTURES / "corrompu.webm").read_bytes()
    with pytest.raises(audio.AudioError) as exc:
        audio.probe_duration(data)
    assert exc.value.code == "audio_invalid"
    with pytest.raises(audio.AudioError):
        audio.to_mp3(data)


def test_ffmpeg_absent(mocker):
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(audio.AudioError) as exc:
        audio.to_mp3(b"x")
    assert exc.value.code == "audio_tool_missing"


def test_ffmpeg_trop_long(mocker):
    mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 60))
    with pytest.raises(audio.AudioError, match="pas pu être lu"):
        audio.to_mp3(b"x")


def test_duree_absente(mocker):
    mocker.patch.object(audio, "_run", return_value=b'{"format": {}}')
    with pytest.raises(audio.AudioError, match="durée"):
        audio.probe_duration(b"x")


def test_conversion_vide(mocker):
    mocker.patch.object(audio, "_run", return_value=b"")
    with pytest.raises(audio.AudioError, match="conversion"):
        audio.to_mp3(b"x")
