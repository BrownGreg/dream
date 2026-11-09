"""Historique et filtres du tableau de bord (DREAM-11, US-09, US-10)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from dashboard.forms import DreamFilterForm
from dashboard.views import _excerpt
from dreams.models import Dream, GeneratedAsset
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory, UserFactory

pytestmark = pytest.mark.django_db
HOME = reverse("dashboard:home")
PARIS = ZoneInfo("Europe/Paris")


def dream_on(user, day, emotion="serein", title="Un rêve", **kwargs):
    dream = DreamFactory(user=user, status=Dream.Status.DONE, title=title, **kwargs)
    Dream.objects.filter(pk=dream.pk).update(created_at=datetime(2026, 11, day, 7, 30, tzinfo=PARIS))
    TranscriptionFactory(dream=dream, text=f"Récit du {day} novembre.")
    EmotionFactory(dream=dream, emotion=emotion)
    return dream


@pytest.fixture
def logged(client, user):
    client.force_login(user)
    return client


def titles(response):
    return [item["dream"].title for item in response.context["items"]]


def test_historique_vide(logged):
    html = logged.get(HOME).content.decode()
    assert "aucun rêve" in html


def test_historique_du_plus_recent_au_plus_ancien_et_seulement_les_miens(logged, user):
    dream_on(user, 1, title="Ancien")
    dream_on(user, 8, title="Récent")
    dream_on(UserFactory(), 9, title="Pas à moi")
    response = logged.get(HOME)
    assert titles(response) == ["Récent", "Ancien"]
    html = response.content.decode()
    assert "Récit du 8 novembre." in html
    assert "Serein" in html
    assert "Pas à moi" not in html


def test_vignette_si_image(logged, user):
    dream = dream_on(user, 3)
    asset = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok")
    asset.file.save("image.svg", ContentFile(b"<svg/>"))
    assert 'loading="lazy"' in logged.get(HOME).content.decode()


def test_statuts_en_cours_et_echec(logged, user):
    DreamFactory(user=user, status=Dream.Status.TRANSCRIBING)
    DreamFactory(user=user, status=Dream.Status.FAILED, error_code="audio_invalid")
    html = logged.get(HOME).content.decode()
    assert "En cours de traitement" in html
    assert "Non traité" in html


def test_filtre_plage_de_dates_bornes_incluses(logged, user):
    for day in (1, 3, 5, 7):
        dream_on(user, day, title=f"J{day}")
    assert titles(logged.get(HOME, {"du": "2026-11-03", "au": "2026-11-05"})) == ["J5", "J3"]


def test_filtre_plage_inversee_remise_dans_l_ordre(logged, user):
    for day in (1, 3, 5):
        dream_on(user, day, title=f"J{day}")
    assert titles(logged.get(HOME, {"du": "2026-11-05", "au": "2026-11-03"})) == ["J5", "J3"]


def test_filtre_humeurs_multiples(logged, user):
    dream_on(user, 1, emotion="serein", title="S")
    dream_on(user, 2, emotion="stressant", title="T")
    dream_on(user, 3, emotion="heureux", title="H")
    assert titles(logged.get(HOME, {"humeur": ["serein", "heureux"]})) == ["H", "S"]


def test_filtre_sur_l_emotion_courante_apres_correction(logged, user):
    dream = dream_on(user, 1, emotion="serein", title="Corrigé")
    dream.emotions.update(is_current=False)
    EmotionFactory(dream=dream, emotion="stressant", source="user", confidence=None)
    assert titles(logged.get(HOME, {"humeur": "serein"})) == []
    assert titles(logged.get(HOME, {"humeur": "stressant"})) == ["Corrigé"]


def test_filtres_combines(logged, user):
    dream_on(user, 1, emotion="serein", title="A")
    dream_on(user, 5, emotion="serein", title="B")
    dream_on(user, 5, emotion="stressant", title="C")
    assert titles(logged.get(HOME, {"du": "2026-11-04", "humeur": "serein"})) == ["B"]


def test_filtres_sans_resultat(logged, user):
    dream_on(user, 1)
    html = logged.get(HOME, {"humeur": "stressant"}).content.decode()
    assert "Aucun rêve ne correspond" in html


def test_valeurs_invalides_ignorees(logged, user):
    dream_on(user, 1)
    response = logged.get(HOME, {"du": "pas-une-date", "humeur": "furieux"})
    assert response.status_code == 200
    assert len(response.context["items"]) == 1


def test_pagination_conserve_les_filtres(logged, user):
    for day in range(1, 13):
        dream_on(user, day, emotion="serein", title=f"J{day}")
    first = logged.get(HOME, {"humeur": "serein"})
    assert len(first.context["items"]) == 10
    html = first.content.decode()
    assert "humeur=serein&amp;page=2" in html
    second = logged.get(HOME, {"humeur": "serein", "page": 2})
    assert titles(second) == ["J2", "J1"]
    assert "Page 2 sur 2" in second.content.decode()


def test_htmx_renvoie_seulement_la_liste(logged, user):
    dream_on(user, 1)
    response = logged.get(HOME, {"humeur": "serein"}, headers={"HX-Request": "true"})
    html = response.content.decode()
    assert 'id="dream-list"' in html
    assert "<html" not in html


def test_formulaire_actif():
    assert not DreamFilterForm({}).active
    assert DreamFilterForm({"humeur": ["serein"]}).active


def test_extrait_coupe_sur_un_mot():
    assert _excerpt("court") == "court"
    long_text = "mot " * 60
    excerpt = _excerpt(long_text)
    assert excerpt.endswith("…")
    assert len(excerpt) <= 141
    assert not excerpt[:-1].endswith(" mo")


def test_nombre_de_requetes_constant(logged, user, django_assert_max_num_queries):
    for day in range(1, 11):
        dream = dream_on(user, day)
        GeneratedAsset.objects.create(dream=dream, kind="image", status="ok")
    # session + utilisateur + comptage + page + émotions + images : pas de N+1.
    with django_assert_max_num_queries(8):
        logged.get(HOME)
