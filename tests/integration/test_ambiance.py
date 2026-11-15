"""Ambiance sonore par émotion (DREAM-15, US-13)."""

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from dreams.ambiance import DESCRIPTIONS, ambiance_for
from dreams.emotions import Emotion
from dreams.models import Dream
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory

pytestmark = pytest.mark.django_db


def test_une_boucle_par_emotion_et_fichiers_presents():
    assert set(DESCRIPTIONS) == set(Emotion.values)
    for emotion in Emotion.values:
        path = Path(settings.STATICFILES_DIRS[0]) / "audio" / "ambiance" / f"{emotion}.mp3"
        assert path.stat().st_size > 10_000
        assert ambiance_for(emotion)["url"].endswith(f"audio/ambiance/{emotion}.mp3")


def test_emotion_inconnue():
    assert ambiance_for(None) is None
    assert ambiance_for("furieux") is None


def test_lecteur_sur_la_page_du_reve_sans_lecture_automatique(client, user):
    dream = DreamFactory(user=user, status=Dream.Status.DONE)
    TranscriptionFactory(dream=dream)
    EmotionFactory(dream=dream, emotion="melancolique")
    client.force_login(user)
    html = client.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "audio/ambiance/melancolique.mp3" in html
    assert "non générée par IA" in html
    assert "autoplay" not in html
    assert 'preload="none"' in html
