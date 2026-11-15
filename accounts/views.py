"""Vues d'inscription et de connexion."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts import gdpr
from accounts.forms import DeleteAccountForm, EmailAuthenticationForm, ImageConsentForm, SignupForm
from accounts.models import Consent, User
from accounts.services import register_user
from dreams.models import Dream


@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    """Affiche et traite le formulaire d'inscription, puis connecte l'utilisateur.

    Args:
        request: Requête HTTP.

    Returns:
        Le formulaire (GET ou erreurs) ou une redirection vers le tableau de bord.
    """
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = register_user(form)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard:home")
    return render(request, "accounts/signup.html", {"form": form})


class EmailLoginView(LoginView):
    """Connexion par e-mail ; un utilisateur déjà connecté est renvoyé au tableau de bord."""

    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101 - garanti par login_required
    return user


@login_required
@require_GET
def account(request: HttpRequest) -> HttpResponse:
    """Page « Mon compte » : consentements, export, suppression.

    Args:
        request: Requête authentifiée.

    Returns:
        La page du compte.
    """
    user = _user(request)
    context = {
        "image_consent": user.has_consent(Consent.Scope.IMAGE_GENERATION),
        "consents": user.consents.order_by("-created_at")[:10],
        "delete_form": DeleteAccountForm(user),
        "dream_count": Dream.objects.filter(user=user).count(),
    }
    return render(request, "accounts/account.html", context)


@login_required
@require_POST
def update_image_consent(request: HttpRequest) -> HttpResponse:
    """Enregistre un nouveau choix de consentement à l'image (une ligne par changement).

    Args:
        request: Requête authentifiée.

    Returns:
        Une redirection vers « Mon compte ».
    """
    user = _user(request)
    granted = ImageConsentForm(request.POST).is_valid() and "granted" in request.POST
    if granted != user.has_consent(Consent.Scope.IMAGE_GENERATION):
        Consent.objects.create(
            user=user, scope=Consent.Scope.IMAGE_GENERATION, granted=granted, text_version=settings.CONSENT_TEXT_VERSION
        )
    messages.success(request, "Génération d'images activée." if granted else "Plus aucune image ne sera générée.")
    return redirect("accounts:account")


@login_required
@require_POST
def export(request: HttpRequest) -> HttpResponse:
    """Télécharge toutes les données de l'utilisateur (US-15, RGPD art. 20).

    Args:
        request: Requête authentifiée.

    Returns:
        Une archive ZIP contenant ``donnees.json`` et les images.
    """
    payload = gdpr.export_zip(_user(request))
    response = HttpResponse(payload, content_type="application/zip")
    name = f"mes-reves-{timezone.localdate():%Y-%m-%d}.zip"
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    response["Cache-Control"] = "no-store"
    return response


@login_required
@require_POST
def delete_account(request: HttpRequest) -> HttpResponse:
    """Supprime le compte après vérification du mot de passe (US-17, RGPD art. 17).

    Args:
        request: Requête authentifiée.

    Returns:
        Une redirection vers l'accueil, ou la page du compte avec l'erreur.
    """
    user = _user(request)
    form = DeleteAccountForm(user, request.POST)
    if not form.is_valid():
        messages.error(request, "Mot de passe incorrect : le compte n'a pas été supprimé.")
        return redirect("accounts:account")
    logout(request)
    gdpr.delete_account(user)
    messages.success(request, "Votre compte et toutes vos données ont été supprimés définitivement.")
    return redirect("accounts:login")
