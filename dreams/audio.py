"""Mesure et conversion des enregistrements avec ffprobe / ffmpeg.

Les navigateurs produisent du ``webm/opus`` (Chrome, Firefox) ou du ``mp4/aac`` (Safari) ;
la documentation Voxtral ne cite que WAV et MP3. Tout enregistrement est donc converti
en MP3 mono 16 kHz avant transcription : un seul format envoyé, quel que soit l'appareil.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from decimal import Decimal, InvalidOperation

FFMPEG_TIMEOUT_S = 60


class AudioError(Exception):
    """Enregistrement inexploitable ; ``code`` alimente le message affiché."""

    def __init__(self, code: str, message: str) -> None:
        """Construit l'erreur.

        Args:
            code: Code stable (``audio_invalid``, ``audio_too_long``…).
            message: Message destiné à l'utilisateur, en français.
        """
        super().__init__(message)
        self.code = code
        self.message = message


def _run(args: list[str], data: bytes) -> bytes:
    """Exécute ffmpeg / ffprobe sur ``data`` écrit dans un fichier temporaire.

    Un fichier plutôt qu'un pipe : ffprobe ne lit pas la durée d'un WAV sur l'entrée
    standard, et un MP4 dont l'index (``moov``) est en fin de fichier exige de pouvoir
    revenir en arrière. ``{input}`` dans ``args`` est remplacé par le chemin du fichier.
    """
    binary = shutil.which(args[0])
    if binary is None:
        raise AudioError("audio_tool_missing", "Le traitement audio est indisponible sur ce serveur.")
    with tempfile.NamedTemporaryFile(suffix=".audio") as source:
        source.write(data)
        source.flush()
        command = [binary, *(source.name if arg == "{input}" else arg for arg in args[1:])]
        try:
            completed = subprocess.run(  # noqa: S603 - binaire résolu, pas de shell
                command, capture_output=True, timeout=FFMPEG_TIMEOUT_S, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise AudioError("audio_invalid", "Le fichier audio n'a pas pu être lu.") from exc
    if completed.returncode != 0:
        raise AudioError("audio_invalid", "Le fichier audio est illisible ou corrompu.")
    return completed.stdout


_TIME = re.compile(r"time=(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


def _decoded_duration(data: bytes) -> Decimal:
    """Durée obtenue en décodant tout le fichier (conteneur sans durée totale).

    Les fichiers écrits en flux par MediaRecorder (webm de Chrome et Firefox) ne portent
    pas leur durée dans les métadonnées : seul un décodage complet la donne.
    """
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise AudioError("audio_tool_missing", "Le traitement audio est indisponible sur ce serveur.")
    with tempfile.NamedTemporaryFile(suffix=".audio") as source:
        source.write(data)
        source.flush()
        try:
            completed = subprocess.run(  # noqa: S603 - binaire résolu, pas de shell
                [binary, "-nostdin", "-hide_banner", "-i", source.name, "-vn", "-f", "null", "-"],
                capture_output=True,
                timeout=FFMPEG_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AudioError("audio_invalid", "Le fichier audio n'a pas pu être lu.") from exc
    matches = _TIME.findall(completed.stderr.decode(errors="replace"))
    if completed.returncode != 0 or not matches:
        raise AudioError("audio_invalid", "Impossible de mesurer la durée de l'enregistrement.")
    hours, minutes, seconds = matches[-1]
    return (Decimal(hours) * 3600 + Decimal(minutes) * 60 + Decimal(seconds)).quantize(Decimal("0.01"))


def probe_duration(data: bytes) -> Decimal:
    """Mesure la durée réelle d'un enregistrement (sans se fier au client).

    Lit d'abord la durée déclarée par le conteneur (rapide) ; si elle est absente,
    comme dans les webm de MediaRecorder, décode le fichier pour la mesurer.

    Args:
        data: Octets du fichier.

    Returns:
        Durée en secondes, arrondie au centième.

    Raises:
        AudioError: Fichier illisible ou sans durée mesurable.
    """
    if not data:
        raise AudioError("audio_empty", "Le fichier audio est vide.")
    out = _run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", "{input}"],
        data,
    )
    try:
        declared = json.loads(out).get("format", {}).get("duration")
        if declared in (None, "N/A"):
            return _decoded_duration(data)
        return Decimal(str(declared)).quantize(Decimal("0.01"))
    except (ValueError, InvalidOperation, TypeError, AttributeError) as exc:
        raise AudioError("audio_invalid", "Impossible de mesurer la durée de l'enregistrement.") from exc


def to_mp3(data: bytes) -> bytes:
    """Convertit un enregistrement en MP3 mono 16 kHz (64 kbit/s), suffisant pour la voix.

    Args:
        data: Octets du fichier source (tout format lu par ffmpeg).

    Returns:
        Octets MP3.

    Raises:
        AudioError: Conversion impossible.
    """
    mp3 = _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            "{input}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            "-f",
            "mp3",
            "pipe:1",
        ],
        data,
    )
    if not mp3:
        raise AudioError("audio_invalid", "La conversion de l'enregistrement a échoué.")
    return mp3
