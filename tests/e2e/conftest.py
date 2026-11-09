"""Fixtures des tests navigateur (Playwright + serveur Django réel)."""

import os

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
