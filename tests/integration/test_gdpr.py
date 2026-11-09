"""Compte : consentement image, export des données, suppression du compte (DREAM-14 ; US-15, US-17)."""

import io
import json
import zipfile
from decimal import Decimal

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse

from accounts.models import Consent, User
from dreams.models import ApiCall, Dream, GeneratedAsset
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory, UserFactory

pytestmark = pytest.mark.django_db
ACCOUNT = reverse("accounts:account")


@pytest.fixture
def logged(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def full_dream(user):
    dream = DreamFactory(user=user, status=Dream.Status.DONE, title="La ville de verre")
    TranscriptionFactory(dream=dream, text="Je volais au-dessus d'une ville de verre.")
    EmotionFactory(dream=dream, emotion="serein", confidence=Decimal("0.80"), is_current=False)
    EmotionFactory(dream=dream, emotion="heureux", source="user", confidence=None)
    asset = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok", visual_prompt="glass city")
    asset.file.save("image.svg", ContentFile(b"<svg>verre</svg>"))
    return dream


def test_page_mon_compte(logged, user):
    html = logged.get(ACCOUNT).content.decode()
    assert user.email in html
    assert "Exporter mes données" in html
    assert "Supprimer mon compte" in html
    assert "checked" in html  # consentement image accordé par la fabrique


def test_page_exige_une_connexion(client):
    assert client.get(ACCOUNT).status_code == 302


def test_retirer_puis_redonner_le_consentement_image(logged, user):
    logged.post(reverse("accounts:image_consent"), {})
    assert not user.has_consent(Consent.Scope.IMAGE_GENERATION)
    logged.post(reverse("accounts:image_consent"), {"granted": "on"})
    assert user.has_consent(Consent.Scope.IMAGE_GENERATION)
    assert user.consents.filter(scope="image_generation").count() == 3  # initial + retrait + accord
    logged.post(reverse("accounts:image_consent"), {"granted": "on"})  # même choix : pas de ligne en plus
    assert user.consents.filter(scope="image_generation").count() == 3


def test_export_zip_complet(logged, user, full_dream):
    response = logged.post(reverse("accounts:export"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert 'attachment; filename="mes-reves-' in response["Content-Disposition"]
    assert response["Cache-Control"] == "no-store"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    data = json.loads(archive.read("donnees.json"))
    assert data["format"] == "dreamsynth-export"
    assert data["account"]["email"] == user.email
    assert {c["scope"] for c in data["consents"]} == {"processing", "image_generation"}
    (dream,) = data["dreams"]
    assert dream["title"] == "La ville de verre"
    assert dream["transcription"]["text"] == "Je volais au-dessus d'une ville de verre."
    assert [(e["emotion"], e["source"], e["current"]) for e in dream["emotions"]] == [
        ("serein", "model", False),
        ("heureux", "user", True),
    ]
    image = dream["images"][0]
    assert image["ai_generated"] is True
    assert archive.read(image["file"]) == b"<svg>verre</svg>"


def test_export_ne_contient_pas_les_reves_des_autres(logged, user):
    other = DreamFactory(user=UserFactory(), title="Secret d'un autre")
    TranscriptionFactory(dream=other, text="Récit d'un autre")
    data = json.loads(zipfile.ZipFile(io.BytesIO(logged.post(reverse("accounts:export")).content)).read("donnees.json"))
    assert data["dreams"] == []


def test_export_en_get_refuse(logged):
    assert logged.get(reverse("accounts:export")).status_code == 405


def test_suppression_du_compte_avec_le_bon_mot_de_passe(logged, user, password, full_dream):
    image_path = full_dream.current_image.file.name
    ApiCall.objects.create(dream=full_dream, step="image", provider="fake", model="m", outcome="ok", cost_usd="0.01")
    response = logged.post(reverse("accounts:delete"), {"password": password}, follow=True)
    assert "supprimés définitivement" in response.content.decode()
    assert not User.objects.filter(pk=user.pk).exists()
    assert not Dream.objects.exists()
    assert not Consent.objects.exists()
    assert not default_storage.exists(image_path)
    call = ApiCall.objects.get()
    assert call.dream is None
    assert str(call.cost_usd) == "0.010000"
    assert logged.get(ACCOUNT).status_code == 302  # déconnecté


def test_suppression_refusee_avec_un_mauvais_mot_de_passe(logged, user):
    response = logged.post(reverse("accounts:delete"), {"password": "faux"}, follow=True)
    assert "Mot de passe incorrect" in response.content.decode()
    assert User.objects.filter(pk=user.pk).exists()


def test_suppression_ne_touche_pas_les_autres_comptes(logged, password):
    other = DreamFactory(user=UserFactory())
    logged.post(reverse("accounts:delete"), {"password": password})
    assert Dream.objects.filter(pk=other.pk).exists()
