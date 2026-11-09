"""Parcours d'authentification : inscription, connexion, force brute, mot de passe oublié."""

import re

import pytest
from django.core import mail
from django.urls import reverse

from accounts.models import Consent, User

pytestmark = pytest.mark.django_db

SIGNUP = reverse("accounts:signup")
LOGIN = reverse("accounts:login")
HOME = reverse("dashboard:home")


def _signup_data(**overrides):
    data = {
        "email": "Lea@Example.org",
        "password1": "un-Mot-de-passe-solide-42",
        "password2": "un-Mot-de-passe-solide-42",
        "consent_processing": "on",
    }
    data.update(overrides)
    return data


def test_page_d_inscription_affiche_les_deux_consentements(client):
    response = client.get(SIGNUP)
    assert response.status_code == 200
    assert b"consent_processing" in response.content
    assert b"consent_image_generation" in response.content


def test_inscription_enregistre_les_consentements_horodates_et_connecte(client, settings):
    response = client.post(SIGNUP, _signup_data(consent_image_generation="on"))
    assert response.status_code == 302
    assert response["Location"] == HOME
    user = User.objects.get(email="lea@example.org")
    consents = {c.scope: c for c in user.consents.all()}
    assert consents[Consent.Scope.PROCESSING].granted
    assert consents[Consent.Scope.IMAGE_GENERATION].granted
    assert consents[Consent.Scope.PROCESSING].text_version == settings.CONSENT_TEXT_VERSION
    assert client.get(HOME).status_code == 200


def test_inscription_sans_consentement_image_reste_possible(client):
    client.post(SIGNUP, _signup_data())
    user = User.objects.get(email="lea@example.org")
    assert user.has_consent(Consent.Scope.PROCESSING)
    assert not user.has_consent(Consent.Scope.IMAGE_GENERATION)


def test_inscription_refusee_sans_consentement_au_traitement(client):
    data = _signup_data()
    del data["consent_processing"]
    response = client.post(SIGNUP, data)
    assert response.status_code == 200
    assert "Ce consentement est nécessaire" in response.content.decode()
    assert not User.objects.exists()


def test_inscription_refuse_un_email_deja_pris(client, user):
    response = client.post(SIGNUP, _signup_data(email=user.email))
    assert response.status_code == 200
    assert User.objects.count() == 1


def test_utilisateur_connecte_est_redirige_depuis_l_inscription(client, user):
    client.force_login(user)
    assert client.get(SIGNUP)["Location"] == HOME


def test_tableau_de_bord_exige_une_connexion(client):
    response = client.get(HOME)
    assert response.status_code == 302
    assert response["Location"].startswith(LOGIN)


def test_connexion_par_email_insensible_a_la_casse(client, user, password):
    response = client.post(LOGIN, {"username": user.email.upper(), "password": password})
    assert response.status_code == 302
    assert response["Location"] == HOME


def test_deconnexion_en_post(client, user):
    client.force_login(user)
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert client.get(HOME).status_code == 302


def test_blocage_apres_cinq_echecs_meme_avec_le_bon_mot_de_passe(client, user, password):
    for _ in range(5):
        client.post(LOGIN, {"username": user.email, "password": "faux"})
    response = client.post(LOGIN, {"username": user.email, "password": password})
    assert response.status_code == 429
    assert "Trop de tentatives" in response.content.decode()


def test_reinitialisation_du_mot_de_passe_de_bout_en_bout(client, user):
    response = client.post(reverse("accounts:password_reset"), {"email": user.email})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    link = re.search(r"https?://[^/]+(/\S+)", mail.outbox[0].body).group(1)
    form_page = client.get(link, follow=True)
    assert form_page.status_code == 200
    new = "nouveau-Mot-de-passe-77"
    done = client.post(form_page.redirect_chain[-1][0], {"new_password1": new, "new_password2": new})
    assert done.status_code == 302
    user.refresh_from_db()
    assert user.check_password(new)


def test_reinitialisation_ne_revele_pas_si_le_compte_existe(client):
    response = client.post(reverse("accounts:password_reset"), {"email": "inconnu@example.org"})
    assert response.status_code == 302
    assert len(mail.outbox) == 0


def test_inscription_refuse_un_doublon_a_la_casse_pres(client, user):
    response = client.post(SIGNUP, _signup_data(email=user.email.upper()))
    assert response.status_code == 200
    assert "existe déjà" in response.content.decode()
    assert User.objects.count() == 1


def test_axes_journalise_l_email_saisi_et_pas_none(client, user):
    from axes.models import AccessAttempt

    client.post(LOGIN, {"username": user.email, "password": "faux"})
    assert AccessAttempt.objects.get().username == user.email


def test_un_autre_compte_n_est_pas_bloque_par_les_echecs_d_un_tiers(client, user, password):
    for _ in range(5):
        client.post(LOGIN, {"username": "attaquant@example.org", "password": "faux"})
    response = client.post(LOGIN, {"username": user.email, "password": password})
    assert response.status_code == 302


@pytest.mark.parametrize(
    ("name", "args"),
    [("accounts:password_reset", []), ("accounts:password_reset_done", []), ("accounts:password_reset_complete", [])],
)
def test_pages_mot_de_passe_utilisent_nos_gabarits_et_pas_ceux_de_l_admin(client, name, args):
    html = client.get(reverse(name, args=args)).content.decode()
    assert "administration de Django" not in html
    assert "Synthétiseur de rêves" in html
