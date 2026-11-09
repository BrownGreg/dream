"""Envoi d'un rêve, validation serveur de l'audio et suivi de l'avancement (DREAM-6)."""

import subprocess
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from dreams.models import ApiCall, Dream, GeneratedAsset
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory, UserFactory

pytestmark = pytest.mark.django_db
FIXTURES = Path(__file__).parent.parent / "fixtures"
RECORD = reverse("dreams:record")


def upload(name="reve_court.wav", data=None):
    content = data if data is not None else (FIXTURES / name).read_bytes()
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


@pytest.fixture
def logged(client, user, settings, mocker):
    settings.AI_MODE = "fake"
    mocker.patch("time.sleep")
    client.force_login(user)
    return client


def test_page_d_enregistrement(logged):
    response = logged.get(RECORD)
    assert response.status_code == 200
    html = response.content.decode()
    assert "data-recorder" in html
    assert 'data-max-seconds="180"' in html
    assert 'accept=".wav,.mp3,.m4a,.webm,audio/*"' in html
    assert "js/recorder.js" in html


def test_page_exige_une_connexion(client):
    assert client.get(RECORD).status_code == 302


@pytest.mark.parametrize("name", ["reve_court.wav", "reve_court.webm", "reve_court.m4a"])
def test_envoi_valide_cree_le_reve_et_lance_le_traitement(logged, user, name, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = logged.post(RECORD, {"audio": upload(name)})
    dream = Dream.objects.get(user=user)
    assert response.status_code == 302
    assert response["Location"] == reverse("dreams:detail", args=[dream.id])
    assert len(callbacks) == 1
    dream.refresh_from_db()
    assert dream.status == "done"  # ImmediateBackend en test : la tâche a tourné
    assert dream.audio_duration_s > 0
    assert dream.audio_mime
    assert not dream.audio  # supprimé après transcription


def test_le_traitement_n_est_pas_dans_la_requete(logged, user, mocker):
    task = mocker.patch("dreams.views.process_dream")
    logged.post(RECORD, {"audio": upload()})
    task.enqueue.assert_not_called()  # pas encore : uniquement après validation de la transaction
    assert Dream.objects.get(user=user).status == "received"
    assert not ApiCall.objects.exists()


def test_choix_sans_image(logged, user, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        logged.post(RECORD, {"audio": upload(), "image_disabled": "on"})
    dream = Dream.objects.get(user=user)
    assert dream.image_disabled
    assert dream.assets.get().status == GeneratedAsset.Status.SKIPPED


def test_envoi_htmx_renvoie_hx_redirect(logged, user):
    response = logged.post(RECORD, {"audio": upload()}, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response["HX-Redirect"] == reverse("dreams:detail", args=[Dream.objects.get(user=user).id])


@pytest.mark.parametrize(
    ("data", "name", "message"),
    [
        (b"", "vide.wav", "vide"),
        (b"ceci est un texte, pas un audio", "faux.webm", "illisible"),
        ((FIXTURES / "corrompu.webm").read_bytes(), "corrompu.webm", "illisible"),
    ],
)
def test_fichiers_refuses(logged, user, data, name, message):
    response = logged.post(RECORD, {"audio": upload(name, data)})
    assert response.status_code in (200, 422)
    assert message in response.content.decode()
    assert not Dream.objects.exists()


def test_type_reel_et_non_extension(logged, mocker):
    mocker.patch("magic.from_buffer", return_value="application/pdf")
    response = logged.post(RECORD, {"audio": upload()})
    assert response.status_code == 422
    assert "illisible" in response.content.decode()


def test_trop_long(logged, settings):
    settings.AUDIO_MAX_SECONDS = 2
    response = logged.post(RECORD, {"audio": upload()})  # 3 s
    assert response.status_code == 422
    assert "dépasse 2 secondes" in response.content.decode()


def test_trop_court(logged, settings):
    settings.AUDIO_MIN_SECONDS = 5
    response = logged.post(RECORD, {"audio": upload()})
    assert "trop court" in response.content.decode()


def test_trop_volumineux(logged, settings):
    settings.AUDIO_MAX_BYTES = 1024
    response = logged.post(RECORD, {"audio": upload()})
    assert "dépasse 1 Ko" in response.content.decode()


def test_erreur_htmx_renvoie_le_fragment(logged):
    response = logged.post(RECORD, {"audio": upload("x.webm", b"texte")}, headers={"HX-Request": "true"})
    assert response.status_code == 422
    html = response.content.decode()
    assert "data-form-errors" in html
    assert "<html" not in html


def test_quota_atteint(logged, user, settings):
    settings.AI_USER_DAILY_DREAMS = 1
    DreamFactory(user=user)
    assert "minuit" in logged.get(RECORD).content.decode()
    response = logged.post(RECORD, {"audio": upload()})
    assert response.status_code == 429
    assert Dream.objects.filter(user=user).count() == 1


def test_budget_atteint(logged, settings):
    settings.AI_BUDGET_EUR = 0
    response = logged.post(RECORD, {"audio": upload()})
    assert response.status_code == 429
    assert "limite de dépenses" in response.content.decode()


def test_mesure_de_duree_impossible(logged, mocker):
    mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 60))
    response = logged.post(RECORD, {"audio": upload()})
    assert response.status_code == 422


# --- Suivi et résultat


def test_detail_en_cours_affiche_l_avancement_et_le_polling(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.ANALYZING)
    html = logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert 'hx-trigger="every 2s"' in html
    assert reverse("dreams:status", args=[dream.id]) in html
    assert 'aria-current="step"' in html
    assert "Analyse de l&#x27;émotion" in html


def test_statut_renvoie_le_fragment_puis_rafraichit_a_la_fin(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.TRANSCRIBING)
    url = reverse("dreams:status", args=[dream.id])
    fragment = logged.get(url)
    assert fragment.status_code == 200
    assert "<html" not in fragment.content.decode()
    dream.status = Dream.Status.DONE
    dream.save()
    assert logged.get(url)["HX-Refresh"] == "true"


def test_statut_signale_une_attente_longue(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.GENERATING)
    Dream.objects.filter(pk=dream.pk).update(created_at=dream.created_at - timedelta(minutes=3))
    assert "plus long que d'habitude" in logged.get(reverse("dreams:status", args=[dream.id])).content.decode()


def test_resultat_complet(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.DONE, title="La ville de verre")
    TranscriptionFactory(dream=dream, text="Je volais au-dessus d'une ville de verre.")
    EmotionFactory(dream=dream, emotion="serein", confidence=Decimal("0.82"))
    asset = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok")
    asset.file.save("image.svg", ContentFile(b"<svg/>"))
    html = logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "La ville de verre" in html
    assert "Image générée par IA" in html
    assert "Serein" in html
    assert "82 %" in html
    assert "ville de verre." in html
    assert "supprimé après la transcription" in html
    assert "hx-trigger" not in html


def test_resultat_partiel_explique_l_absence_d_image(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.PARTIAL)
    TranscriptionFactory(dream=dream)
    EmotionFactory(dream=dream, emotion="etrange", confidence=Decimal("0.40"), provider="local")
    GeneratedAsset.objects.create(dream=dream, kind="image", status="rejected", rejection_reason="image_rejected")
    html = logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "a refusé ce rêve" in html
    assert "estimation par lexique" in html
    assert "Image générée par IA" not in html


def test_echec_affiche_un_message_clair(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.FAILED, error_code="provider_timeout")
    html = logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "met trop de temps" in html
    assert 'role="alert"' in html


def test_reve_d_un_autre_utilisateur_introuvable(logged):
    other = DreamFactory(user=UserFactory())
    assert logged.get(reverse("dreams:detail", args=[other.id])).status_code == 404
    assert logged.get(reverse("dreams:status", args=[other.id])).status_code == 404


@pytest.mark.parametrize(
    ("seconds", "label"), [(180, "3 minutes"), (60, "1 minute"), (90, "90 secondes"), (1, "1 seconde")]
)
def test_durees_lisibles(seconds, label):
    from dreams.forms import human_duration

    assert human_duration(seconds) == label


def test_tailles_lisibles():
    from dreams.forms import human_size

    assert human_size(20 * 1024 * 1024) == "20 Mo"
    assert human_size(512 * 1024) == "512 Ko"
    assert human_size(10) == "1 Ko"
