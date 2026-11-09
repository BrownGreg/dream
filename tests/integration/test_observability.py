"""Observabilité : journaux sans contenu, request_id, Sentry nettoyé, page /ops (DREAM-17)."""

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from config.observability import REDACTED, init_sentry, redact, sentry_before_send
from dashboard import ops
from dreams import pipeline
from dreams.models import ApiCall, Dream
from tests.factories import DreamFactory, UserFactory

pytestmark = pytest.mark.django_db
WAV = (Path(__file__).parent.parent / "fixtures" / "reve_court.wav").read_bytes()


def queued_task(minutes_ago: int = 0):
    """Ligne de tâche en attente, telle que l'écrit le backend base de données."""
    from django_tasks_db.models import DBTaskResult

    now = timezone.now()
    task = DBTaskResult.objects.create(
        status="READY",
        args_kwargs={"args": ["00000000-0000-0000-0000-000000000000"], "kwargs": {}},
        task_path="dreams.tasks.process_dream",
        queue_name="default",
        backend_name="default",
        run_after=now,
    )
    DBTaskResult.objects.filter(pk=task.pk).update(enqueued_at=now - timedelta(minutes=minutes_ago))
    return task


def test_redact_masque_les_champs_sensibles():
    event = {"event": "x", "text": "récit", "Title": "titre", "dream_id": "abc", "email": "a@b.c"}
    assert redact(None, "info", event) == {
        "event": "x",
        "text": REDACTED,
        "Title": REDACTED,
        "dream_id": "abc",
        "email": REDACTED,
    }


def test_aucun_contenu_de_reve_dans_les_journaux(caplog, settings, mocker):
    settings.AI_MODE = "fake"
    mocker.patch("time.sleep")
    user = UserFactory(email="secret.person@example.org")
    dream = DreamFactory(user=user, audio_duration_s=Decimal(3))
    dream.audio.save("Léa-chez-sa-mère.wav", ContentFile(WAV))
    caplog.set_level("INFO")
    pipeline.run(dream.id)
    dream.refresh_from_db()
    logs = caplog.text
    assert "dream_processed" in logs
    assert str(dream.id) in logs  # identifiants techniques : oui
    for secret in (dream.transcription.text[:30], dream.title, dream.current_image.visual_prompt[:30], user.email):
        assert secret not in logs


def test_request_id_genere_ou_repris(client):
    response = client.get(reverse("health"))
    assert len(response["X-Request-ID"]) == 32
    assert client.get(reverse("health"), headers={"X-Request-ID": "abc-123-def"})["X-Request-ID"] == "abc-123-def"
    forged = client.get(reverse("health"), headers={"X-Request-ID": "<script>"})["X-Request-ID"]
    assert forged != "<script>"


def test_journal_de_requete_sans_corps_ni_identifiants(client, caplog, user, password):
    caplog.set_level("INFO")
    client.post(reverse("accounts:login"), {"username": user.email, "password": password})
    logs = caplog.text
    assert "accounts:login" in logs
    assert password not in logs
    assert user.email not in logs


def test_sentry_before_send_retire_corps_cookies_et_contenu():
    event = {
        "request": {
            "data": {"text": "récit"},
            "cookies": {"sessionid": "x"},
            "query_string": "q=1",
            "headers": {"User-Agent": "UA", "Cookie": "x", "X-Request-ID": "r"},
        },
        "user": {"id": "7", "email": "a@b.c", "ip_address": "1.2.3.4"},
        "extra": {"visual_prompt": "glass city", "nested": {"title": "t", "dream_id": "d"}},
        "breadcrumbs": {"values": [{"data": {"text": "récit", "status": 200}}]},
    }
    clean = sentry_before_send(event, {})
    assert "data" not in clean["request"]
    assert "cookies" not in clean["request"]
    assert clean["request"]["headers"] == {"User-Agent": "UA", "X-Request-ID": "r"}
    assert clean["user"] == {"id": "7"}
    assert clean["extra"] == {"visual_prompt": REDACTED, "nested": {"title": REDACTED, "dream_id": "d"}}
    assert clean["breadcrumbs"]["values"][0]["data"] == {"text": REDACTED, "status": 200}
    assert sentry_before_send({"user": {"email": "x"}}, {})["user"] == {}


