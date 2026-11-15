"""Génère les tableaux de la section 4 du dossier de cadrage depuis le catalogue.

Usage : python benchmark/build_report.py → docs/cadrage/_gen/benchmark_tables.md
Les chiffres ne sont jamais recopiés à la main dans le dossier : ils viennent d'ici.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from catalog import cost_per_dream, load_catalog, load_hypotheses
from cost_model import scenario_costs

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "cadrage" / "_gen" / "benchmark_tables.md"
NOT_MEASURED = "NON MESURÉ — mock"
LABELS = {
    "STT": "STT",
    "LLM": "LLM",
    "T2I": "Image",
    "VIDEO": "Vidéo",
    "TTS": "TTS",
    "AMBIANCE": "Son",
}


def fr(x: float, digits: int = 4) -> str:
    """Nombre au format français."""
    return f"{x:.{digits}f}".replace(".", ",")


def latest_live() -> dict[str, dict[str, str]]:
    """Dernier résumé de mesures live, indexé par fournisseur."""
    rows: dict[str, dict[str, str]] = {}
    for pattern in ("summary_local_*.csv", "summary_live_*.csv"):
        files = sorted((HERE / "results").glob(pattern))
        if files:
            with files[-1].open(encoding="utf-8") as fh:
                rows |= {r["provider"]: r | {"source": files[-1].name} for r in csv.DictReader(fh)}
    return rows


def short(text: str, n: int = 38) -> str:
    """Tronque un texte de cellule."""
    text = str(text) or "non trouvé"
    return text if len(text) <= n else text[: n - 1] + "…"


def main() -> None:
    """Écrit les tableaux Markdown."""
    consulted, providers = load_catalog()
    h = load_hypotheses()
    live = latest_live()
    lines = [
        "<!-- Généré par benchmark/build_report.py — ne pas éditer -->",
        "",
        f"Prix et clauses consultés le {consulted}. Coût par rêve selon les hypothèses H1–H8 "
        "(annexe `benchmark.xlsx`, onglet Hypothèses).",
        "",
        "| Cat. | Fournisseur — modèle | $/rêve | p95 (s) | Quota | UE · DPA | Entraînement |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in providers:
        c = cost_per_dream(p, h)
        cost = "NP" if math.isnan(c) else fr(c) + (" ᴱ" if p.status == "ESTIMÉ" else "")
        m = live.get(p.key)
        p95 = (
            fr(float(m["p95_total_s"]), 2)
            if m
            else (
                "local"
                if p.extra.get("hq") == "Interne"
                else "auto-hébergé"
                if math.isnan(c)
                else "n. m."
            )
        )
        lines.append(
            f"| {LABELS[p.category]} | {p.vendor} — {p.model} | {cost} | {p95} | "
            f"{short(p.extra.get('rate_limit', '') or '—', 14)} | "
            f"{'oui' if p.eu else 'non'} · {short(p.extra.get('dpa', ''), 12)} | "
            f"{short(p.extra.get('training', ''), 34)} |"
        )
    wer_files = sorted((HERE / "results").glob("wer_*.csv"))
    # Dernière mesure de WER de chaque fournisseur (une campagne live ne doit pas effacer la locale).
    wer: dict[str, dict[str, str]] = {}
    for wer_file in wer_files:
        with wer_file.open(encoding="utf-8") as fh:
            wer.update({r["provider"]: r for r in csv.DictReader(fh)})
    for key, m in live.items():
        extra = ""
        if key in wer:
            extra = f", WER {fr(float(wer[key]['wer']) * 100, 1)} % ({wer[key]['source']})"
        lines += [
            "",
            f"**Mesure réelle** ({m['mode']}) — `{key}` : {m['calls']} appels, p50 "
            f"{fr(float(m['p50_total_s']), 2)} s, p95 {fr(float(m['p95_total_s']), 2)} s, "
            f"premier segment p50 {fr(float(m['p50_ttfb_s']), 2)} s{extra} ; fichier "
            f"`{m.get('source', 'summary')}`.",
        ]
    lines += [
        "",
        "ᴱ prix ESTIMÉ (non publié en clair, méthode dans le classeur) · NP : non publié "
        "(auto-hébergé, coût d'infrastructure) · *n. m.* = NON MESURÉ : pas de clé pour ce "
        "fournisseur, la colonne reste vide de chiffre. Latence : p95 de la dernière campagne "
        "réelle (live ou locale) de chaque fournisseur.",
        "",
        "| Scénario | $/rêve | $/jour | $/mois | $/an | $/mois bêta | ≤ 0,05 $ (CS-03) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in scenario_costs({p.key: p for p in providers}, h):
        flag = " ᴱ" if r["contains_estimate"] else ""
        ok = "oui" if float(r["per_dream_usd"]) <= 0.05 else "non"  # type: ignore[arg-type]
        lines.append(
            f"| {r['scenario']}{flag} | {fr(float(r['per_dream_usd']))} | "  # type: ignore[arg-type]
            f"{fr(float(r['per_day_usd']), 3)} | {fr(float(r['per_month_usd']), 2)} | "  # type: ignore[arg-type]
            f"{fr(float(r['per_year_usd']), 2)} | {fr(float(r['beta_month_usd']), 2)} | "  # type: ignore[arg-type]
            f"{ok} |"
        )
    lines += [
        "",
        "ᴱ contient au moins un prix ESTIMÉ (FLUX.2, non publié en clair). Mois = 30 jours (H9), "
        "an = 365 jours. Bêta : 30 utilisateurs × 0,5 rêve/jour (H10, H11 ESTIMÉ) = 15 rêves/jour.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
