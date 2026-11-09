"""Fixtures des tests navigateur (Playwright + serveur Django réel)."""

import os
from pathlib import Path

import pytest

# Playwright pilote le navigateur depuis une boucle asyncio : Django doit accepter les
# appels ORM synchrones des fixtures pendant ce temps (tests uniquement).
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def login(page, live_server):
    """Connecte un utilisateur dans le navigateur."""

    def _login(email: str, password: str) -> None:
        page.goto(f"{live_server.url}/comptes/connexion/")
        page.fill("#id_username", email)
        page.fill("#id_password", password)
        page.click("button[type=submit]")
        page.wait_for_url(f"{live_server.url}/")

    return _login


FAKE_MIC = Path(__file__).parent.parent / "fixtures" / "reve.wav"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Chromium partagé par tous les tests E2E, avec un micro simulé (voix de synthèse)."""
    return {
        **browser_type_launch_args,
        "args": [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-audio-capture={FAKE_MIC}",
        ],
    }
