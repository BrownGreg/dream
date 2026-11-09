"""Opérations métier sur les comptes."""

from django.conf import settings
from django.db import transaction

from accounts.forms import SignupForm
from accounts.models import Consent, User


@transaction.atomic
def register_user(form: SignupForm) -> User:
    """Crée le compte et enregistre les deux choix de consentement.

    Args:
        form: Formulaire d'inscription déjà validé.

    Returns:
        Le nouvel utilisateur.
    """
    user = form.save()
    version = settings.CONSENT_TEXT_VERSION
    Consent.objects.bulk_create(
        [
            Consent(user=user, scope=Consent.Scope.PROCESSING, granted=True, text_version=version),
            Consent(
                user=user,
                scope=Consent.Scope.IMAGE_GENERATION,
                granted=form.cleaned_data["consent_image_generation"],
                text_version=version,
            ),
        ]
    )
    return user
