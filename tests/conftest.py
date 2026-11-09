"""Fixtures partagées."""

import pytest

from tests.factories import UserFactory


@pytest.fixture
def password() -> str:
    return "un-Mot-de-passe-solide-42"


@pytest.fixture
def user(password):
    return UserFactory(password=password)


# --- Cassettes VCR (pytest-recording) ------------------------------------------------
# Enregistrement volontaire seulement (`--record-mode=once` avec de vraies clés, corpus
# synthétique) ; en CI, `none` : aucune requête réseau ne peut partir.
SECRET_HEADERS = ["authorization", "x-key", "cookie", "set-cookie"]


def _scrub_request(request):
    # Le corps porte l'audio ou le récit : il n'est jamais écrit dans une cassette.
    request.body = b"[corps retire]" if request.body else request.body
    return request


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [(name, "[secret]") for name in SECRET_HEADERS],
        "filter_query_parameters": ["key", "token"],
        "before_record_request": _scrub_request,
        "record_mode": "none",
        "match_on": ["method", "scheme", "host", "path"],
        "decode_compressed_response": True,
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    from pathlib import Path

    return str(Path(__file__).parent / "cassettes" / request.module.__name__.rsplit(".", 1)[-1])
