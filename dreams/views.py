"""Vues des rêves."""

from __future__ import annotations

import mimetypes
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh
from django_htmx.middleware import HtmxDetails

from dreams.emotions import COLORS, ICONS
from dreams.forms import DreamUploadForm
from dreams.messages import message_for
from dreams.models import Dream, GeneratedAsset
from dreams.services import budget
from dreams.services.errors import BudgetExceededError, QuotaExceededError
from dreams.tasks import process_dream


class HtmxHttpRequest(HttpRequest):
    """Requête enrichie par ``HtmxMiddleware`` (typage)."""

    htmx: HtmxDetails


STEPS = (
    (Dream.Status.TRANSCRIBING, "Transcription du récit"),
    (Dream.Status.ANALYZING, "Analyse de l'émotion"),
    (Dream.Status.GENERATING, "Création de l'image"),
)


@login_required
@require_GET
def serve_file(request: HttpRequest, path: str) -> FileResponse:
    """Sert une image ou un audio, uniquement à l'utilisateur propriétaire du rêve.

    Les chemins ont la forme ``<audio|assets>/<dream_id>/<nom>`` ; tout autre chemin,
    ou un rêve d'un autre utilisateur, donne 404 (sans révéler l'existence du fichier).

    Args:
        request: Requête authentifiée.
        path: Chemin du fichier dans le stockage.

    Returns:
        Le fichier, en cache privé.

    Raises:
        Http404: Chemin invalide, rêve d'un autre utilisateur ou fichier absent.
    """
    parts = path.split("/")
    if len(parts) != 3 or parts[0] not in ("audio", "assets") or ".." in parts:
        raise Http404
    try:
        dream_id = uuid.UUID(parts[1])
    except ValueError as exc:
        raise Http404 from exc
    if not Dream.objects.filter(id=dream_id, user_id=int(request.user.pk or 0)).exists():
        raise Http404
    try:
        handle = default_storage.open(path)
    except FileNotFoundError as exc:
        raise Http404 from exc
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    response = FileResponse(handle, content_type=content_type)
    response["Cache-Control"] = "private, max-age=86400"
    response["X-Content-Type-Options"] = "nosniff"
    if content_type == "image/svg+xml":
        # Une image SVG ne doit jamais exécuter de script, même servie depuis notre domaine.
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response


def _quota_message(user_id: int) -> str:
    """Message bloquant si le quota du jour ou le budget global est atteint, sinon chaîne vide."""
    try:
        budget.ensure_user_quota(user_id)
        budget.ensure_budget()
    except QuotaExceededError:
        return message_for("quota_exceeded")
    except BudgetExceededError:
        return message_for("budget_exceeded")
    return ""


@login_required
@require_http_methods(["GET", "POST"])
def record(request: HtmxHttpRequest) -> HttpResponse:
    """Écran d'enregistrement : micro ou import de fichier, puis mise en file du traitement.

    Args:
        request: Requête authentifiée ; en POST, formulaire multipart (formulaire classique ou ``fetch``).

    Returns:
        Le formulaire (avec erreurs le cas échéant) ou une redirection vers le suivi du rêve.
    """
    user_id = int(request.user.pk or 0)
    blocked = _quota_message(user_id)
    form = DreamUploadForm(request.POST or None, request.FILES or None)
    status = 200
    if request.method == "POST":
        if blocked:
            status = 429
        elif form.is_valid():
            upload = form.cleaned_data["audio"]
            with transaction.atomic():
                dream = Dream(
                    user_id=user_id,
                    image_disabled=form.cleaned_data["image_disabled"],
                    audio_mime=form.mime,
                    audio_duration_s=form.duration,
                    audio_size_bytes=upload.size,
                )
                dream.audio.save(upload.name or "reve", upload, save=False)
                dream.save()
                # La tâche part après la validation de la transaction : le worker voit toujours le rêve.
                transaction.on_commit(lambda: process_dream.enqueue(str(dream.id)))
            target = reverse("dreams:detail", args=[dream.id])
            return HttpResponseClientRedirect(target) if request.htmx else redirect(target)
        else:
            status = 422
    context = {
        "form": form,
        "blocked": blocked,
        "max_seconds": settings.AUDIO_MAX_SECONDS,
        "max_bytes": settings.AUDIO_MAX_BYTES,
    }
    template = "dreams/_record_form.html" if request.htmx else "dreams/record.html"
    return render(request, template, context, status=status)


def settings_value(name: str) -> int:
    """Lit un réglage entier (exposé aux gabarits pour la validation côté client)."""
    from django.conf import settings

    return int(getattr(settings, name))


def _dream_context(dream: Dream) -> dict[str, object]:
    emotion = dream.current_emotion
    image_attempt = dream.assets.filter(kind=GeneratedAsset.Kind.IMAGE).order_by("-attempt").first()
    image_message = ""
    if image_attempt and image_attempt.status != GeneratedAsset.Status.OK:
        image_message = message_for(image_attempt.rejection_reason)
    order: list[str] = [str(step) for step, _ in STEPS]
    current = order.index(dream.status) if dream.status in order else (-1 if not dream.is_finished else len(order))
    return {
        "dream": dream,
        "transcription": getattr(dream, "transcription", None),
        "emotion": emotion,
        "emotion_icon": ICONS.get(emotion.emotion, "") if emotion else "",
        "emotion_color": COLORS.get(emotion.emotion, "") if emotion else "",
        "image": dream.current_image,
        "image_message": image_message,
        "error_message": message_for(dream.error_code) if dream.error_code else "",
        "steps": [
            {"label": label, "state": "done" if i < current else "current" if i == current else "todo"}
            for i, (_, label) in enumerate(STEPS)
        ],
    }


@login_required
@require_GET
def detail(request: HttpRequest, dream_id: uuid.UUID) -> HttpResponse:
    """Affiche un rêve : avancement tant qu'il est traité, résultat ensuite.

    Args:
        request: Requête authentifiée.
        dream_id: Rêve demandé (404 s'il appartient à un autre utilisateur).

    Returns:
        La page du rêve.
    """
    dream = get_object_or_404(Dream.objects.select_related("transcription"), id=dream_id, user_id=request.user.pk)
    return render(request, "dreams/detail.html", _dream_context(dream))


@login_required
@require_GET
def status(request: HttpRequest, dream_id: uuid.UUID) -> HttpResponse:
    """Fragment d'avancement interrogé toutes les 2 s par HTMX.

    Une fois le traitement terminé, demande au navigateur de recharger la page entière
    (en-tête ``HX-Refresh``), ce qui arrête le polling et affiche le résultat.

    Args:
        request: Requête authentifiée.
        dream_id: Rêve suivi.

    Returns:
        Le fragment d'avancement, ou un rafraîchissement complet si le rêve est terminé.
    """
    dream = get_object_or_404(Dream, id=dream_id, user_id=request.user.pk)
    if dream.is_finished:
        return HttpResponseClientRefresh()
    context = _dream_context(dream)
    context["waited_s"] = int((timezone.now() - dream.created_at).total_seconds())
    return render(request, "dreams/_progress.html", context)
