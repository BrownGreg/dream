"""Réglages de la suite de tests : rapides, déterministes, sans appel réseau."""

from .base import *  # noqa: F403
from .base import BASE_DIR, env

SECRET_KEY = "test-uniquement"  # noqa: S105 - clé de test, sans valeur hors tests
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite://:memory:")}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = BASE_DIR / ".test-media"
TASKS = {"default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}}
FIELD_ENCRYPTION_KEYS = ["dGVzdC11bmlxdWVtZW50LWNsZS1kZS0zMi1vY3RldHM="]
AI_MODE = "fake"
AI_RETRY_BASE_SECONDS = 0.0
