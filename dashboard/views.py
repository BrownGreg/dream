"""Vues du tableau de bord."""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dashboard import ops as ops_metrics
from dashboard.forms import DreamFilterForm
from dashboard.queries import user_dreams
from dashboard.stats import DEFAULT_PERIOD, MONTHS_FR, PERIODS, compute
from dreams.emotions import COLORS, ICONS, Emotion

PAGE_SIZE = 10
EXCERPT_CHARS = 140


def _excerpt(text: str) -> str:
    """Début du récit, coupé sur un mot."""
    if len(text) <= EXCERPT_CHARS:
        return text
    return text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"


def home(request: HttpRequest) -> HttpResponse:
    """Accueil : landing page pour un visiteur, historique pour un utilisateur connecté.

    Args:
        request: Requête entrante.

    Returns:
        La landing page (contenu statique, aucune donnée) ou l'historique.
    """
    if not request.user.is_authenticated:
        return render(request, "landing.html")
    return history(request)


@login_required
def history(request: HttpRequest) -> HttpResponse:
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


@login_required
def stats(request: HttpRequest) -> HttpResponse:
    """Statistiques personnelles : fréquence, répartition, émotion dominante, évolution (US-16).

    Args:
        request: Requête authentifiée ; ``?periode=30|90|365``.

    Returns:
        La page de statistiques.
    """
    period = request.GET.get("periode", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    result = compute(int(request.user.pk or 0), period)
    labels = dict(Emotion.choices)
    chart_data = {
        "weeks": {
            "labels": [f"{d.day} {MONTHS_FR[d.month - 1]}" for d, _ in result.weeks],
            "values": [n for _, n in result.weeks],
        },
        "distribution": {
            "labels": [str(labels[e]) for e, _ in result.distribution],
            "values": [n for _, n in result.distribution],
        },
        "evolution": {
            "labels": result.months,
            "series": [
                {"key": key, "label": str(labels[key]), "values": values} for key, values in result.evolution.items()
            ],
        },
    }
    context = {
        "stats": result,
        "period": period,
        "periods": [("30", "30 jours"), ("90", "3 mois"), ("365", "12 mois")],
        "dominant_label": labels.get(result.dominant, "") if result.dominant else "",
        "dominant_icon": ICONS.get(result.dominant, "") if result.dominant else "",
        "distribution_rows": [(labels[e], ICONS[e], n) for e, n in result.distribution],
        "evolution_rows": [
            (month, [result.evolution[key][i] for key, _ in Emotion.choices]) for i, month in enumerate(result.months)
        ],
        "emotion_labels": [label for _, label in Emotion.choices],
        "chart_data": chart_data,
    }
    return render(request, "dashboard/stats.html", context)


@staff_member_required(login_url="accounts:login")  # type: ignore[untyped-decorator]
def ops(request: HttpRequest) -> HttpResponse:
    """Page d'exploitation (staff) : budget, latences, erreurs, file, coût par rêve.

    Args:
        request: Requête d'un membre du staff.

    Returns:
        La page ``/ops`` ; aucun contenu de rêve n'y figure.
    """
    return render(request, "dashboard/ops.html", {"o": ops_metrics.overview()})
