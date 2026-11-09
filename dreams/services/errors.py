"""Erreurs du domaine IA, indépendantes des SDK fournisseurs.

Chaque adapter traduit les exceptions de son SDK vers ces classes ; le client résilient
décide seul de ce qui se rejoue.
"""

from __future__ import annotations

from datetime import datetime


class AIServiceError(Exception):
    """Base des erreurs de la couche IA ; ``code`` est stable et affichable (``Dream.error_code``)."""

    code = "ai_error"


class ProviderError(AIServiceError):
    """Échec d'un appel fournisseur.

    Attributes:
        status: Code HTTP renvoyé, s'il existe.
        transient: ``True`` si un nouvel essai peut réussir (429, 5xx, réseau).
        retry_after: Délai demandé par le fournisseur avant de réessayer, en secondes.
    """

    code = "provider_error"

    def __init__(
        self, message: str, *, status: int | None = None, transient: bool = False, retry_after: float | None = None
    ) -> None:
        """Construit l'erreur.

        Args:
            message: Description technique, sans contenu de rêve.
            status: Code HTTP éventuel.
            transient: Erreur passagère, à rejouer.
            retry_after: Délai imposé par le fournisseur (en-tête ``Retry-After``).
        """
        super().__init__(message)
        self.status = status
        self.transient = transient
        self.retry_after = retry_after

    @classmethod
    def from_status(cls, status: int, message: str = "", retry_after: float | None = None) -> ProviderError:
        """Classe une réponse HTTP : seuls 408, 429 et 5xx sont passagers ; jamais les autres 4xx.

        Args:
            status: Code HTTP.
            message: Description technique.
            retry_after: Délai ``Retry-After`` éventuel.

        Returns:
            L'erreur, marquée passagère ou non.
        """
        transient = status in (408, 429) or status >= 500
        return cls(message or f"HTTP {status}", status=status, transient=transient, retry_after=retry_after)


class ProviderTimeoutError(ProviderError):
    """Délai dépassé ou coupure réseau : passager par nature."""

    code = "provider_timeout"

    def __init__(self, message: str = "délai dépassé") -> None:
        """Construit l'erreur passagère."""
        super().__init__(message, transient=True)


class SafetyRejectionError(ProviderError):
    """Le filtre de sécurité du fournisseur a refusé la demande : à reformuler, pas à rejouer."""

    code = "safety_rejected"

    def __init__(self, message: str = "refus du filtre de sécurité") -> None:
        """Construit l'erreur non passagère."""
        super().__init__(message, transient=False)


class BudgetExceededError(AIServiceError):
    """Le coupe-circuit budgétaire (ADR-009) bloque tout nouvel appel payant."""

    code = "budget_exceeded"


class QuotaExceededError(AIServiceError):
    """L'utilisateur a atteint son quota quotidien de rêves.

    Attributes:
        resets_at: Date de remise à zéro du quota.
    """

    code = "quota_exceeded"

    def __init__(self, resets_at: datetime) -> None:
        """Construit l'erreur avec la date de remise à zéro."""
        super().__init__(f"quota atteint jusqu'à {resets_at.isoformat()}")
        self.resets_at = resets_at
