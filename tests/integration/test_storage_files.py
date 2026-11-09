"""Stockage en base (ADR-010) et vue protégée des fichiers."""

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse

from dreams.models import StoredFile
from dreams.storage import DatabaseStorage, ProtectedFileSystemStorage
from tests.factories import DreamFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_database_storage_cycle_complet():
    storage = DatabaseStorage()
    name = storage.save("assets/x/image.jpg", ContentFile(b"\xff\xd8data"))
    assert storage.exists(name)
    assert storage.size(name) == 6
    assert storage.open(name).read() == b"\xff\xd8data"
    assert storage.url(name) == "/reves/fichiers/assets/x/image.jpg"
    storage.save(name + "2", ContentFile("texte"))
    assert storage.open(name + "2").read() == b"texte"
    assert str(StoredFile.objects.get(name=name)) == "assets/x/image.jpg (6 o)"
    storage.delete(name)
    assert not storage.exists(name)
    with pytest.raises(FileNotFoundError):
        storage.open(name)
    with pytest.raises(FileNotFoundError):
        storage.size(name)


def test_nom_deja_pris_obtient_un_nom_libre():
    storage = DatabaseStorage()
    first = storage.save("assets/a/b.jpg", ContentFile(b"1"))
    second = storage.save("assets/a/b.jpg", ContentFile(b"2"))
    assert first != second


def test_stockage_disque_servi_par_la_vue_protegee(tmp_path):
    assert ProtectedFileSystemStorage(location=tmp_path).url("assets/x/y.jpg") == "/reves/fichiers/assets/x/y.jpg"


@pytest.fixture
def owned_file():
    dream = DreamFactory()
    path = default_storage.save(f"assets/{dream.id}/image-1.svg", ContentFile(b"<svg/>"))
    return dream, path


def test_le_proprietaire_obtient_son_fichier(client, owned_file):
    dream, path = owned_file
    client.force_login(dream.user)
    response = client.get(reverse("dreams:file", args=[path]))
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"<svg/>"
    assert response["Content-Type"] == "image/svg+xml"
    assert "sandbox" in response["Content-Security-Policy"]
    assert response["Cache-Control"] == "private, max-age=86400"


def test_un_autre_utilisateur_recoit_404(client, owned_file):
    _, path = owned_file
    client.force_login(UserFactory())
    assert client.get(reverse("dreams:file", args=[path])).status_code == 404


def test_anonyme_redirige_vers_la_connexion(client, owned_file):
    _, path = owned_file
    assert client.get(reverse("dreams:file", args=[path])).status_code == 302


@pytest.mark.parametrize("path", ["autre/x/y.jpg", "assets/pas-un-uuid/y.jpg", "assets/../../etc", "assets/y.jpg"])
def test_chemins_invalides(client, user, path):
    client.force_login(user)
    assert client.get(reverse("dreams:file", args=[path])).status_code == 404


def test_fichier_absent(client):
    dream = DreamFactory()
    client.force_login(dream.user)
    assert client.get(reverse("dreams:file", args=[f"assets/{dream.id}/absent.jpg"])).status_code == 404
