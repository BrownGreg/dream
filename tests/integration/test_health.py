"""Contrôle de santé utilisé par Render et la CI."""

import pytest
from django.db import connection
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_ok(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "worker": "ok"}, "release": ""}
    assert "no-cache" in response["Cache-Control"]


def test_health_503_si_la_base_tombe(client, mocker):
    mocker.patch.object(connection, "cursor", side_effect=RuntimeError("panne"))
    response = client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "error"


def test_health_degrade_si_le_worker_est_en_retard(client):
    from tests.integration.test_observability import queued_task

    queued_task(minutes_ago=10)
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "checks": {"database": "ok", "worker": "stale"}, "release": ""}


def test_health_donne_le_commit_deploye(client, settings):
    # La CI attend que /health annonce le commit qu'elle vient de tester (sinon elle validerait l'ancienne instance).
    settings.RELEASE = "48bb3dbd6134f3552706f8bc1cfb0a4563aded92"
    response = client.get(reverse("health"))
    assert response.json()["release"] == "48bb3dbd6134f3552706f8bc1cfb0a4563aded92"
