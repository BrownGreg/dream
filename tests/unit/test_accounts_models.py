"""Modèle utilisateur et consentements (US-03)."""

import pytest

from accounts.models import Consent, User

pytestmark = pytest.mark.django_db


def test_create_user_normalise_l_email_et_hache_le_mot_de_passe():
    user = User.objects.create_user("Ines@Example.ORG", "secret-assez-long")
    assert user.email == "ines@example.org"
    assert user.password != "secret-assez-long"
    assert user.check_password("secret-assez-long")
    assert not user.is_staff
    assert str(user) == "ines@example.org"


def test_create_user_sans_email_echoue():
    with pytest.raises(ValueError, match="obligatoire"):
        User.objects.create_user("", "x")


def test_create_superuser_a_les_droits_staff():
    admin = User.objects.create_superuser("ops@example.org", "secret-assez-long")
    assert admin.is_staff
    assert admin.is_superuser


def test_le_dernier_choix_de_consentement_l_emporte(user):
    assert user.has_consent(Consent.Scope.IMAGE_GENERATION)
    Consent.objects.create(user=user, scope=Consent.Scope.IMAGE_GENERATION, granted=False, text_version="v2")
    assert not user.has_consent(Consent.Scope.IMAGE_GENERATION)
    assert user.has_consent(Consent.Scope.PROCESSING)


def test_sans_ligne_de_consentement_pas_de_consentement():
    user = User.objects.create_user("vide@example.org", "secret-assez-long")
    assert not user.has_consent(Consent.Scope.PROCESSING)
    consent = Consent(scope=Consent.Scope.PROCESSING, granted=True, text_version="v1")
    assert str(consent) == "processing=oui (v1)"
