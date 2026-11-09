"""Vues du tableau de bord."""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dashboard.forms import DreamFilterForm
from dashboard.queries import user_dreams
from dreams.emotions import COLORS, ICONS

PAGE_SIZE = 10
EXCERPT_CHARS = 140


def _excerpt(text: str) -> str:
    """Début du récit, coupé sur un mot."""
    if len(text) <= EXCERPT_CHARS:
        return text
    return text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Historique paginé des rêves, filtrable par dates et humeurs (US-09, US-10).

    Les filtres restent dans l'URL : la page se partage, se met en favori et survit
    au rechargement. Requête HTMX : seule la liste est renvoyée.

    Args:
        request: Requête authentifiée.

    Returns:
        La page, ou le fragment de liste pour HTMX.
    """
    form = DreamFilterForm(request.GET or None)
    filters = form.cleaned_data if form.is_valid() else {}
    page = Paginator(user_dreams(int(request.user.pk or 0), filters), PAGE_SIZE).get_page(request.GET.get("page"))
    items = []
    for dream in page.object_list:
        emotion = dream.current_emotions[0] if dream.current_emotions else None  # type: ignore[attr-defined]
        image = dream.ok_images[0] if dream.ok_images else None  # type: ignore[attr-defined]
        transcription = getattr(dream, "transcription", None)
        items.append(
            {
                "dream": dream,
                "emotion": emotion,
                "icon": ICONS.get(emotion.emotion, "") if emotion else "",
                "color": COLORS.get(emotion.emotion, "") if emotion else "",
                "image": image,
                "excerpt": _excerpt(transcription.text) if transcription else "",
            }
        )
    # Paramètres à conserver dans les liens de pagination (tout sauf « page »).
    kept = [(key, value) for key in request.GET for value in request.GET.getlist(key) if key != "page"]
    context = {
        "form": form,
        "page": page,
        "items": items,
        "query": urlencode(kept),
        "filtered": form.is_bound and form.active,
        "has_any": page.paginator.count > 0 or (form.is_bound and form.active),
    }
    template = "dashboard/_dream_list.html" if getattr(request, "htmx", False) else "dashboard/home.html"
    return render(request, template, context)
