"""Actions sur un rêve : corriger, régénérer, supprimer (DREAM-13 ; US-05, US-14, US-12)."""

from decimal import Decimal

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse

from accounts.models import Consent
from dreams.models import ApiCall, Dream, EmotionAnalysis, GeneratedAsset, Transcription
from dreams.services.ports import VisualPrompt
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged(client, user, settings, mocker):
    settings.AI_MODE = "fake"
    mocker.patch("time.sleep")
    client.force_login(user)
    return client


@pytest.fixture
def done_dream(user):
    dream = DreamFactory(user=user, status=Dream.Status.DONE, title="Titre")
    TranscriptionFactory(dream=dream, text="Je volais au-dessus de la mer calme.")
    EmotionFactory(dream=dream, emotion="serein", confidence=Decimal("0.80"))
    asset = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok", attempt=1)
    asset.file.save("image.svg", ContentFile(b"<svg/>"))
    return dream


def url(name, dream):
    return reverse(f"dreams:{name}", args=[dream.id])


def test_page_detail_propose_les_actions(logged, done_dream):
    html = logged.get(url("detail", done_dream)).content.decode()
    assert "Corriger le récit" in html
    assert "Ce n'est pas la bonne émotion" in html
    assert "Générer une autre image" in html
    assert url("delete", done_dream) in html


def test_corriger_le_recit(logged, done_dream):
    response = logged.post(url("edit_transcription", done_dream), {"text": "  Je nageais avec des dauphins.  "})
    assert response.status_code == 302
    transcription = Transcription.objects.get(dream=done_dream)
    assert transcription.text == "Je nageais avec des dauphins."
    assert transcription.edited_by_user
    assert "Récit corrigé par vous" in logged.get(url("detail", done_dream)).content.decode()


def test_recit_vide_refuse(logged, done_dream):
    logged.post(url("edit_transcription", done_dream), {"text": "   "})
    assert Transcription.objects.get(dream=done_dream).text.startswith("Je volais")


def test_corriger_sans_transcription(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.FAILED)
    response = logged.post(url("edit_transcription", dream), {"text": "x"}, follow=True)
    assert "pas encore de transcription" in response.content.decode()


def test_corriger_l_emotion_garde_l_historique(logged, done_dream):
    logged.post(url("edit_emotion", done_dream), {"emotion": "stressant"})
    current = done_dream.current_emotion
    assert (current.emotion, current.source, current.confidence) == ("stressant", "user", None)
    assert EmotionAnalysis.objects.filter(dream=done_dream, is_current=False, emotion="serein").exists()
    assert "Choisie par vous" in logged.get(url("detail", done_dream)).content.decode()


def test_emotion_invalide_refusee(logged, done_dream):
    logged.post(url("edit_emotion", done_dream), {"emotion": "furieux"})
    assert done_dream.current_emotion.emotion == "serein"


def test_regenerer_une_image(logged, done_dream, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = logged.post(url("regenerate", done_dream))
    assert response.status_code == 302
    assert list(done_dream.assets.values_list("attempt", flat=True).order_by("attempt")) == [1, 2]
    done_dream.refresh_from_db()
    assert done_dream.status == "done"
    assert ApiCall.objects.filter(step="image").count() == 1


def test_regeneration_utilise_le_recit_corrige(logged, done_dream, mocker, django_capture_on_commit_callbacks):
    logged.post(url("edit_transcription", done_dream), {"text": "Une baleine dans le salon."})
    builder = mocker.patch("dreams.services.registry.prompt_builder")
    builder.return_value.build.return_value = VisualPrompt("T", "whale", "fake", "fake")
    with django_capture_on_commit_callbacks(execute=True):
        logged.post(url("regenerate", done_dream))
    assert builder.return_value.build.call_args.args[0] == "Une baleine dans le salon."


def test_regeneration_bloquee_apres_le_maximum(logged, done_dream, settings):
    settings.AI_MAX_IMAGE_ATTEMPTS = 1
    html = logged.get(url("detail", done_dream)).content.decode()
    assert "Générer une autre image" not in html
    response = logged.post(url("regenerate", done_dream), follow=True)
    assert "nombre maximal" in response.content.decode()
    assert done_dream.assets.count() == 1


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("disabled", "ne pas générer"),
        ("no_consent", "sans votre accord"),
        ("budget", "budget du service"),
        ("running", "erreur inattendue"),
    ],
)
def test_regeneration_bloquee(logged, done_dream, settings, setup, message):
    if setup == "disabled":
        Dream.objects.filter(pk=done_dream.pk).update(image_disabled=True)
    elif setup == "no_consent":
        Consent.objects.create(user=done_dream.user, scope="image_generation", granted=False, text_version="v2")
    elif setup == "budget":
        settings.AI_BUDGET_EUR = 0
    else:
        Dream.objects.filter(pk=done_dream.pk).update(status=Dream.Status.GENERATING)
    response = logged.post(url("regenerate", done_dream), follow=True)
    assert message in response.content.decode()


def test_supprimer_confirme_puis_efface_fichiers_et_lignes(logged, done_dream):
    path = done_dream.current_image.file.name
    call = ApiCall.objects.create(dream=done_dream, step="image", provider="fake", model="m", outcome="ok")
    confirm = logged.get(url("delete", done_dream))
    assert "définitivement" in confirm.content.decode()
    assert Dream.objects.filter(pk=done_dream.pk).exists()
    response = logged.post(url("delete", done_dream), follow=True)
    assert "supprimés définitivement" in response.content.decode()
    assert not Dream.objects.filter(pk=done_dream.pk).exists()
    assert not GeneratedAsset.objects.exists()
    assert not Transcription.objects.exists()
    assert not default_storage.exists(path)
    call.refresh_from_db()
    assert call.dream is None


def test_supprimer_efface_aussi_l_audio_en_attente(logged, user):
    dream = DreamFactory(user=user, status=Dream.Status.FAILED)
    dream.audio.save("reve.wav", ContentFile(b"RIFF"))
    path = dream.audio.name
    logged.post(url("delete", dream))
    assert not default_storage.exists(path)


@pytest.mark.parametrize("name", ["edit_transcription", "edit_emotion", "regenerate", "delete"])
def test_actions_interdites_sur_le_reve_d_un_autre(logged, name):
    other = DreamFactory(user=UserFactory(), status=Dream.Status.DONE)
    assert logged.post(url(name, other), {"text": "x", "emotion": "serein"}).status_code == 404
    assert Dream.objects.filter(pk=other.pk).exists()


@pytest.mark.parametrize("name", ["edit_transcription", "edit_emotion", "regenerate"])
def test_actions_refusent_get(logged, done_dream, name):
    assert logged.get(url(name, done_dream)).status_code == 405
