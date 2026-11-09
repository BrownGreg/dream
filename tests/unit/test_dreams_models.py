"""Modèle de données des rêves (DREAM-4) : chiffrement, contraintes, cascade."""

import pytest
from cryptography.fernet import InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, connection, transaction

from dreams import fields
from dreams.models import ApiCall, Dream, EmotionAnalysis, GeneratedAsset, Transcription
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory

pytestmark = pytest.mark.django_db

SECRET_TEXT = "Je volais au-dessus d'une ville de verre"


def _raw(table: str, column: str, pk_column: str, pk) -> str:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {table} WHERE {pk_column} = %s", [pk])  # noqa: S608 - noms en dur
        return cursor.fetchone()[0]


def test_la_transcription_est_chiffree_en_base_et_lisible_en_python():
    transcription = TranscriptionFactory(text=SECRET_TEXT)
    raw = _raw("dreams_transcription", "text", "id", transcription.pk)
    assert SECRET_TEXT not in raw
    assert raw.startswith("gAAAA")  # jeton Fernet
    assert Transcription.objects.get(pk=transcription.pk).text == SECRET_TEXT


def test_titre_et_prompt_visuel_sont_chiffres():
    dream = DreamFactory(title="La ville de verre")
    asset = GeneratedAsset.objects.create(
        dream=dream, kind=GeneratedAsset.Kind.IMAGE, status=GeneratedAsset.Status.OK, visual_prompt="glass city"
    )
    assert "verre" not in _raw("dreams_dream", "title", "id", dream.pk.hex)
    assert "glass" not in _raw("dreams_generatedasset", "visual_prompt", "id", asset.pk)
    assert Dream.objects.get(pk=dream.pk).title == "La ville de verre"


def test_champ_vide_reste_vide_sans_chiffrement():
    dream = DreamFactory(title="")
    assert _raw("dreams_dream", "title", "id", dream.pk.hex) == ""


def test_rotation_de_cle_lecture_avec_l_ancienne_cle(settings):
    TranscriptionFactory(text=SECRET_TEXT)
    old_key = settings.FIELD_ENCRYPTION_KEYS[0]
    settings.FIELD_ENCRYPTION_KEYS = ["bm91dmVsbGUtY2xlLWRlLXJvdGF0aW9uLTMyLW9jdGU=", old_key]
    fields._fernet.cache_clear()
    try:
        assert Transcription.objects.get().text == SECRET_TEXT
    finally:
        fields._fernet.cache_clear()


def test_cle_inconnue_donne_une_erreur_de_configuration_explicite(settings):
    TranscriptionFactory(text=SECRET_TEXT)
    settings.FIELD_ENCRYPTION_KEYS = ["bm91dmVsbGUtY2xlLWRlLXJvdGF0aW9uLTMyLW9jdGU="]
    fields._fernet.cache_clear()
    try:
        with pytest.raises(ImproperlyConfigured, match="illisible"):
            Transcription.objects.get()
    finally:
        fields._fernet.cache_clear()


def test_sans_cle_le_chiffrement_refuse_de_fonctionner(settings):
    settings.FIELD_ENCRYPTION_KEYS = []
    fields._fernet.cache_clear()
    try:
        with pytest.raises(ImproperlyConfigured, match="vide"):
            fields.encrypt("x")
    finally:
        fields._fernet.cache_clear()


def test_decrypt_refuse_un_jeton_altere():
    token = fields.encrypt("secret")
    with pytest.raises(InvalidToken):
        fields.decrypt(token[:-4] + "AAAA")


def test_une_seule_emotion_courante_par_reve():
    dream = DreamFactory()
    EmotionFactory(dream=dream)
    with pytest.raises(IntegrityError), transaction.atomic():
        EmotionFactory(dream=dream)
    EmotionFactory(dream=dream, is_current=False, emotion="heureux")
    assert dream.current_emotion.emotion == "serein"


def test_la_confiance_reste_entre_0_et_1():
    with pytest.raises(IntegrityError), transaction.atomic():
        EmotionFactory(confidence="1.50")


def test_suppression_du_reve_en_cascade_mais_cout_conserve():
    dream = DreamFactory()
    TranscriptionFactory(dream=dream)
    EmotionFactory(dream=dream)
    GeneratedAsset.objects.create(dream=dream, kind="image", status="ok")
    call = ApiCall.objects.create(dream=dream, step="stt", provider="fake", model="m", outcome="ok", cost_usd="0.0035")
    dream.delete()
    assert not Transcription.objects.exists()
    assert not EmotionAnalysis.objects.exists()
    assert not GeneratedAsset.objects.exists()
    call.refresh_from_db()
    assert call.dream is None
    assert str(call.cost_usd) == "0.003500"


def test_image_courante_et_etat_final():
    dream = DreamFactory()
    assert dream.current_image is None
    assert not dream.is_finished
    GeneratedAsset.objects.create(dream=dream, kind="image", status="failed", attempt=1)
    ok = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok", attempt=2)
    assert dream.current_image == ok
    dream.status = Dream.Status.PARTIAL
    assert dream.is_finished


def test_representations_sans_contenu():
    dream = DreamFactory(title="Titre intime")
    assert "intime" not in str(dream)
    transcription = TranscriptionFactory(dream=dream)
    assert "volais" not in str(transcription)
    assert str(EmotionFactory(dream=dream)) == "serein (model)"
    asset = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok")
    assert str(asset) == "image #1 (ok)"
    call = ApiCall(step="stt", provider="mistral", model="m", outcome="ok", latency_ms=1200)
    assert str(call) == "stt/mistral ok 1200 ms"


def test_chemins_de_fichiers_aleatoires_sans_nom_d_origine():
    from dreams.models import _asset_path, _audio_path

    dream = DreamFactory()
    path = _audio_path(dream, "Rêve de Léa chez sa mère.WEBM")
    assert path.startswith(f"audio/{dream.id}/")
    assert path.endswith(".webm")
    assert "Léa" not in path
    asset = GeneratedAsset(dream=dream, kind="image")
    assert _asset_path(asset, "x").endswith(".bin")
