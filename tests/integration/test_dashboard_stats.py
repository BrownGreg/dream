"""Statistiques personnelles (DREAM-12, US-16)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from dashboard.stats import compute
from dreams.models import Dream
from tests.factories import DreamFactory, EmotionFactory, UserFactory

pytestmark = pytest.mark.django_db
PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 9, 12, 0, tzinfo=PARIS)  # lundi


def dream_at(user, when, emotion="serein"):
    dream = DreamFactory(user=user, status=Dream.Status.DONE)
    Dream.objects.filter(pk=dream.pk).update(created_at=when)
    if emotion:
        EmotionFactory(dream=dream, emotion=emotion)
    return dream


def test_sans_reve():
    stats = compute(UserFactory().id, "30", now=NOW)
    assert stats.total == 0
    assert stats.dominant is None
    assert stats.distribution == []
    assert all(n == 0 for _, n in stats.weeks)
    assert len(stats.months) == 12


def test_semaines_comblees_et_comptees(user):
    dream_at(user, datetime(2026, 11, 2, 8, tzinfo=PARIS))  # lundi
    dream_at(user, datetime(2026, 11, 8, 23, 30, tzinfo=PARIS))  # dimanche soir, même semaine à Paris
    dream_at(user, datetime(2026, 10, 20, 7, tzinfo=PARIS))
    stats = compute(user.id, "30", now=NOW)
    weeks = dict(stats.weeks)
    assert weeks[date(2026, 11, 2)] == 2
    assert weeks[date(2026, 10, 19)] == 1
    assert weeks[date(2026, 10, 26)] == 0
    assert stats.weeks[0][0] == date(2026, 10, 5)  # lundi de la semaine du début de période
    assert stats.weeks[-1][0] == date(2026, 11, 9)
    assert stats.total == 3
    assert stats.per_week == round(3 / (30 / 7), 1)


def test_periode_exclut_les_reves_anciens(user):
    dream_at(user, datetime(2026, 7, 1, tzinfo=PARIS))
    assert compute(user.id, "30", now=NOW).total == 0
    assert compute(user.id, "365", now=NOW).total == 1


def test_periode_inconnue_retombe_sur_90_jours(user):
    assert compute(user.id, "999", now=NOW).period_days == 90


def test_repartition_triee_et_dominante_sur_l_emotion_courante(user):
    for _ in range(2):
        dream_at(user, datetime(2026, 11, 3, tzinfo=PARIS), "stressant")
    corrected = dream_at(user, datetime(2026, 11, 4, tzinfo=PARIS), "stressant")
    corrected.emotions.update(is_current=False)
    EmotionFactory(dream=corrected, emotion="heureux", source="user", confidence=None)
    dream_at(user, datetime(2026, 11, 5, tzinfo=PARIS), "heureux")
    dream_at(user, datetime(2026, 11, 6, tzinfo=PARIS), "serein")
    stats = compute(user.id, "30", now=NOW)
    assert stats.distribution == [("heureux", 2), ("stressant", 2), ("serein", 1)]  # égalité : ordre de l'énumération
    assert stats.dominant == "heureux"


def test_reve_sans_emotion_compte_dans_le_total_seulement(user):
    dream_at(user, datetime(2026, 11, 3, tzinfo=PARIS), emotion=None)
    stats = compute(user.id, "30", now=NOW)
    assert stats.total == 1
    assert stats.distribution == []


def test_evolution_sur_12_mois_a_cheval_sur_l_annee(user):
    dream_at(user, datetime(2025, 12, 15, tzinfo=PARIS), "melancolique")
    dream_at(user, datetime(2026, 11, 1, 0, 30, tzinfo=PARIS), "serein")  # 31 oct. 23 h 30 UTC
    dream_at(user, datetime(2025, 11, 30, tzinfo=PARIS), "serein")  # hors fenêtre
    stats = compute(user.id, "365", now=NOW)
    assert stats.months[0] == "déc. 25"
    assert stats.months[-1] == "nov. 26"
    assert stats.evolution["melancolique"][0] == 1
    assert stats.evolution["serein"][-1] == 1
    assert sum(stats.evolution["serein"]) == 1


def test_isolation_entre_utilisateurs(user):
    dream_at(UserFactory(), datetime(2026, 11, 3, tzinfo=PARIS), "stressant")
    stats = compute(user.id, "365", now=NOW)
    assert stats.total == 0
    assert sum(sum(v) for v in stats.evolution.values()) == 0


def test_page_statistiques(client, user):
    client.force_login(user)
    dream_at(user, datetime.now(PARIS), "serein")
    response = client.get(reverse("dashboard:stats"), {"periode": "30"})
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-chart="weeks"' in html
    assert 'data-chart="distribution"' in html
    assert 'data-chart="evolution"' in html
    assert 'id="chart-data"' in html
    assert "Voir les données" in html
    assert 'aria-current="page"' in html
    assert "chart-4.6.1.umd.min.js" in html
    assert "Serein" in html
    data = response.context["chart_data"]
    assert data["distribution"]["values"] == [1]
    assert next(s["key"] for s in data["evolution"]["series"]) == "heureux"


def test_page_statistiques_vide_et_periode_invalide(client, user):
    client.force_login(user)
    response = client.get(reverse("dashboard:stats"), {"periode": "abc"})
    assert response.context["period"] == "90"
    assert "Aucun rêve sur cette période" in response.content.decode()


def test_page_statistiques_exige_une_connexion(client):
    assert client.get(reverse("dashboard:stats")).status_code == 302
