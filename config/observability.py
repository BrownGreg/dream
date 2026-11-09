"""Journaux structurés et Sentry, sans aucun contenu de rêve.

- structlog : JSON en production, console lisible en développement ; ``request_id`` et
  ``dream_id`` liés au contexte ; tout champ sensible est masqué avant écriture.
- Sentry : aucune donnée personnelle par défaut, corps de requête jamais envoyé,
  variables locales désactivées, et ``before_send`` qui masque les mêmes champs.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

# Champs qui peuvent contenir le récit, sa reformulation ou une donnée d'identification.
SENSITIVE_KEYS = frozenset(
    {"text", "transcription", "transcript", "prompt", "visual_prompt", "title", "email", "password", "content", "audio"}
)
REDACTED = "[masqué]"


def redact(_logger: Any, _method: str, event: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Processeur structlog : remplace la valeur des champs sensibles.

    Args:
        _logger: Logger (inutilisé).
        _method: Niveau (inutilisé).
        event: Dictionnaire de l'événement.

    Returns:
        L'événement masqué.
    """
    for key in list(event):
        if key.lower() in SENSITIVE_KEYS:
            event[key] = REDACTED
    return event


def logging_config(*, json_logs: bool, level: str = "INFO") -> dict[str, Any]:
    """Configuration ``LOGGING`` de Django branchée sur structlog.

    Args:
        json_logs: JSON (production) ou rendu console (développement).
        level: Niveau minimal.

    Returns:
        Le dictionnaire ``LOGGING``.
    """
    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(colors=False)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
                "foreign_pre_chain": shared,
            }
        },
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "structlog"}},
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            # Les traces d'erreur de requête de Django peuvent contenir le corps POST : on ne garde que le statut.
            "django.request": {"level": "ERROR", "propagate": True},
            "axes": {"level": "WARNING", "propagate": True},
        },
    }


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: REDACTED if str(k).lower() in SENSITIVE_KEYS else _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def sentry_before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """Retire de l'événement Sentry tout ce qui pourrait contenir un rêve ou une identité.

    Args:
        event: Événement Sentry.
        _hint: Informations complémentaires (inutilisées).

    Returns:
        L'événement nettoyé.
    """
    request = event.get("request") or {}
    for key in ("data", "cookies", "query_string"):
        request.pop(key, None)
    if "headers" in request:
        request["headers"] = {
            k: v for k, v in request["headers"].items() if k.lower() in {"user-agent", "x-request-id"}
        }
    user = event.get("user") or {}
    event["user"] = {"id": user["id"]} if "id" in user else {}
    for section in ("extra", "contexts", "tags"):
        if section in event:
            event[section] = _scrub(event[section])
    for crumb in (event.get("breadcrumbs") or {}).get("values", []):
        crumb["data"] = _scrub(crumb.get("data") or {})
    return event


def init_sentry(dsn: str, environment: str, release: str) -> None:
    """Active Sentry si un DSN est fourni.

    Args:
        dsn: DSN du projet Sentry (vide : rien n'est activé).
        environment: ``production``, ``dev``…
        release: Version déployée (SHA du commit).
    """
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release or None,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0.1,
        before_send=sentry_before_send,  # type: ignore[arg-type]
        integrations=[DjangoIntegration(), LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
    )
