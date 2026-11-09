"""Rapport du test de charge : paliers, latences, erreurs, file et débit du worker.

Sources (toutes produites par le test, aucune valeur saisie à la main) :
- ``locust_stats_history.csv`` (Locust, ``--csv-full-history``) ;
- ``file.csv`` (``scripts/sample_queue.py``) ;
- la table des tâches ``django-tasks-db`` (dates de mise en file, début et fin).

Usage : ``uv run python scripts/load_report.py load-results --stage-s 90 --workers 1``.
"""

import argparse
import csv
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

STAGES = ((5, "5 utilisateurs"), (20, "20 utilisateurs"), (50, "50 utilisateurs"))


def pct(values: list[float], p: float) -> float | None:
    """Percentile par rang le plus proche."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def ms(seconds: list[float], p: float) -> float | None:
    """Percentile d'une liste de durées en secondes, converti en millisecondes."""
    value = pct(seconds, p)
    return None if value is None else value * 1000


def fmt(value: float | None, unit: str = "ms") -> str:
    """Nombre formaté à la française, ou tiret."""
    if value is None:
        return "—"
    return f"{value:,.0f} {unit}".replace(",", " ")


def stage_of(elapsed: float, stage_s: int) -> int:
    """Indice du palier pour un instant donné."""
    return min(int(elapsed // stage_s), len(STAGES) - 1)


def locust_by_stage(path: Path, stage_s: int) -> dict[int, dict[str, dict[str, float]]]:
    """Dernière ligne cumulée de chaque palier, par requête (les cumuls sont différenciés)."""
    rows = list(csv.DictReader(path.open()))
    if not rows:
        return {}
    t0 = int(rows[0]["Timestamp"])
    snapshots: dict[int, dict[str, dict[str, str]]] = {}
    for row in rows:
        stage = stage_of(int(row["Timestamp"]) - t0, stage_s)
        snapshots.setdefault(stage, {})[row["Name"]] = row
    result: dict[int, dict[str, dict[str, float]]] = {}
    previous: dict[str, dict[str, str]] = {}
    for stage in sorted(snapshots):
        result[stage] = {}
        for name, row in snapshots[stage].items():
            before = previous.get(name, {})
            count = int(row["Total Request Count"]) - int(before.get("Total Request Count", 0) or 0)
            failures = int(row["Total Failure Count"]) - int(before.get("Total Failure Count", 0) or 0)
            result[stage][name] = {
                "count": count,
                "failures": failures,
                "p50": float(row["50%"] or 0),
                "p95": float(row["95%"] or 0),
                "rps": float(row["Requests/s"] or 0),
            }
        previous.update(snapshots[stage])
    return result


def main() -> None:
    """Écrit ``rapport.md`` dans le dossier de résultats."""
    import django

    django.setup()
    from django_tasks_db.models import DBTaskResult

    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--stage-s", type=int, default=90)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--fake-latency-ms", type=int, default=0)
    parser.add_argument("--runner", default="")
    args = parser.parse_args()
    folder = Path(args.results)

    per_stage = locust_by_stage(folder / "locust_stats_history.csv", args.stage_s)
    queue = list(csv.DictReader((folder / "file.csv").open())) if (folder / "file.csv").exists() else []
    tasks = [
        (enqueued, started, finished, status)
        for enqueued, started, finished, status in DBTaskResult.objects.filter(
            task_path="dreams.tasks.process_dream", finished_at__isnull=False, started_at__isnull=False
        ).values_list("enqueued_at", "started_at", "finished_at", "status")
        if enqueued and started and finished
    ]
    waits = [(started - enqueued).total_seconds() for enqueued, started, _, _ in tasks]
    runs = [(finished - started).total_seconds() for _, started, finished, _ in tasks]
    totals = [(finished - enqueued).total_seconds() for enqueued, _, finished, _ in tasks]
    failed = sum(1 for *_, status in tasks if status == "FAILED")
    span = (max(t[2] for t in tasks) - min(t[1] for t in tasks)).total_seconds() if tasks else 0

    lines = [
        "# Test de charge — résultats",
        "",
        f"Paliers de {args.stage_s} s : 5 → 20 → 50 utilisateurs virtuels. Adapters **fake** "
        f"(latence simulée {args.fake_latency_ms} ms par appel fournisseur, 4 appels par rêve). "
        f"{args.workers} worker(s) `db_worker`, gunicorn 2 processus, PostgreSQL 17. "
        f"Machine : {args.runner or 'non précisée'}.",
        "",
        "## Requêtes HTTP par palier",
        "",
        "| Palier | Requête | Nombre | Échecs | p50 | p95 | Req/s |",
        "|---|---|---|---|---|---|---|",
    ]
    for stage, (_, label) in enumerate(STAGES):
        for name, row in sorted(per_stage.get(stage, {}).items()):
            if name == "Aggregated":
                continue
            lines.append(
                f"| {label} | {name} | {row['count']} | {row['failures']} | {fmt(row['p50'])} | {fmt(row['p95'])} "
                f"| {row['rps']:.1f} |"
            )
        agg = per_stage.get(stage, {}).get("Aggregated")
        if agg:
            rate = 100 * agg["failures"] / agg["count"] if agg["count"] else 0
            lines.append(
                f"| **{label}** | **toutes** | **{agg['count']}** | **{agg['failures']} ({rate:.1f} %)** "
                f"| **{fmt(agg['p50'])}** | **{fmt(agg['p95'])}** | **{agg['rps']:.1f}** |"
            )
    lines += ["", "## File de tâches et worker", ""]
    if queue:
        for stage, (_, label) in enumerate(STAGES):
            samples = [r for r in queue if stage_of(float(r["elapsed_s"]), args.stage_s) == stage]
            if samples:
                lines.append(
                    f"- {label} : file max **{max(int(r['ready']) for r in samples)}** tâches, "
                    f"attente max {max(int(r['oldest_wait_s']) for r in samples)} s."
                )
    lines += [
        f"- Rêves traités : **{len(tasks)}** ({failed} en échec), débit mesuré "
        f"**{(len(tasks) / span * 60) if span else 0:.1f} rêves/min**.",
        f"- Attente en file : p50 {fmt(ms(waits, 50))}, p95 {fmt(ms(waits, 95))}.",
        f"- Traitement par le worker : p50 {fmt(ms(runs, 50))}, p95 {fmt(ms(runs, 95))}.",
        f"- Mise en file → terminé : p50 {fmt(ms(totals, 50))}, p95 {fmt(ms(totals, 95))}.",
        "",
    ]
    (folder / "rapport.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
