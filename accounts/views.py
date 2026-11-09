"""Vues d'inscription et de connexion."""

from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import EmailAuthenticationForm, SignupForm
from accounts.services import register_user


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
