"""Droits RGPD : portabilité (art. 20) et effacement (art. 17) des données d'un utilisateur."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Any

import structlog
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from dreams.deletion import delete_dream
from dreams.models import Dream

log = structlog.get_logger(__name__)
EXPORT_VERSION = "1"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _extension(name: str | None) -> str:
    return (name or "").rsplit(".", 1)[-1] or "bin"


def export_data(user: User) -> dict[str, Any]:
    """Rassemble toutes les données d'un utilisateur dans une structure JSON.

    Args:
        user: Utilisateur concerné.

    Returns:
        Le compte, l'historique des consentements et chaque rêve avec son récit, ses
        émotions (proposées et corrigées) et ses images (chemin dans l'archive).
    """
    dreams = []
    for dream in Dream.objects.filter(user=user).select_related("transcription").prefetch_related("emotions", "assets"):
        transcription = getattr(dream, "transcription", None)
        dreams.append(
            {
                "id": str(dream.id),
                "created_at": _iso(dream.created_at),
                "status": dream.status,
                "title": dream.title,
                "image_disabled": dream.image_disabled,
                "transcription": {
                    "text": transcription.text,
                    "edited_by_user": transcription.edited_by_user,
                    "provider": transcription.provider,
                    "model": transcription.model,
                }
                if transcription
                else None,
                "emotions": [
                    {
                        "emotion": e.emotion,
                        "confidence": float(e.confidence) if e.confidence is not None else None,
                        "source": e.source,
                        "provider": e.provider,
                        "current": e.is_current,
                        "created_at": _iso(e.created_at),
                    }
                    for e in dream.emotions.all().order_by("created_at")
                ],
                "images": [
                    {
                        "attempt": a.attempt,
                        "status": a.status,
                        "visual_prompt": a.visual_prompt,
                        "ai_generated": a.ai_generated,
                        "file": f"images/{dream.id}-{a.attempt}.{_extension(a.file.name)}" if a.file else None,
                        "created_at": _iso(a.created_at),
                    }
                    for a in dream.assets.all().order_by("attempt")
                ],
            }
        )
    return {
        "format": "dreamsynth-export",
        "version": EXPORT_VERSION,
        "exported_at": _iso(timezone.now()),
        "account": {"email": user.email, "date_joined": _iso(user.date_joined)},
        "consents": [
            {"scope": c.scope, "granted": c.granted, "text_version": c.text_version, "created_at": _iso(c.created_at)}
            for c in user.consents.order_by("created_at")
        ],
        "dreams": dreams,
    }


def export_zip(user: User) -> bytes:
    """Archive ZIP : ``donnees.json`` (format ouvert) et les images générées.

    Args:
        user: Utilisateur concerné.

    Returns:
        Les octets de l'archive.
    """
    data = export_data(user)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("donnees.json", json.dumps(data, ensure_ascii=False, indent=2))
        for dream in Dream.objects.filter(user=user).prefetch_related("assets"):
            for asset in dream.assets.all():
                if asset.file:
                    with asset.file.open("rb") as handle:
                        extension = _extension(asset.file.name)
                        archive.writestr(f"images/{dream.id}-{asset.attempt}.{extension}", handle.read())
    log.info("account_exported", dreams=len(data["dreams"]))
    return buffer.getvalue()


def delete_account(user: User) -> int:
    """Supprime définitivement le compte, ses rêves et tous ses fichiers.

    Le journal ``ApiCall`` ne garde qu'un pseudonyme et des coûts, sans contenu ni lien.

    Args:
        user: Utilisateur à supprimer.

    Returns:
        Le nombre de rêves supprimés.
    """
    with transaction.atomic():
        dreams = list(Dream.objects.filter(user=user).prefetch_related("assets"))
        for dream in dreams:
            delete_dream(dream)
        user.delete()
    log.info("account_deleted", dreams=len(dreams))
    return len(dreams)
