"""Les fichiers statiques passent le post-traitement de production (manifest whitenoise).

Reproduit, sans Docker, l'étape ``collectstatic`` de l'image : une référence vers un
fichier absent (``sourceMappingURL``, ``url()`` CSS…) y fait échouer le build (incident #8).
"""

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_collectstatic_manifest_de_production(settings, tmp_path):
    settings.STATIC_ROOT = tmp_path
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    call_command("collectstatic", "--noinput", verbosity=0)
    assert (tmp_path / "staticfiles.json").exists()
    assert list(tmp_path.glob("vendor/chart-4.6.1.umd.min.*.js"))
