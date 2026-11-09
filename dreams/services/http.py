"""Client résilient commun à tous les appels fournisseurs.

Pour chaque appel : coupe-circuit budgétaire vérifié **avant** chaque tentative, délai
imposé par l'adapter, retries exponentiels bornés sur les seules erreurs passagères
(408, 429, 5xx, délai dépassé ; jamais les autres 4xx), et une ligne ``ApiCall`` par
tentative, réussie ou non, avec son coût estimé.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import structlog
from django.conf import settings
from django.utils.crypto import salted_hmac
from tenacity import RetryCallState, Retrying, retry_if_exception, stop_after_attempt

from dreams.models import ApiCall
from dreams.services import budget, pricing
from dreams.services.errors import BudgetExceededError, ProviderError, ProviderTimeoutError, SafetyRejectionError

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CallContext:
    """Ce qui identifie un appel dans le journal, sans aucun contenu.

    Attributes:
        step: Étape du pipeline (valeur de ``ApiCall.Step``).
        provider: Fournisseur.
        model: Modèle appelé.
        dream_id: Rêve concerné, s'il existe.
        user_id: Utilisateur, pseudonymisé avant écriture.
    """

    step: str
    provider: str
    model: str
    dream_id: UUID | None = None
    user_id: int | None = None


def pseudonymize(user_id: int | None) -> str:
    """Pseudonyme stable d'un utilisateur (HMAC-SHA256 dérivé de ``SECRET_KEY``).

    Args:
        user_id: Identifiant, ou ``None``.

    Returns:
        64 caractères hexadécimaux, ou une chaîne vide.
    """
    if user_id is None:
        return ""
    return salted_hmac("dreams.apicall.user", str(user_id), algorithm="sha256").hexdigest()


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


def _wait(state: RetryCallState) -> float:
    """Backoff exponentiel (base * 2^n), borné, allongé au ``Retry-After`` du fournisseur."""
    base = float(settings.AI_RETRY_BASE_SECONDS)
    delay: float = min(base * 2.0 ** (state.attempt_number - 1), 30.0)
    exc = state.outcome.exception() if state.outcome else None
    if isinstance(exc, ProviderError) and exc.retry_after:
        delay = max(delay, min(float(exc.retry_after), 30.0))
    return delay


def _outcome(exc: BaseException) -> str:
    if isinstance(exc, ProviderTimeoutError):
        return ApiCall.Outcome.TIMEOUT
    if isinstance(exc, SafetyRejectionError):
        return ApiCall.Outcome.REJECTED
    return ApiCall.Outcome.ERROR


def resilient_call[T](
    ctx: CallContext,
    fn: Callable[[], T],
    *,
    estimated_units: Decimal,
    billed_units: Callable[[T], Decimal] | None = None,
    max_attempts: int | None = None,
) -> T:
    """Exécute un appel fournisseur avec budget, retries et journalisation.

    Args:
        ctx: Identification de l'appel.
        fn: Appel au fournisseur, déjà muni de son délai ; lève des :class:`ProviderError`.
        estimated_units: Unités facturées attendues, pour le contrôle de budget avant l'appel
            et pour le coût d'un délai dépassé (la requête a pu être traitée et facturée).
        billed_units: Extrait les unités réellement facturées de la réponse ; à défaut,
            l'estimation est retenue.
        max_attempts: Nombre total de tentatives (``AI_MAX_ATTEMPTS`` par défaut).

    Returns:
        Le résultat de ``fn``.

    Raises:
        BudgetExceededError: Si le coupe-circuit bloque l'appel ; aucun fournisseur n'est contacté.
        ProviderError: Dernière erreur, une fois les tentatives épuisées ou si elle n'est pas passagère.
    """
    unit = pricing.price_for(ctx.provider, ctx.model).unit
    estimated_cost = pricing.cost_usd(ctx.provider, ctx.model, estimated_units)
    pseudonym = pseudonymize(ctx.user_id)
    attempts = max_attempts or settings.AI_MAX_ATTEMPTS

    def journal(attempt: int, outcome: str, started: float, **fields: object) -> ApiCall:
        call = ApiCall.objects.create(
            dream_id=ctx.dream_id,
            user_pseudonym=pseudonym,
            step=ctx.step,
            provider=ctx.provider,
            model=ctx.model,
            outcome=outcome,
            attempt=attempt,
            unit=unit,
            latency_ms=int((time.monotonic() - started) * 1000),
            **fields,
        )
        log.info(
            "api_call",
            step=ctx.step,
            provider=ctx.provider,
            model=ctx.model,
            outcome=outcome,
            attempt=attempt,
            latency_ms=call.latency_ms,
            http_status=call.http_status,
            cost_usd=str(call.cost_usd),
            dream_id=str(ctx.dream_id) if ctx.dream_id else None,
        )
        return call

    def attempt_once(state_attempt: int) -> T:
        started = time.monotonic()
        try:
            budget.ensure_budget(estimated_cost)
        except BudgetExceededError:
            journal(state_attempt, ApiCall.Outcome.BLOCKED, started, error_type="BudgetExceededError")
            raise
        try:
            result = fn()
        except ProviderError as exc:
            # Un délai dépassé est compté comme facturé : la requête a pu aboutir chez le fournisseur.
            timed_out = isinstance(exc, ProviderTimeoutError)
            journal(
                state_attempt,
                _outcome(exc),
                started,
                http_status=exc.status,
                error_type=type(exc).__name__,
                billed_units=estimated_units if timed_out else Decimal(0),
                cost_usd=estimated_cost if timed_out else Decimal(0),
            )
            raise
        units = billed_units(result) if billed_units else estimated_units
        journal(
            state_attempt,
            ApiCall.Outcome.OK,
            started,
            http_status=200,
            billed_units=units,
            cost_usd=pricing.cost_usd(ctx.provider, ctx.model, units),
        )
        return result

    retrying = Retrying(
        stop=stop_after_attempt(attempts),
        wait=_wait,
        retry=retry_if_exception(_is_transient),
        reraise=True,
        sleep=time.sleep,
    )
    for attempt in retrying:
        with attempt:
            return attempt_once(attempt.retry_state.attempt_number)
    raise AssertionError("inatteignable : Retrying relance la dernière erreur")  # pragma: no cover
