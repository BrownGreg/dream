"""Réglages lus depuis l'environnement, tels qu'après ``scripts/install.sh``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def engine_with(settings_module: str, database_url: str) -> str:
    """Moteur de base choisi par un module de réglages, dans un processus neuf."""
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": settings_module, "DATABASE_URL": database_url}
    code = (
        "import django; django.setup(); from django.conf import settings; "
        "print(settings.DATABASES['default']['ENGINE'])"
    )
    completed = subprocess.run(  # noqa: S603 - interpréteur courant, code fixe
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@pytest.mark.parametrize("settings_module", ["config.settings.dev", "config.settings.test"])
def test_database_url_vide_donne_sqlite(settings_module):
    # `.env.example` contient `DATABASE_URL=` (vide) : une installation neuve doit tourner sur SQLite.
    assert engine_with(settings_module, "") == "django.db.backends.sqlite3"


def test_database_url_renseignee_est_respectee():
    url = "postgres://dream:dream@localhost:5432/dream"
    assert engine_with("config.settings.dev", url) == "django.db.backends.postgresql"
