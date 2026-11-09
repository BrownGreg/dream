"""Réglages communs à tous les environnements.

Toute valeur qui change d'un environnement à l'autre, ou qui est secrète, est lue
dans les variables d'environnement (fichier ``.env`` en local, plateforme en production).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS: list[str] = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django_htmx",
    "django_tailwind_cli",
    "django_tasks_db",
    "axes",
    "accounts",
    "dreams",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # Doit rester en dernier : transforme un blocage de connexion en réponse lisible.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Authentification
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    # Axes en premier : il refuse la tentative avant tout contrôle du mot de passe.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# Force brute : 5 échecs pour un couple (identifiant, IP) → blocage 15 min.
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = 0.25
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "accounts/lockout.html"
AXES_SENSITIVE_PARAMETERS = ["password"]
# Le formulaire de connexion poste l'e-mail dans « username » ; Axes lirait sinon USERNAME_FIELD (« email »).
AXES_USERNAME_FORM_FIELD = "username"

# Version du texte de consentement affiché à l'inscription (preuve RGPD, art. 7).
CONSENT_TEXT_VERSION = "2026-11-09"

# Clés Fernet du chiffrement applicatif des récits ; la première chiffre, toutes déchiffrent (rotation).
FIELD_ENCRYPTION_KEYS: list[str] = env.list("FIELD_ENCRYPTION_KEYS", default=[])

# --- E-mail (réinitialisation du mot de passe)
EMAIL_CONFIG = env.email_url("EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Synthétiseur de rêves <no-reply@dreamsynth.local>")

# --- Internationalisation
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# --- Fichiers statiques et média
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "assets"]
# Fichiers des rêves : en base (ADR-010) par défaut, sur disque si STORAGE_BACKEND=filesystem.
STORAGE_BACKEND = env("STORAGE_BACKEND", default="database")
STORAGES = {
    "default": {
        "BACKEND": "dreams.storage.DatabaseStorage"
        if STORAGE_BACKEND == "database"
        else "dreams.storage.ProtectedFileSystemStorage"
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

TAILWIND_CLI_VERSION = "4.3.5"
TAILWIND_CLI_SRC_CSS = "frontend/source.css"
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"

# --- Tâches de fond (django.tasks + backend base de données, ADR-008)
TASKS = {
    "default": {
        "BACKEND": "django_tasks_db.DatabaseBackend",
        "QUEUES": ["default"],
    }
}

# --- IA : adapters, budget et résilience (ADR-008, ADR-009)
AI_MODE = env("AI_MODE", default="fake")  # real | fake
AI_BUDGET_EUR = env.float("AI_BUDGET_EUR", default=15.0)
AI_BUDGET_ALERT_RATIO = env.float("AI_BUDGET_ALERT_RATIO", default=0.8)
AI_USD_EUR_RATE = env.float("AI_USD_EUR_RATE", default=1.0)
AI_USER_DAILY_DREAMS = env.int("AI_USER_DAILY_DREAMS", default=5)
AI_MAX_IMAGE_ATTEMPTS = env.int("AI_MAX_IMAGE_ATTEMPTS", default=2)
AI_MAX_ATTEMPTS = env.int("AI_MAX_ATTEMPTS", default=3)
AI_RETRY_BASE_SECONDS = env.float("AI_RETRY_BASE_SECONDS", default=1.0)
AI_FAKE_LATENCY_MS = env.int("AI_FAKE_LATENCY_MS", default=0)
AI_FAKE_FAIL_STEPS: list[str] = env.list("AI_FAKE_FAIL_STEPS", default=[])

# --- Fournisseurs (ADR-002 à ADR-004, ADR-008)
MISTRAL_API_KEY = env("MISTRAL_API_KEY", default="")
MISTRAL_BASE_URL = env("MISTRAL_BASE_URL", default="https://api.mistral.ai")
MISTRAL_STT_MODEL = env("MISTRAL_STT_MODEL", default="voxtral-mini-transcribe-3")
MISTRAL_LLM_MODEL = env("MISTRAL_LLM_MODEL", default="mistral-small-2603")
HF_TOKEN = env("HF_TOKEN", default="")
HF_BASE_URL = env("HF_BASE_URL", default="https://router.huggingface.co/hf-inference")
HF_EMOTION_MODEL = env("HF_EMOTION_MODEL", default="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
BFL_API_KEY = env("BFL_API_KEY", default="")
BFL_BASE_URL = env("BFL_BASE_URL", default="https://api.eu.bfl.ai")
BFL_IMAGE_MODEL = env("BFL_IMAGE_MODEL", default="flux-2-klein-4b")

# --- Enregistrements (validation client et serveur)
AUDIO_MAX_SECONDS = env.int("AUDIO_MAX_SECONDS", default=180)
AUDIO_MIN_SECONDS = env.int("AUDIO_MIN_SECONDS", default=1)
AUDIO_MAX_BYTES = env.int("AUDIO_MAX_BYTES", default=20 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = AUDIO_MAX_BYTES + 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
