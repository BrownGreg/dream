"""Appel Mistral à sortie JSON validée par schéma, commun à l'émotion et au prompt visuel.

API : ``POST /v1/chat/completions`` avec ``response_format`` de type ``json_schema``
(bloc 1, ``docs/preprod/maquette/benchmark/providers/mistral.py``, docs consultées le
2026-11-02). Coût compté sur ``usage.total_tokens``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings
from pydantic import BaseModel, ValidationError

from dreams.services.adapters._http import json_body, send
from dreams.services.errors import ProviderError
from dreams.services.http import CallContext, resilient_call

TIMEOUT = httpx.Timeout(20.0, connect=5.0)


class InvalidOutputError(ProviderError):
    """Le modèle a répondu hors schéma : une seule nouvelle demande, puis abandon."""

    code = "llm_invalid_output"

    def __init__(self) -> None:
        """Construit l'erreur passagère (un nouvel échantillonnage peut réussir)."""
        super().__init__("sortie non conforme au schéma", transient=True)


def chat_json[M: BaseModel](
    client: httpx.Client,
    ctx: CallContext,
    *,
    system: str,
    user: str,
    schema: type[M],
    estimated_tokens: int,
) -> M:
    """Demande au modèle un objet JSON conforme à ``schema``.

    Args:
        client: Client HTTP muni de son délai.
        ctx: Identification de l'appel (étape, modèle, rêve).
        system: Consigne système.
        user: Message utilisateur (le texte du rêve ; jamais journalisé).
        schema: Modèle Pydantic attendu.
        estimated_tokens: Jetons attendus, pour le contrôle de budget.

    Returns:
        La réponse validée.

    Raises:
        ProviderError: Échec du fournisseur ou sortie hors schéma deux fois de suite.
    """
    body = {
        "model": ctx.model,
        "temperature": 0.2,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__.lower(), "schema": schema.model_json_schema(), "strict": True},
        },
    }

    def call() -> tuple[M, int]:
        if not settings.MISTRAL_API_KEY:
            raise ProviderError("MISTRAL_API_KEY absente", status=401)
        response = send(
            client,
            "POST",
            f"{settings.MISTRAL_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json=body,
        )
        payload: dict[str, Any] = json_body(response)
        usage = payload.get("usage") or {}
        tokens = int(usage.get("total_tokens") or estimated_tokens)
        try:
            content = payload["choices"][0]["message"]["content"]
            return schema.model_validate_json(content), tokens
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise InvalidOutputError from exc

    result, _ = resilient_call(
        ctx, call, estimated_units=Decimal(estimated_tokens), billed_units=lambda r: Decimal(r[1]), max_attempts=2
    )
    return result
