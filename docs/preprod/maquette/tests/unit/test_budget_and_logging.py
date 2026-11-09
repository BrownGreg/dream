"""Coupe-circuit budgétaire (ENF-06) et journaux sans contenu de rêve (ENF-10)."""

from __future__ import annotations

import logging

import pytest

from dreamsynth.budget import BudgetGuard, BudgetState
from dreamsynth.safe_logging import REDACTED, get_logger, pseudonymize


def test_budget_alerts_at_80_percent_and_cuts_images_at_100() -> None:  # ENF-06
    guard = BudgetGuard(monthly_limit_usd=15.0)
    assert guard.record(11.0) is BudgetState.OK and guard.image_allowed()
    assert guard.record(1.5) is BudgetState.ALERT and guard.image_allowed()
    assert guard.record(3.0) is BudgetState.CUT and not guard.image_allowed()
    assert len(guard.alerts) == 2  # une alerte par changement d'état
    guard.reset_month()
    assert guard.image_allowed()


def test_budget_rejects_negative_cost() -> None:
    with pytest.raises(ValueError):
        BudgetGuard().record(-1)


def test_logs_never_contain_dream_content(caplog: pytest.LogCaptureFixture) -> None:  # ENF-10
    logger = get_logger("dreamsynth.test")
    with caplog.at_level(logging.INFO, logger="dreamsynth.test"):
        logger.info("étape terminée", extra={"step": "stt", "text": "je tombais dans le vide"})
    record = caplog.records[-1]
    assert record.text == REDACTED  # type: ignore[attr-defined]
    assert record.step == "stt"  # type: ignore[attr-defined]
    assert "vide" not in caplog.text


def test_pseudonym_is_stable_and_not_the_id() -> None:
    a = pseudonymize("user-42", b"secret")
    assert a == pseudonymize("user-42", b"secret") and "user-42" not in a
    assert a != pseudonymize("user-42", b"autre-cle")
