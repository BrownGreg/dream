"""Traduction des réponses httpx en erreurs du domaine, commune aux adapters réels."""

from __future__ import annotations

from typing import Any

import httpx

from dreams.services.errors import ProviderError, ProviderTimeoutError


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    try:
        return float(value) if value else None
    except ValueError:
        return None  # date HTTP : on garde le backoff exponentiel


def send(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Envoie une requête et lève une erreur du domaine si elle échoue.

    Args:
        client: Client httpx muni de son délai.
        method: Verbe HTTP.
        url: URL absolue.
        **kwargs: Arguments transmis à ``httpx.Client.request``.

    Returns:
        La réponse, de statut < 400.

    Raises:
        ProviderTimeoutError: Délai dépassé ou coupure réseau.
        ProviderError: Statut HTTP ≥ 400, classé passager ou non.
    """
    try:
        response = client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ProviderTimeoutError(type(exc).__name__) from exc
    if response.status_code >= 400:
        raise ProviderError.from_status(
            response.status_code,
            f"{method} {httpx.URL(url).path} → HTTP {response.status_code}",
            _retry_after(response),
        )
    return response


def json_body(response: httpx.Response) -> dict[str, Any]:
    """Décode une réponse JSON objet.

    Args:
        response: Réponse du fournisseur.

    Returns:
        Le dictionnaire décodé.

    Raises:
        ProviderError: Si le corps n'est pas un objet JSON (réponse inexploitable, non passagère).
    """
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderError("réponse non JSON", status=response.status_code) from exc
    if not isinstance(payload, dict):
        raise ProviderError("réponse JSON inattendue", status=response.status_code)
    return payload
