"""Contrôle de santé utilisé par Render et la CI."""

import pytest
from django.db import connection
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_ok(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}
    assert "no-cache" in response["Cache-Control"]


def test_health_503_si_la_base_tombe(client, mocker):
    mocker.patch.object(connection, "cursor", side_effect=RuntimeError("panne"))
    response = client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "error"
