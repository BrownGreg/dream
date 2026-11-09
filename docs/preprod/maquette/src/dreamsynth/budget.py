"""Garde budgétaire des appels API (ADR-007, ENF-06).

Alerte à 80 % du budget mensuel, coupe-circuit de la génération d'image à 100 % ; les
autres étapes (transcription, émotion, ambiance) ne sont jamais bloquées.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BudgetState(StrEnum):
    """État du budget du mois en cours."""

    OK = "ok"
    ALERT = "alert"
    CUT = "cut"


@dataclass
class BudgetGuard:
    """Cumule le coût des appels du mois et décide si l'image reste autorisée."""

    monthly_limit_usd: float = 25.0
    alert_ratio: float = 0.8
    spent_usd: float = 0.0
    alerts: list[str] = field(default_factory=list)

    @property
    def state(self) -> BudgetState:
        """État courant selon la dépense cumulée."""
        if self.spent_usd >= self.monthly_limit_usd:
            return BudgetState.CUT
        if self.spent_usd >= self.alert_ratio * self.monthly_limit_usd:
            return BudgetState.ALERT
        return BudgetState.OK

    def record(self, cost_usd: float) -> BudgetState:
        """Ajoute le coût d'un appel ; émet une alerte à chaque changement d'état."""
        if cost_usd < 0:
            raise ValueError("coût négatif")
        before = self.state
        self.spent_usd += cost_usd
        after = self.state
        if after is not before:
            self.alerts.append(
                f"budget {after.value} : {self.spent_usd:.2f} $ / {self.monthly_limit_usd:.2f} $"
            )
        return after

    def image_allowed(self) -> bool:
        """Faux une fois le coupe-circuit déclenché."""
        return self.state is not BudgetState.CUT

    def reset_month(self) -> None:
        """Remise à zéro au 1er du mois."""
        self.spent_usd = 0.0
