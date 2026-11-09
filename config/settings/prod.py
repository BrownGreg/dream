"""Réglages de production (Render ou Docker Compose).

Toute valeur sensible vient de l'environnement ; l'absence de ``DJANGO_SECRET_KEY``
ou de ``DATABASE_URL`` fait échouer le démarrage plutôt que de dégrader la sécurité.
"""

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, env

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
FIELD_ENCRYPTION_KEYS = env.list("FIELD_ENCRYPTION_KEYS")
# Render fournit le nom d'hôte public du service.
if render_host := env("RENDER_EXTERNAL_HOSTNAME", default=""):
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, render_host]
    CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, f"https://{render_host}"]
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^health$"]
# Désactivable uniquement pour Docker Compose en HTTP local.
SESSION_COOKIE_SECURE = env.bool("DJANGO_SECURE_COOKIES", default=True)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=3600)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Derrière le proxy Render, l'IP cliente est la première de X-Forwarded-For.
AXES_IPWARE_PROXY_COUNT = env.int("AXES_IPWARE_PROXY_COUNT", default=1)
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]
