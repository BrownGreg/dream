"""Adapter simulé : valide la chaîne de mesure sans clé API.

Les durées produites sont **fictives** (quelques millisecondes) et toujours marquées
mode="mock" : build_xlsx.py ne les reporte jamais comme mesures.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import time

import httpx

from providers.base import BenchItem, CallResult


class MockProvider:
    """Simule un fournisseur avec un taux d'échec et de retry déterministes."""

    def __init__(self, key: str, category: str, failure_rate: float = 0.05) -> None:
        """Initialise un générateur pseudo-aléatoire propre au fournisseur."""
        self.key = key
        self.category = category
        self.failure_rate = failure_rate
        seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        self._rng = random.Random(seed)

    async def run(self, client: httpx.AsyncClient, item: BenchItem) -> CallResult:
        """Simule un appel de quelques millisecondes."""
        del client
        start = time.perf_counter()
        await asyncio.sleep(self._rng.uniform(0.001, 0.004))
        ttfb = time.perf_counter() - start
        await asyncio.sleep(self._rng.uniform(0.001, 0.004))
        roll = self._rng.random()
        ok = roll >= self.failure_rate
        retries = 1 if roll < 2 * self.failure_rate else 0
        text = item.text if self.category == "STT" else ""
        return CallResult(
            provider=self.key,
            category=self.category,
            item_id=item.item_id,
            mode="mock",
            ok=ok,
            status_code=200 if ok else 503,
            ttfb_s=ttfb,
            total_s=time.perf_counter() - start,
            retries=retries,
            error="" if ok else "simulated 503",
            output_text=text,
        )
