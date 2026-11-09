"""Rapport du test de charge : paliers, latences, erreurs, file et débit du worker.

Sources (toutes produites par le test, aucune valeur saisie à la main) :
- ``requests.csv`` : chaque requête Locust avec son instant (``tests/load/locustfile.py``),
  pour des percentiles exacts par palier (l'historique Locust est cumulatif) ;
- ``file.csv`` (``scripts/sample_queue.py``) ;
- la table des tâches ``django-tasks-db`` (dates de mise en file, début et fin).

Usage : ``uv run python scripts/load_report.py load-results --stage-s 90 --workers 1``.
"""

import argparse
import csv
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

STAGES = ("5 utilisateurs", "20 utilisateurs", "50 utilisateurs")
PIPELINE = "pipeline : bout en bout"


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


def http_table(path: Path, stage_s: int) -> list[str]:
    """Tableau par palier et par requête : nombre, échecs, p50, p95, débit moyen."""
    groups: dict[tuple[int, str], list[tuple[float, int]]] = defaultdict(list)
    for row in csv.DictReader(path.open()):
        stage = stage_of(float(row["elapsed_s"]), stage_s)
        groups[(stage, row["name"])].append((float(row["response_ms"]), int(row["failed"])))
    lines = [
        "| Palier | Requête | Nombre | Échecs | p50 | p95 | Req/s (moyenne) |",
        "|---|---|---|---|---|---|---|",
    ]
    for stage, label in enumerate(STAGES):
        pages: list[tuple[float, int]] = []
        for (s, name), items in sorted(groups.items()):
            if s != stage:
                continue
            times = [t for t, _ in items]
            failures = sum(f for _, f in items)
            if name != PIPELINE:
                pages.extend(items)
            lines.append(
                f"| {label} | {name} | {len(items)} | {failures} | {fmt(pct(times, 50))} | {fmt(pct(times, 95))} "
                f"| {len(items) / stage_s:.2f} |"
            )
        if pages:
            times = [t for t, _ in pages]
            failures = sum(f for _, f in pages)
            lines.append(
                f"| **{label}** | **toutes les requêtes HTTP** | **{len(pages)}** "
                f"| **{failures} ({100 * failures / len(pages):.1f} %)** | **{fmt(pct(times, 50))}** "
                f"| **{fmt(pct(times, 95))}** | **{len(pages) / stage_s:.2f}** |"
            )
    return lines


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
        f"Paliers de {args.stage_s} s : 5 → 20 → 50 utilisateurs virtuels (attente de 2 à 5 s entre deux actions). "
        f"Adapters **fake** : latence simulée de {args.fake_latency_ms} ms par appel fournisseur, 4 appels par rêve. "
        f"{args.workers} processus `db_worker`, gunicorn 2 processus synchrones, PostgreSQL 17. "
        f"Machine : {args.runner or 'non précisée'}.",
        "",
        "## Requêtes HTTP par palier",
        "",
        "Percentiles calculés sur les requêtes du palier seulement. « pipeline : bout en bout » = de l'envoi "
        "à la page terminée, vu par l'utilisateur (polling toutes les 2 s), compté dans le palier où il se termine.",
        "",
        *http_table(folder / "requests.csv", args.stage_s),
        "",
        "## File de tâches et worker",
        "",
    ]
    for stage, label in enumerate(STAGES):
        samples = [r for r in queue if stage_of(float(r["elapsed_s"]), args.stage_s) == stage]
        if samples:
            lines.append(
                f"- {label} : file max **{max(int(r['ready']) for r in samples)}** tâches en attente, "
                f"plus longue attente **{max(int(r['oldest_wait_s']) for r in samples)} s**."
            )
    lines += [
        f"- Rêves traités : **{len(tasks)}** ({failed} en échec), débit **{(len(tasks) / span * 60) if span else 0:.1f}"
        " rêves/min**.",
        f"- Attente en file : p50 {fmt(ms(waits, 50))}, p95 {fmt(ms(waits, 95))}.",
        f"- Traitement par le worker : p50 {fmt(ms(runs, 50))}, p95 {fmt(ms(runs, 95))}.",
        f"- Mise en file → terminé : p50 {fmt(ms(totals, 50))}, p95 {fmt(ms(totals, 95))}.",
        "",
    ]
    (folder / "rapport.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
