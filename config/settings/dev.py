"""Réglages de développement local."""

from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-uniquement-jamais-en-production")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])  # noqa: S104 - écoute locale en conteneur
# Clé de développement publique : ne protège rien, sert à faire tourner l'application sans configuration.
FIELD_ENCRYPTION_KEYS = env.list("FIELD_ENCRYPTION_KEYS", default=["ZGV2LXVuaXF1ZW1lbnQtamFtYWlzLWVuLXByb2R1Y3Q="])
