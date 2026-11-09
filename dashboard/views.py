"""Vues du tableau de bord."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Affiche l'accueil de l'utilisateur connecté.

    Args:
        request: Requête HTTP authentifiée.

    Returns:
        La page d'accueil du tableau de bord.
    """
    return render(request, "dashboard/home.html")
