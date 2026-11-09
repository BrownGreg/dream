"""Fixtures partagées."""

import pytest

from tests.factories import UserFactory


@pytest.fixture
def password() -> str:
    return "un-Mot-de-passe-solide-42"


@pytest.fixture
def user(password):
    return UserFactory(password=password)
