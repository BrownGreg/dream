"""Commande de démonstration seed_demo."""

import pytest
from django.core.management import CommandError, call_command

from accounts.models import User
from dreams.models import ApiCall, Dream

pytestmark = pytest.mark.django_db


def test_seed_demo_cree_des_reves_synthetiques_sans_journal(settings, mocker):
    settings.DEBUG = True
    mocker.patch("time.sleep")
    call_command("seed_demo", "--dreams", "5", "--email", "demo@example.org")
    user = User.objects.get(email="demo@example.org")
    assert Dream.objects.filter(user=user, status="done").count() == 5
    assert all(d.current_image and d.current_emotion for d in Dream.objects.filter(user=user))
    assert not ApiCall.objects.exists()
    call_command("seed_demo", "--dreams", "2", "--email", "demo@example.org")  # recrée le compte
    assert Dream.objects.count() == 2


def test_seed_demo_refuse_hors_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_demo", "--dreams", "1")
