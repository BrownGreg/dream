"""Formulaire d'envoi d'un rêve : validation **côté serveur** de l'audio.

Le navigateur valide aussi (type, durée, taille), mais rien de ce qu'il déclare n'est cru :
le type est lu dans les octets (libmagic), la durée mesurée par ffprobe.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import magic
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from dreams import audio
from dreams.messages import message_for

# Types réels acceptés : webm/opus (Chrome, Firefox), mp4/aac (Safari), wav, mp3, ogg.
ALLOWED_MIME: frozenset[str] = frozenset(
    {
        "audio/webm", "video/webm", "audio/ogg", "audio/opus",
        "audio/mp4", "video/mp4", "audio/x-m4a", "audio/aac", "audio/x-hx-aac-adts",
        "audio/mpeg", "audio/mp3",
        "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave",
    }
)  # fmt: skip


def human_duration(seconds: int) -> str:
    """Durée lisible : « 3 minutes », « 90 secondes ».

    Args:
        seconds: Durée en secondes.

    Returns:
        Le libellé en français.
    """
    if seconds >= 60 and seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    return f"{seconds} seconde{'s' if seconds > 1 else ''}"


def human_size(size: int) -> str:
    """Taille lisible : « 20 Mo », « 512 Ko ».

    Args:
        size: Taille en octets.

    Returns:
        Le libellé en français.
    """
    if size >= 1024 * 1024:
        return f"{size // (1024 * 1024)} Mo"
    return f"{max(1, size // 1024)} Ko"


class DreamUploadForm(forms.Form):
    """Enregistrement micro ou fichier importé, plus le choix « sans image » (US-11)."""

    audio = forms.FileField(
        label="Enregistrement ou fichier audio",
        help_text="Formats .wav, .mp3, .m4a ou .webm.",
        widget=forms.ClearableFileInput(attrs={"accept": ".wav,.mp3,.m4a,.webm,audio/*"}),
    )
    image_disabled = forms.BooleanField(required=False, label="Ne pas générer d'image pour ce rêve")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Prépare les champs calculés par la validation."""
        super().__init__(*args, **kwargs)
        self.mime = ""
        self.duration = Decimal(0)

    def clean_audio(self) -> UploadedFile[bytes]:
        """Vérifie taille, type réel et durée de l'enregistrement.

        Returns:
            Le fichier validé.

        Raises:
            forms.ValidationError: Avec un code et un message compréhensible.
        """
        upload: UploadedFile[bytes] = self.cleaned_data["audio"]
        size = upload.size or 0
        if size == 0:
            raise forms.ValidationError(message_for("audio_empty"), code="audio_empty")
        if size > settings.AUDIO_MAX_BYTES:
            raise forms.ValidationError(
                f"Le fichier dépasse {human_size(settings.AUDIO_MAX_BYTES)}.", code="audio_too_large"
            )
        upload.seek(0)
        data = upload.read()
        upload.seek(0)
        self.mime = magic.from_buffer(data[:8192], mime=True)
        if self.mime not in ALLOWED_MIME:
            raise forms.ValidationError(message_for("audio_invalid"), code="audio_invalid")
        try:
            self.duration = audio.probe_duration(data)
        except audio.AudioError as exc:
            raise forms.ValidationError(exc.message, code=exc.code) from exc
        if self.duration < settings.AUDIO_MIN_SECONDS:
            raise forms.ValidationError(message_for("audio_too_short"), code="audio_too_short")
        if self.duration > settings.AUDIO_MAX_SECONDS:
            raise forms.ValidationError(
                f"L'enregistrement dépasse {human_duration(settings.AUDIO_MAX_SECONDS)} : "
                "racontez l'essentiel, en plus court.",
                code="audio_too_long",
            )
        return upload
