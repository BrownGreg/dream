"""Validation d'un audio reçu : taille, format réel (signature d'octets) et durée (EXF-02).

L'ordre des contrôles est délibéré : taille d'abord (refus sans lecture du contenu), puis
format, puis durée (seul contrôle qui décode le fichier).
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from pathlib import PurePath

from mutagen.mp3 import MP3, HeaderNotFoundError

from dreamsynth.domain.models import AudioMeta
from dreamsynth.errors import DreamError, ErrorCode

MAX_BYTES = 20 * 1024 * 1024
MIN_SECONDS = 3.0
MAX_SECONDS = 300.0
ALLOWED_EXTENSIONS = {".wav", ".mp3"}


@dataclass(frozen=True)
class AudioUpload:
    """Audio tel que reçu de l'UI (micro ou fichier)."""

    filename: str
    data: bytes


def sniff_format(data: bytes) -> str | None:
    """Reconnaît WAV ou MP3 par leurs premiers octets ; None si autre chose."""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:3] == b"ID3" or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "mp3"
    return None


def _duration(data: bytes, fmt: str) -> float:
    try:
        if fmt == "wav":
            with wave.open(io.BytesIO(data)) as wav:
                frames: int = wav.getnframes()
                rate: int = wav.getframerate()
                return frames / float(rate)
        info = MP3(io.BytesIO(data)).info  # type: ignore[no-untyped-call]
        length = getattr(info, "length", None)
        if not isinstance(length, int | float):
            raise DreamError(ErrorCode.AUDIO_INVALID, "durée MP3 illisible")
        return float(length)
    except (wave.Error, EOFError, HeaderNotFoundError, ZeroDivisionError) as exc:
        raise DreamError(ErrorCode.AUDIO_INVALID, str(exc)) from exc


def validate_audio(upload: AudioUpload) -> AudioMeta:
    """Valide un audio et retourne ses métadonnées.

    Args:
        upload: nom de fichier et contenu brut.

    Returns:
        Métadonnées de l'audio accepté.

    Raises:
        DreamError: code `audio_*` décrivant le premier contrôle en échec.
    """
    if len(upload.data) > MAX_BYTES:
        raise DreamError(ErrorCode.AUDIO_TOO_LARGE)
    extension = PurePath(upload.filename).suffix.lower()
    fmt = sniff_format(upload.data)
    if extension not in ALLOWED_EXTENSIONS or fmt is None or f".{fmt}" != extension:
        raise DreamError(ErrorCode.AUDIO_UNSUPPORTED)
    duration = _duration(upload.data, fmt)
    if duration < MIN_SECONDS:
        raise DreamError(ErrorCode.AUDIO_TOO_SHORT)
    if duration > MAX_SECONDS:
        raise DreamError(ErrorCode.AUDIO_TOO_LONG)
    return AudioMeta(
        filename=PurePath(upload.filename).name[:255],
        mime_type="audio/wav" if fmt == "wav" else "audio/mpeg",
        duration_s=round(duration, 2),
        size_bytes=len(upload.data),
    )
