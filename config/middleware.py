"""Corrélation des requêtes : ``request_id`` dans le contexte des journaux et en en-tête."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

log = structlog.get_logger("http")
_VALID_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class RequestIdMiddleware:
    """Attribue un identifiant à chaque requête et journalise sa durée (sans contenu)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Mémorise la suite de la chaîne de middlewares."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Traite la requête.

        Reprend ``X-Request-ID`` du proxy s'il est bien formé, sinon en génère un.

        Args:
            request: Requête entrante.

        Returns:
            La réponse, avec l'en-tête ``X-Request-ID``.
        """
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        match = getattr(request, "resolver_match", None)
        log.info(
            "request",
            method=request.method,
            route=match.view_name if match else "",
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response["X-Request-ID"] = request_id
        return response
