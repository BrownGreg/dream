"""Formulaires d'inscription et de connexion."""

from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from accounts.models import User


class SignupForm(UserCreationForm[User]):
    """Inscription par e-mail avec consentements explicites et séparés (US-03).

    Le consentement au traitement du récit est obligatoire : sans lui, le service ne
    peut rien faire. L'envoi d'un prompt au générateur d'image reste optionnel (US-11).
    """

    consent_processing = forms.BooleanField(
        required=True,
        label=(
            "J'accepte que ma voix soit transcrite et que le texte de mes rêves soit analysé "
            "par des services d'IA hébergés dans l'Union européenne. L'audio est supprimé "
            "dès la transcription réussie."
        ),
        error_messages={"required": "Ce consentement est nécessaire pour utiliser le service."},
    )
    consent_image_generation = forms.BooleanField(
        required=False,
        label=(
            "J'accepte qu'une description reformulée de mon rêve, sans nom ni détail "
            "identifiant, soit envoyée à un générateur d'image."
        ),
    )

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Ajoute les attributs d'autocomplétion attendus par les navigateurs mobiles."""
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"autocomplete": "email", "autofocus": True})

    def clean_email(self) -> str:
        """Normalise l'e-mail en minuscules et refuse un doublon à la casse près.

        ``BaseUserManager.normalize_email`` ne met en minuscules que le domaine :
        sans ce contrôle, ``Lea@x.org`` et ``lea@x.org`` créeraient deux comptes.

        Returns:
            L'adresse normalisée.

        Raises:
            forms.ValidationError: Si un compte utilise déjà cette adresse.
        """
        email = str(self.cleaned_data["email"]).strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse.")
        return email


class EmailAuthenticationForm(AuthenticationForm):
    """Connexion par e-mail ; le champ garde le nom ``username`` attendu par Django et Axes."""

    username = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )

    def clean_username(self) -> str:
        """Normalise l'e-mail en minuscules, comme à l'inscription."""
        return str(self.cleaned_data["username"]).strip().lower()


class ImageConsentForm(forms.Form):
    """Accorder ou retirer le consentement à la génération d'image."""

    granted = forms.BooleanField(required=False, label="J'accepte la génération d'images à partir de mes rêves")


class DeleteAccountForm(forms.Form):
    """Confirmation de la suppression du compte par le mot de passe."""

    password = forms.CharField(
        label="Mot de passe", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    def __init__(self, user: User, *args: Any, **kwargs: Any) -> None:
        """Associe l'utilisateur dont on vérifie le mot de passe."""
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self) -> str:
        """Vérifie le mot de passe.

        Returns:
            Le mot de passe saisi.

        Raises:
            forms.ValidationError: Mot de passe incorrect.
        """
        password = str(self.cleaned_data["password"])
        if not self.user.check_password(password):
            raise forms.ValidationError("Mot de passe incorrect.")
        return password
