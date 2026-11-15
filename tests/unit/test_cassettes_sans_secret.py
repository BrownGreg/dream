"""Aucune cassette ne contient de clé, de jeton ou de corps de requête (DREAM-18)."""

import re
from pathlib import Path

import pytest

CASSETTES = sorted((Path(__file__).parent.parent / "cassettes").rglob("*.yaml"))
SECRET_PATTERNS = [
    re.compile(r"Bearer\s+(?!\[secret\])\S+"),
    re.compile(r"\bhf_[A-Za-z0-9]{10,}"),
    re.compile(r"x-key:\s*\n\s*-\s*(?!\[secret\])\S+", re.I),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
]


@pytest.mark.parametrize("cassette", CASSETTES, ids=lambda p: p.name)
def test_cassette_sans_secret_ni_corps(cassette):
    content = cassette.read_text(errors="replace")
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content), f"{cassette.name} : motif {pattern.pattern}"
    # Les corps de requête (audio, récit) sont remplacés à l'enregistrement.
    for body in re.findall(r"request:\n\s+body: (.+)", content):
        assert body.strip() in ("'[corps retire]'", "[corps retire]", "null", "''"), cassette.name


def test_filtre_de_requete_retire_le_corps():
    from tests.conftest import _scrub_request

    class Req:
        body = b"Je volais au-dessus de la mer"

    assert _scrub_request(Req()).body == b"[corps retire]"
    empty = Req()
    empty.body = None
    assert _scrub_request(empty).body is None
