"""Pipeline process_dream (DREAM-10) : bout en bout en mode fake, reprise, dégradations."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from accounts.models import Consent
from dreams import locks, pipeline
from dreams.models import ApiCall, Dream, GeneratedAsset, Transcription
from dreams.services.errors import SafetyRejectionError
from dreams.services.ports import GeneratedImage, VisualPrompt
from dreams.tasks import process_dream, regenerate_image
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory, UserFactory

pytestmark = pytest.mark.django_db
WAV = (Path(__file__).parent.parent / "fixtures" / "reve_court.wav").read_bytes()


@pytest.fixture(autouse=True)
def fast(mocker, settings):
    settings.AI_MODE = "fake"
    mocker.patch("time.sleep")


def make_dream(user=None, data=WAV, **kwargs):
    dream = DreamFactory(user=user or UserFactory(), audio_duration_s=Decimal("3.00"), **kwargs)
    if data is not None:
        dream.audio.save("reve.wav", ContentFile(data), save=True)
    return dream


def test_parcours_complet_en_mode_fake():
    dream = make_dream()
    assert pipeline.run(dream.id) == "done"
    dream.refresh_from_db()
    assert dream.status == "done"
    assert dream.error_code == ""
    assert dream.title
    assert dream.transcription.provider == "fake"
    assert dream.current_emotion.emotion
    image = dream.current_image
    assert image.status == "ok"
    assert image.file.name.endswith(".svg")
    assert image.visual_prompt
    assert not dream.audio
    assert dream.audio_purged_at is not None
    assert sorted(ApiCall.objects.values_list("step", flat=True)) == ["emotion", "image", "prompt", "stt"]


def test_tache_django_tasks():
    dream = make_dream()
    result = process_dream.enqueue(str(dream.id))
    assert result.return_value == "done"


def test_rejouer_un_reve_termine_ne_refait_rien():
    dream = make_dream()
    pipeline.run(dream.id)
    calls = ApiCall.objects.count()
    assert pipeline.run(dream.id) == "skipped"
    assert ApiCall.objects.count() == calls


def test_reve_inexistant():
    assert pipeline.run(DreamFactory.build().id) == "skipped"


def test_reprise_apres_plantage_ne_retranscrit_pas():
    dream = make_dream(data=None, status=Dream.Status.ANALYZING)
    TranscriptionFactory(dream=dream)
    assert pipeline.run(dream.id) == "done"
    assert not ApiCall.objects.filter(step="stt").exists()


def test_reprise_avec_emotion_existante():
    dream = make_dream(data=None, status=Dream.Status.GENERATING)
    TranscriptionFactory(dream=dream)
    EmotionFactory(dream=dream, emotion="heureux")
    pipeline.run(dream.id)
    assert not ApiCall.objects.filter(step__in=["stt", "emotion"]).exists()
    assert dream.emotions.count() == 1


def test_echec_image_donne_un_reve_partiel_qui_garde_le_reste(settings):
    settings.AI_FAKE_FAIL_STEPS = ["image"]
    dream = make_dream()
    assert pipeline.run(dream.id) == "partial"
    dream.refresh_from_db()
    assert Transcription.objects.filter(dream=dream).exists()
    assert dream.current_emotion is not None
    failed = dream.assets.get()
    assert (failed.status, failed.rejection_reason) == ("failed", "image_failed")
    # Une reprise ne relance pas d'image payante : la régénération est un choix de l'utilisateur.
    dream.status = Dream.Status.FAILED
    dream.save()
    pipeline.run(dream.id)
    assert dream.assets.count() == 1


def test_image_desactivee_par_l_utilisateur():
    dream = make_dream(image_disabled=True)
    assert pipeline.run(dream.id) == "done"
    skipped = dream.assets.get()
    assert (skipped.status, skipped.rejection_reason) == ("skipped", "image_disabled")
    assert not ApiCall.objects.filter(step__in=["prompt", "image"]).exists()


def test_pas_d_image_sans_consentement():
    user = UserFactory(consents=False)
    dream = make_dream(user=user)
    assert user.has_consent(Consent.Scope.PROCESSING)
    pipeline.run(dream.id)
    assert dream.assets.get().rejection_reason == "image_no_consent"


class Rejecting:
    """Générateur qui refuse les n premiers prompts."""

    def __init__(self, refusals):
        self.refusals = refusals
        self.prompts = []

    def generate(self, prompt, caller):
        self.prompts.append(prompt)
        if len(self.prompts) <= self.refusals:
            raise SafetyRejectionError
        return GeneratedImage(b"\xff\xd8jpeg", "jpg", "bfl", "flux-2-klein-4b")


def test_refus_de_securite_puis_reformulation_reussie(mocker):
    generator = Rejecting(refusals=1)
    mocker.patch("dreams.services.registry.image_generator", return_value=generator)
    dream = make_dream()
    assert pipeline.run(dream.id) == "done"
    assert len(generator.prompts) == 2
    assert "abstract" in generator.prompts[1]
    assert dream.current_image.file.name.endswith(".jpg")


def test_refus_de_securite_deux_fois_donne_un_placeholder(mocker):
    mocker.patch("dreams.services.registry.image_generator", return_value=Rejecting(refusals=2))
    dream = make_dream()
    assert pipeline.run(dream.id) == "partial"
    assert dream.assets.get().rejection_reason == "image_rejected"


def test_budget_epuise_avant_l_image(mocker):
    builder = MagicMock()
    builder.build.return_value = VisualPrompt("Titre", "prompt", "fake", "fake")
    mocker.patch("dreams.services.registry.prompt_builder", return_value=builder)
    from dreams.services.errors import BudgetExceededError

    mocker.patch("dreams.services.registry.image_generator").return_value.generate.side_effect = BudgetExceededError
    dream = make_dream()
    assert pipeline.run(dream.id) == "partial"
    assert dream.assets.get().rejection_reason == "image_budget"


def test_budget_epuise_bloque_la_transcription(settings):
    settings.AI_BUDGET_EUR = 0
    dream = make_dream()
    assert pipeline.run(dream.id) == "failed"
    dream.refresh_from_db()
    assert dream.error_code == "budget_exceeded"
    assert dream.audio  # conservé pour réessayer


def test_panne_stt_conserve_l_audio_puis_reussit_au_nouvel_essai(settings):
    settings.AI_FAKE_FAIL_STEPS = ["stt"]
    settings.AI_MAX_ATTEMPTS = 2
    dream = make_dream()
    assert pipeline.run(dream.id) == "failed"
    dream.refresh_from_db()
    assert (dream.status, dream.error_code) == ("failed", "provider_error")
    assert dream.audio
    settings.AI_FAKE_FAIL_STEPS = []
    assert pipeline.run(dream.id) == "done"


def test_transcription_vide(mocker):
    from dreams.services.errors import ProviderError

    mocker.patch("dreams.services.registry.transcriber").return_value.transcribe.side_effect = ProviderError(
        "transcription vide"
    )
    dream = make_dream()
    pipeline.run(dream.id)
    dream.refresh_from_db()
    assert dream.error_code == "transcription_empty"


def test_audio_corrompu():
    dream = make_dream(data=b"pas un audio")
    pipeline.run(dream.id)
    dream.refresh_from_db()
    assert (dream.status, dream.error_code) == ("failed", "audio_invalid")


def test_audio_absent():
    dream = make_dream(data=None)
    pipeline.run(dream.id)
    dream.refresh_from_db()
    assert dream.error_code == "audio_missing"


def test_erreur_inattendue_marque_le_reve_et_remonte(mocker):
    mocker.patch("dreams.services.registry.emotion_classifier", side_effect=RuntimeError("bug"))
    dream = make_dream()
    with pytest.raises(RuntimeError):
        pipeline.run(dream.id)
    dream.refresh_from_db()
    assert (dream.status, dream.error_code) == ("failed", "internal_error")


def test_purge_des_audios_de_plus_de_24_h():
    old = make_dream()
    recent = make_dream()
    Dream.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(hours=25))
    assert pipeline.purge_stale_audio() == 1
    old.refresh_from_db()
    recent.refresh_from_db()
    assert not old.audio
    assert old.audio_purged_at
    assert recent.audio


def test_regeneration_ajoute_une_tentative_dans_la_limite(settings):
    settings.AI_MAX_IMAGE_ATTEMPTS = 2
    dream = make_dream()
    pipeline.run(dream.id)
    assert regenerate_image.enqueue(str(dream.id)).return_value == "ok"
    assert list(dream.assets.values_list("attempt", flat=True).order_by("attempt")) == [1, 2]
    assert pipeline.regenerate(dream.id) == "failed"
    assert dream.assets.count() == 2
    dream.refresh_from_db()
    assert dream.status == "done"


def test_regeneration_impossible_sans_transcription():
    assert pipeline.regenerate(make_dream().id) == "skipped"


def _fake_postgres(mocker, *, acquired):
    # Seule la connexion vue par dreams.locks est simulée : l'ORM garde la vraie base.
    cursor = MagicMock()
    cursor.fetchone.return_value = (acquired,)
    fake = MagicMock(vendor="postgresql")
    fake.cursor.return_value.__enter__.return_value = cursor
    mocker.patch.object(locks, "connection", fake)
    return cursor


def test_verrou_postgres_deja_pris(mocker):
    dream = make_dream()
    cursor = _fake_postgres(mocker, acquired=False)
    assert pipeline.run(dream.id) == "skipped"
    assert pipeline.regenerate(dream.id) == "skipped"
    cursor.execute.assert_any_call("SELECT pg_try_advisory_lock(%s)", [locks._key(dream.id)])


def test_verrou_postgres_pris_puis_libere(mocker):
    dream = make_dream()
    cursor = _fake_postgres(mocker, acquired=True)
    with locks.dream_lock(dream.id) as acquired:
        assert acquired
    cursor.execute.assert_called_with("SELECT pg_advisory_unlock(%s)", [locks._key(dream.id)])
    assert 0 <= locks._key(dream.id) < 2**63


def test_messages_d_erreur():
    from dreams.messages import message_for

    assert "minuit" in message_for("quota_exceeded")
    assert message_for("code-inconnu") == message_for("internal_error")
    assert GeneratedAsset.Status.REJECTED == "rejected"
