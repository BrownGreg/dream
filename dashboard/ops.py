"""Indicateurs d'exploitation pour la page ``/ops`` (staff) et ``/health``.

Tout est calculé depuis nos tables (``ApiCall``, ``Dream``, file ``django-tasks-db``) :
les chiffres du rapport viennent de mesures, pas d'hypothèses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from dreams.models import ApiCall, Dream, StoredFile
from dreams.services import budget


def percentile(values: list[int], p: float) -> int | None:
    """Percentile par rang le plus proche.

    Args:
        values: Mesures.
        p: Percentile entre 0 et 100.

    Returns:
        La valeur, ou ``None`` sans mesure.
    """
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


@dataclass(frozen=True)
class QueueState:
    """État de la file des tâches.

    Attributes:
        ready: Tâches en attente d'un worker.
        running: Tâches en cours.
        failed_24h: Tâches en échec sur 24 h.
        oldest_wait_s: Attente de la plus ancienne tâche prête (secondes).
        worker_ok: Faux si une tâche attend depuis plus de ``WORKER_STALE_AFTER_S``.
    """

    ready: int
    running: int
    failed_24h: int
    oldest_wait_s: int
    worker_ok: bool


def queue_state() -> QueueState:
    """Mesure la file ``django-tasks-db``.

    Returns:
        L'état courant de la file.
    """
    now = timezone.now()
    tasks = DBTaskResult.objects.all()
    # `ready()` du paquet : une tâche sans délai est stockée avec `run_after` à la date maximale
    # (et non « maintenant ») ; un filtre `run_after <= now` les ignorerait toutes (incident #10).
    first = DBTaskResult.objects.ready().order_by("enqueued_at").values_list("enqueued_at", flat=True).first()
    wait = int((now - first).total_seconds()) if first else 0
    return QueueState(
        ready=tasks.filter(status="READY").count(),
        running=tasks.filter(status="RUNNING").count(),
        failed_24h=tasks.filter(status="FAILED", finished_at__gte=now - timedelta(hours=24)).count(),
        oldest_wait_s=wait,
        worker_ok=wait <= settings.WORKER_STALE_AFTER_S,
    )


def provider_metrics(days: int = 7) -> list[dict[str, Any]]:
    """Latence p50/p95, volume, taux d'erreur et coût par étape et fournisseur.

    Args:
        days: Fenêtre d'analyse.

    Returns:
        Une ligne par couple (étape, fournisseur, modèle).
    """
    since = timezone.now() - timedelta(days=days)
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for call in ApiCall.objects.filter(created_at__gte=since).values(
        "step", "provider", "model", "outcome", "latency_ms", "cost_usd"
    ):
        key = (call["step"], call["provider"], call["model"])
        row = rows.setdefault(key, {"latencies": [], "calls": 0, "errors": 0, "cost": Decimal(0)})
        row["calls"] += 1
        row["cost"] += call["cost_usd"]
        if call["outcome"] == ApiCall.Outcome.OK:
            row["latencies"].append(call["latency_ms"])
        elif call["outcome"] != ApiCall.Outcome.BLOCKED:
            row["errors"] += 1
    return [
        {
            "step": step,
            "provider": provider,
            "model": model,
            "calls": row["calls"],
            "p50_ms": percentile(row["latencies"], 50),
            "p95_ms": percentile(row["latencies"], 95),
            "error_rate": round(100 * row["errors"] / row["calls"], 1),
            "cost_usd": row["cost"],
        }
        for (step, provider, model), row in sorted(rows.items())
    ]


def overview(days: int = 14) -> dict[str, Any]:
    """Synthèse pour la page ``/ops``.

    Args:
        days: Fenêtre des séries quotidiennes.

    Returns:
        Budget, coût par rêve, rêves par jour et par statut, file, fournisseurs, stockage.
    """
    since = timezone.now() - timedelta(days=days)
    per_dream = (
        ApiCall.objects.exclude(dream__isnull=True)
        .values("dream")
        .annotate(total=Sum("cost_usd"))
        .values_list("total", flat=True)
    )
    costs = [c for c in per_dream if c is not None]
    end_to_end = [
        int((d.finished_at - d.created_at).total_seconds() * 1000)
        for d in Dream.objects.filter(status=Dream.Status.DONE, created_at__gte=since, finished_at__isnull=False).only(
            "created_at", "finished_at"
        )
        if d.finished_at
    ]
    return {
        "budget": budget.budget_status(),
        "cost_per_dream_usd": (sum(costs, Decimal(0)) / len(costs)).quantize(Decimal("0.000001")) if costs else None,
        "dreams_with_cost": len(costs),
        "dreams_per_day": list(
            Dream.objects.filter(created_at__gte=since)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(n=Count("id"))
            .order_by("day")
        ),
        "status_counts": dict(Dream.objects.values_list("status").annotate(n=Count("id")).order_by()),
        "end_to_end_p50_ms": percentile(end_to_end, 50),
        "end_to_end_p95_ms": percentile(end_to_end, 95),
        "queue": queue_state(),
        "providers": provider_metrics(),
        "storage_bytes": StoredFile.objects.aggregate(total=Sum("size"))["total"] or 0,
    }
