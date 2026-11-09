"""Image par Black Forest Labs FLUX.2 [klein] 4B, endpoint UE (ADR-004).

API (https://docs.bfl.ai, consultée le 2026-11-09) : ``POST /v1/flux-2-klein-4b`` (en-tête
``x-key``) renvoie ``id``, ``polling_url`` et ``cost`` en crédits (1 crédit = 0,01 $) ; on
interroge ``polling_url`` jusqu'à ``Ready``, puis on télécharge ``result.sample`` aussitôt :
l'URL signée expire au bout de 10 minutes.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

from dreams.models import ApiCall
from dreams.services.adapters._http import json_body, send
from dreams.services.errors import ProviderError, ProviderTimeoutError, SafetyRejectionError
from dreams.services.http import CallContext, resilient_call
from dreams.services.ports import Caller, GeneratedImage

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
POLL_INTERVAL_S = 0.5
POLL_DEADLINE_S = 45.0
# ~0,014 $ par image d'1 mégapixel (ESTIMÉ, catalogue du bloc 1) : sert au contrôle de budget
# avant l'appel ; le coût journalisé est celui renvoyé par BFL.
ESTIMATED_CREDITS = Decimal("1.4")

PENDING = {"Pending", "Reasoning", "Generating"}
MODERATED = {"Request Moderated", "Content Moderated"}


class BflImageGenerator:
    """FLUX.2 [klein] 4B, 1024 x 1024, JPEG."""

    provider = "bfl"

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Prépare l'adapter.

        Args:
            client: Client HTTP (injecté par les tests).
            model: Endpoint BFL ; ``BFL_IMAGE_MODEL`` par défaut.
        """
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or settings.BFL_IMAGE_MODEL

    def _headers(self) -> dict[str, str]:
        if not settings.BFL_API_KEY:
            raise ProviderError("BFL_API_KEY absente", status=401)
        return {"x-key": settings.BFL_API_KEY, "accept": "application/json"}

    def _poll(self, polling_url: str) -> str:
        deadline = time.monotonic() + POLL_DEADLINE_S
        while time.monotonic() < deadline:
            payload = json_body(send(self.client, "GET", polling_url, headers=self._headers()))
            status = str(payload.get("status", ""))
            if status == "Ready":
                result: Any = payload.get("result") or {}
                sample = result.get("sample") if isinstance(result, dict) else None
                if not sample:
                    raise ProviderError("image prête sans URL")
                return str(sample)
            if status in MODERATED:
                raise SafetyRejectionError(status)
            if status not in PENDING:
                # « Error », « Failed », « Task not found » : le fournisseur a échoué, on peut réessayer.
                raise ProviderError(f"génération en échec : {status or 'statut absent'}", transient=True)
            time.sleep(POLL_INTERVAL_S)
        raise ProviderTimeoutError("image non prête dans le délai")

    def _call(self, prompt: str) -> tuple[GeneratedImage, Decimal]:
        submitted = json_body(
            send(
                self.client,
                "POST",
                f"{settings.BFL_BASE_URL}/v1/{self.model}",
                headers=self._headers(),
                json={
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "output_format": "jpeg",
                    "safety_tolerance": 2,
                },
            )
        )
        polling_url = submitted.get("polling_url")
        if not polling_url:
            raise ProviderError("réponse sans polling_url")
        credits = Decimal(str(submitted["cost"])) if submitted.get("cost") is not None else ESTIMATED_CREDITS
        sample_url = self._poll(str(polling_url))
        image = send(self.client, "GET", sample_url)
        if not image.content:
            raise ProviderError("image téléchargée vide", transient=True)
        return GeneratedImage(image.content, "jpg", self.provider, self.model), credits

    def generate(self, prompt: str, caller: Caller) -> GeneratedImage:
        """Génère l'image et la télécharge avant l'expiration de l'URL signée.

        Args:
            prompt: Prompt visuel reformulé.
            caller: Contexte de journalisation.

        Returns:
            L'image JPEG.
        """
        ctx = CallContext(ApiCall.Step.IMAGE, self.provider, self.model, caller.dream_id, caller.user_id)
        image, _ = resilient_call(
            ctx,
            lambda: self._call(prompt),
            estimated_units=ESTIMATED_CREDITS,
            billed_units=lambda r: r[1],
            max_attempts=2,
        )
        return image