def test_init_sentry(mocker):
    init = mocker.patch("sentry_sdk.init")
    init_sentry("", "dev", "")
    init.assert_not_called()
    init_sentry("https://k@o.ingest.sentry.io/1", "production", "abc123")
    kwargs = init.call_args.kwargs
    assert kwargs["send_default_pii"] is False
    assert kwargs["include_local_variables"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["before_send"] is sentry_before_send
    assert kwargs["release"] == "abc123"


def test_percentile():
    assert ops.percentile([], 95) is None
    assert ops.percentile([100], 50) == 100
    values = list(range(1, 101))
    assert ops.percentile(values, 50) == 50
    assert ops.percentile(values, 95) == 95


def test_metriques_fournisseurs_et_cout_par_reve():
    dream = DreamFactory(status=Dream.Status.DONE)
    for latency in (100, 200, 300, 400):
        ApiCall.objects.create(
            dream=dream, step="stt", provider="mistral", model="m", outcome="ok", latency_ms=latency, cost_usd="0.0035"
        )
    ApiCall.objects.create(dream=dream, step="stt", provider="mistral", model="m", outcome="error", http_status=503)
    ApiCall.objects.create(step="image", provider="bfl", model="k", outcome="blocked")
    rows = {r["step"]: r for r in ops.provider_metrics()}
    stt = rows["stt"]
    assert (stt["calls"], stt["p50_ms"], stt["p95_ms"], stt["error_rate"]) == (5, 200, 400, 20.0)
    assert stt["cost_usd"] == Decimal("0.014")
    assert rows["image"]["error_rate"] == 0.0  # un blocage budget n'est pas une erreur fournisseur
    overview = ops.overview()
    assert overview["cost_per_dream_usd"] == Decimal("0.014000")
    assert overview["queue"].worker_ok


def test_page_ops_reservee_au_staff(client, user):
    client.force_login(user)
    assert client.get(reverse("dashboard:ops")).status_code == 302
    staff = User.objects.create_user("ops@example.org", "secret-assez-long", is_staff=True)
    client.force_login(staff)
    dream = DreamFactory(title="Titre intime", status=Dream.Status.DONE)
    Dream.objects.filter(pk=dream.pk).update(updated_at=dream.created_at + timedelta(seconds=12))
    ApiCall.objects.create(
        dream=dream,
        step="image",
        provider="bfl",
        model="flux-2-klein-4b",
        outcome="ok",
        latency_ms=8000,
        cost_usd="0.012",
    )
    html = client.get(reverse("dashboard:ops")).content.decode()
    assert "flux-2-klein-4b" in html
    assert "0.01 €" in html or "0,01 €" in html
    assert "Titre intime" not in html
    assert "Worker à l&#x27;heure" in html or "Worker à l'heure" in html


def test_page_ops_alerte_budget(client, settings):
    settings.AI_BUDGET_EUR = 0.01
    ApiCall.objects.create(step="image", provider="bfl", model="k", outcome="ok", cost_usd="0.02")
    client.force_login(User.objects.create_user("ops@example.org", "secret-assez-long", is_staff=True))
    assert "Coupe-circuit déclenché" in client.get(reverse("dashboard:ops")).content.decode()


def test_file_en_retard():
    from django_tasks_db.models import DBTaskResult

    queued_task()
    assert ops.queue_state().ready == 1
    DBTaskResult.objects.update(enqueued_at=timezone.now() - timedelta(minutes=5))
    state = ops.queue_state()
    assert state.oldest_wait_s >= 299
    assert not state.worker_ok
    assert json.dumps(state.__dict__)
