"""Contrat commun des adapters de benchmark et mesure d'un appel HTTP.

Chaque appel mesure :
- ttfb_s  : temps jusqu'au premier octet de la réponse (en-têtes + 1er bloc du corps) ;
- total_s : temps jusqu'au dernier octet ;
- retries : nombre de nouvelles tentatives (tenacity), comptées à part des échecs.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


@dataclass
class BenchItem:
    """Une entrée du corpus (audio pour STT, texte pour LLM/TTS, prompt pour T2I)."""

    item_id: str
    text: str = ""
    audio_path: str = ""


@dataclass
class CallResult:
    """Résultat brut d'un appel mesuré (une ligne du CSV)."""

    provider: str
    category: str
    item_id: str
    mode: str
    ok: bool
    status_code: int
    ttfb_s: float
    total_s: float
    retries: int
    error: str = ""
    billed_audio_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    output_chars: int = 0
    output_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def row(self) -> dict[str, Any]:
        """Ligne CSV (le champ `extra` est omis)."""
        data = asdict(self)
        data.pop("extra")
        return data


class BenchProvider(Protocol):
    """Adapter mesurable."""

    key: str
    category: str

    async def run(self, client: httpx.AsyncClient, item: BenchItem) -> CallResult:
        """Exécute un appel sur `item` et retourne la mesure."""
        ...


class RetryableStatusError(Exception):
    """Réponse HTTP qui justifie une nouvelle tentative."""

    def __init__(self, status: int) -> None:
        """Mémorise le code HTTP."""
        super().__init__(f"HTTP {status}")
        self.status = status


@dataclass
class Timing:
    """Mesure d'un échange HTTP en streaming."""

    status: int
    ttfb_s: float
    total_s: float
    body: bytes


async def timed_request(client: httpx.AsyncClient, build: Callable[[], httpx.Request]) -> Timing:
    """Envoie la requête en streaming et chronomètre premier et dernier octet."""
    start = time.perf_counter()
    response = await client.send(build(), stream=True)
    ttfb = -1.0
    chunks: list[bytes] = []
    try:
        # aiter_bytes décode le Content-Encoding (gzip chez Mistral) ;
        # aiter_raw rendait les octets compressés.
        async for chunk in response.aiter_bytes():
            if ttfb < 0:
                ttfb = time.perf_counter() - start
            chunks.append(chunk)
    finally:
        await response.aclose()
    total = time.perf_counter() - start
    if ttfb < 0:
        ttfb = total
    if response.status_code in RETRYABLE_STATUS:
        raise RetryableStatusError(response.status_code)
    return Timing(response.status_code, ttfb, total, b"".join(chunks))


async def measured(
    call: Callable[[], Awaitable[Timing]], max_attempts: int = 3
) -> tuple[Timing | None, int, str]:
    """Exécute `call` avec retries ; retourne (mesure de la tentative finale, retries, erreur)."""
    attempts = 0

    def retryable(exc: BaseException) -> bool:
        return isinstance(exc, RetryableStatusError | httpx.TransportError)

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.5, max=8),
            retry=retry_if_exception(retryable),
            reraise=False,
        ):
            with attempt:
                attempts += 1
                timing = await call()
                return timing, attempts - 1, ""
    except RetryError as exc:
        last = exc.last_attempt.exception()
        return None, attempts - 1, repr(last)
    except Exception as exc:
        return None, attempts - 1, repr(exc)
    return None, attempts - 1, "aucune tentative"
