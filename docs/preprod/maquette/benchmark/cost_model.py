"""Modèle de coût : 10 rêves/jour → coût par rêve, jour, mois, an, par scénario.

Usage : python benchmark/cost_model.py  → affiche le tableau et écrit
benchmark/results/cost_<horodatage>.csv
"""

from __future__ import annotations

import csv
import math
from datetime import UTC, datetime
from pathlib import Path

from catalog import CATEGORIES, Hypotheses, Provider, cost_per_dream, load_catalog, load_hypotheses

RESULTS = Path(__file__).resolve().parent / "results"


def scenario_costs(providers: dict[str, Provider], h: Hypotheses) -> list[dict[str, object]]:
    """Calcule le détail par étape et les totaux de chaque scénario."""
    rows: list[dict[str, object]] = []
    for sc in h.scenarios:
        detail: dict[str, float] = {}
        for cat in CATEGORIES:
            key = sc.get(cat, "")
            detail[cat] = cost_per_dream(providers[key], h) if key else 0.0
        per_dream = sum(detail.values())
        estimated = any(providers[sc[c]].status == "ESTIMÉ" for c in CATEGORIES if sc.get(c))
        per_day = per_dream * h["H0"]
        rows.append(
            {
                "scenario": f"{sc['id']} {sc['name']}",
                **{f"{c}_usd": round(v, 6) for c, v in detail.items()},
                "per_dream_usd": round(per_dream, 5),
                "per_day_usd": round(per_day, 4),
                "per_month_usd": round(per_day * h["H9"], 2),
                "per_year_usd": round(per_day * 365, 2),
                "beta_month_usd": round(per_dream * h["H10"] * h["H11"] * h["H9"], 2),
                "contains_estimate": estimated,
            }
        )
    return rows


def main() -> None:
    """Affiche et exporte le modèle de coût."""
    consulted, plist = load_catalog()
    h = load_hypotheses()
    providers = {p.key: p for p in plist}
    rows = scenario_costs(providers, h)
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"cost_{stamp}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Prix consultés le {consulted} · {int(h['H0'])} rêves/jour")
    print(f"{'Scénario':34} {'$/rêve':>9} {'$/jour':>8} {'$/mois':>8} {'$/an':>8}")
    for r in rows:
        flag = " (ESTIMÉ)" if r["contains_estimate"] else ""
        print(
            f"{r['scenario']:34} {r['per_dream_usd']:>9.4f} {r['per_day_usd']:>8.3f} "
            f"{r['per_month_usd']:>8.2f} {r['per_year_usd']:>8.2f}{flag}"
        )
    print("\nCoût par rêve et par fournisseur (catégorie seule) :")
    for p in plist:
        c = cost_per_dream(p, h)
        shown = "NON PUBLIÉ" if math.isnan(c) else f"{c:.5f} $"
        print(f"  {p.category:8} {p.vendor[:28]:28} {p.model[:34]:34} {shown}  [{p.status}]")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
