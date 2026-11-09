"""L'administration n'expose jamais le contenu des rêves."""

import pytest
from django.urls import reverse

from accounts.models import User
from dreams.models import ApiCall
from tests.factories import DreamFactory, TranscriptionFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    client.force_login(User.objects.create_superuser("ops@example.org", "secret-assez-long"))
    return client


def test_admin_reve_sans_titre_ni_transcription(admin_client):
    dream = DreamFactory(title="Titre très intime")
    TranscriptionFactory(dream=dream, text="Récit très intime")
    listing = admin_client.get(reverse("admin:dreams_dream_changelist")).content.decode()
    detail = admin_client.get(reverse("admin:dreams_dream_change", args=[dream.pk])).content.decode()
    for page in (listing, detail):
        assert "intime" not in page
    assert admin_client.get(reverse("admin:dreams_dream_add")).status_code == 403


def test_journal_api_en_lecture_seule(admin_client):
    call = ApiCall.objects.create(step="stt", provider="fake", model="m", outcome="ok")
    assert admin_client.get(reverse("admin:dreams_apicall_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:dreams_apicall_add")).status_code == 403
    page = admin_client.get(reverse("admin:dreams_apicall_change", args=[call.pk]))
    assert page.status_code == 200
    assert b'name="_save"' not in page.content


def test_admin_utilisateurs_et_consentements(admin_client, user):
    page = admin_client.get(reverse("admin:accounts_user_change", args=[user.pk]))
    assert page.status_code == 200
    assert b"processing" in page.content
