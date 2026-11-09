"""Valide le backlog et génère les artefacts dérivés de `docs/backlog/stories.toml`.

Sorties :
    docs/cadrage/_gen/story_map.md      tableau MoSCoW par release
    docs/diagrams/story_map.svg         carte activités → tâches → stories
    tests/features/<activité>.feature   critères d'acceptation Gherkin (pytest-bdd)
    docs/specs/_gen/requirements.md     tableau des exigences EXF / ENF
    docs/annexes/tracabilite.csv        exigence → stories → tests → composants C4

Usage : python tools/backlog.py [--check]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import textwrap
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "backlog" / "stories.toml"
REQUIREMENTS = ROOT / "docs" / "backlog" / "requirements.toml"
ID_PATTERN = re.compile(r"\b(?:US|EXF|ENF)-\d{2}\b")
FIBONACCI = {0, 1, 2, 3, 5, 8, 13}
RELEASES = ["MVP", "R2", "R3"]
MOSCOW_COLORS = {"Must": "#C0392B", "Should": "#E67E22", "Could": "#2E86C1", "Won't": "#7F8C8D"}
KANO_LABELS = {
    "B": "basique",
    "P": "performance",
    "E": "enthousiasmante",
    "I": "indiff.",
    "R": "inverse",
}
FEATURE_FILES = {
    "A1": "raconter",
    "A2": "comprendre",
    "A3": "visualiser",
    "A4": "retrouver",
    "A5": "controler",
}


def load() -> dict[str, Any]:
    """Charge le fichier source du backlog."""
    with SOURCE.open("rb") as fh:
        return tomllib.load(fh)


def validate(data: dict[str, Any]) -> list[str]:
    """Retourne la liste des incohérences du backlog (vide si tout est valide)."""
    errors: list[str] = []
    activities = {a["id"] for a in data["activity"]}
    seen: set[str] = set()
    for s in data["story"]:
        sid = s["id"]
        if sid in seen:
            errors.append(f"{sid}: identifiant dupliqué")
        seen.add(sid)
        if s["activity"] not in activities:
            errors.append(f"{sid}: activité inconnue {s['activity']}")
        if s["points"] not in FIBONACCI:
            errors.append(f"{sid}: {s['points']} points n'est pas dans Fibonacci")
        if s["kano"] == "B" and s["moscow"] not in {"Must", "Should"}:
            errors.append(f"{sid}: basique (Kano) classé {s['moscow']}")
        if s["kano"] == "R" and s["moscow"] != "Won't":
            errors.append(f"{sid}: inverse (Kano) non exclu")
        if s["moscow"] != "Won't":
            if s["release"] not in RELEASES:
                errors.append(f"{sid}: release inconnue {s['release']}")
            if not s["gherkin"].strip():
                errors.append(f"{sid}: critères d'acceptation manquants")
    return errors


def short_title(story: dict[str, Any], width: int = 42) -> str:
    """Titre court dérivé du « je veux »."""
    want = str(story["want"])
    return textwrap.shorten(want[0].upper() + want[1:], width=width, placeholder="…")


def story_sentence(s: dict[str, Any]) -> str:
    """Phrase « En tant que… je veux… afin de… »."""
    return f"En tant que {s['role']}, je veux {s['want']} afin de {s['so_that']}."


def write_markdown(data: dict[str, Any]) -> Path:
    """Écrit le tableau MoSCoW par release (inclus dans le dossier de cadrage)."""
    lines = [
        "| Rel. | ID | Tâche | « Je veux… » | Kano | MoSCoW | Pts |",
        "|-----|------|--------------|----------------------------------------------------|"
        "----------|--------|----|",
    ]
    order = {r: i for i, r in enumerate([*RELEASES, "—"])}
    stories = sorted(data["story"], key=lambda s: (order[s["release"]], s["id"]))
    for s in stories:
        lines.append(
            f"| {s['release']} | {s['id']} | {s['task']} | "
            f"{short_title(s, 200)} | {KANO_LABELS[s['kano']]} | {s['moscow']} | "
            f"{s['points'] or '—'} |"
        )
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for s in data["story"]:
        totals[s["release"]] += s["points"]
        counts[s["release"]] += 1
    summary = " · ".join(f"**{r}** : {counts[r]} stories, {totals[r]} pts" for r in RELEASES)
    out = ROOT / "docs" / "cadrage" / "_gen" / "story_map.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "<!-- Généré par tools/backlog.py — ne pas éditer -->\n\n"
        + summary
        + "\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    return out


def write_features(data: dict[str, Any]) -> list[Path]:
    """Écrit un fichier .feature par activité, chaque scénario étiqueté par sa story."""
    by_activity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in data["story"]:
        if s["gherkin"].strip():
            by_activity[s["activity"]].append(s)
    paths: list[Path] = []
    for act in data["activity"]:
        stories = by_activity.get(act["id"], [])
        if not stories:
            continue
        out = [
            "# language: fr",
            "# Généré par tools/backlog.py depuis docs/backlog/stories.toml — ne pas éditer",
            f"Fonctionnalité: {act['name']}",
            "",
        ]
        for s in stories:
            out.append(f"  # {s['id']} — {story_sentence(s)}")
            block = textwrap.dedent(s["gherkin"]).strip("\n")
            for raw in block.splitlines():
                if raw.startswith("Scénario"):
                    out.append(f"  @{s['id']} @{s['release']}")
                out.append(f"  {raw}" if raw else "")
            out.append("")
        path = ROOT / "tests" / "features" / f"{FEATURE_FILES[act['id']]}.feature"
        path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        paths.append(path)
    return paths


Cells = dict[tuple[str, str, str], list[dict[str, Any]]]


def _layout(data: dict[str, Any]) -> tuple[list[tuple[str, str]], Cells, dict[str, int]]:
    """Colonnes (activité, tâche), cartes par cellule et profondeur maximale par release."""
    stories = [s for s in data["story"] if s["moscow"] != "Won't"]
    columns: list[tuple[str, str]] = []
    for act in data["activity"]:
        for s in stories:
            key = (act["id"], s["task"])
            if s["activity"] == act["id"] and key not in columns:
                columns.append(key)
    cells: Cells = defaultdict(list)
    for s in stories:
        cells[(s["activity"], s["task"], s["release"])].append(s)
    max_depth = {r: max(len(cells[(a, t, r)]) for a, t in columns) or 1 for r in RELEASES}
    return columns, cells, max_depth


def write_svg(data: dict[str, Any]) -> Path:
    """Dessine la User Story Map (colonnes = activités/tâches, lignes = releases)."""
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    plt.rcParams["svg.fonttype"] = "none"
    columns, cells, max_depth = _layout(data)
    col_w, card_h, gap = 1.0, 0.8, 0.08
    names = {a["id"]: a["name"] for a in data["activity"]}
    height = 1.6 + sum(max_depth[r] * (card_h + gap) + 0.35 for r in RELEASES)
    fig, ax = plt.subplots(figsize=(len(columns) * 1.05, height * 0.95))
    ax.set_xlim(0, len(columns) * col_w)
    ax.set_ylim(-height, 0.2)
    ax.axis("off")
    # bandeau activités
    start = 0
    for act in data["activity"]:
        n = sum(1 for a, _ in columns if a == act["id"])
        if not n:
            continue
        ax.add_patch(
            FancyBboxPatch(
                (start * col_w + 0.03, -0.42),
                n * col_w - 0.06,
                0.4,
                boxstyle="round,pad=0.01",
                fc="#4B3F72",
                ec="none",
            )
        )
        ax.text(
            (start + n / 2) * col_w,
            -0.22,
            names[act["id"]],
            ha="center",
            va="center",
            color="white",
            fontsize=7.5,
            fontweight="bold",
        )
        start += n
    for i, (_, task) in enumerate(columns):
        ax.add_patch(
            FancyBboxPatch(
                (i * col_w + 0.04, -0.92),
                col_w - 0.08,
                0.42,
                boxstyle="round,pad=0.01",
                fc="#D7D2E8",
                ec="none",
            )
        )
        ax.text(
            i * col_w + col_w / 2,
            -0.71,
            textwrap.fill(task, 16),
            ha="center",
            va="center",
            fontsize=6.5,
        )
    y = -1.05
    for r in RELEASES:
        ax.axhline(y, color="#999999", linewidth=0.7, linestyle="--")
        ax.text(0.01, y - 0.02, r, fontsize=7, fontweight="bold", va="top", color="#555555")
        for i, (a, t) in enumerate(columns):
            for k, s in enumerate(cells[(a, t, r)]):
                cy = y - 0.2 - k * (card_h + gap)
                ax.add_patch(
                    FancyBboxPatch(
                        (i * col_w + 0.05, cy - card_h),
                        col_w - 0.1,
                        card_h,
                        boxstyle="round,pad=0.01",
                        fc="#FFF8DC",
                        ec=MOSCOW_COLORS[s["moscow"]],
                        linewidth=1.4,
                    )
                )
                ax.text(
                    i * col_w + 0.09,
                    cy - 0.08,
                    f"{s['id']} · {s['points']} pts",
                    fontsize=5.8,
                    fontweight="bold",
                    va="top",
                )
                ax.text(
                    i * col_w + 0.09,
                    cy - 0.2,
                    textwrap.fill(short_title(s, 60), 17),
                    fontsize=5.2,
                    va="top",
                )
        y -= 0.2 + max_depth[r] * (card_h + gap) + 0.15
    handles = [
        plt.Line2D([], [], color=c, linewidth=3, label=m)
        for m, c in MOSCOW_COLORS.items()
        if m != "Won't"
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=6.5, frameon=False, ncol=3)
    out = ROOT / "docs" / "diagrams" / "story_map.svg"
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)
    return out


def load_requirements() -> list[dict[str, Any]]:
    """Charge les exigences EXF / ENF."""
    with REQUIREMENTS.open("rb") as fh:
        return list(tomllib.load(fh)["req"])


def validate_links(data: dict[str, Any], reqs: list[dict[str, Any]]) -> list[str]:
    """Vérifie que chaque story cite des exigences existantes et que chaque EXF est couverte."""
    known = {r["id"] for r in reqs}
    errors = [
        f"{s['id']}: exigence inconnue {rid}"
        for s in data["story"]
        for rid in s["requirements"]
        if rid not in known
    ]
    covered = {rid for s in data["story"] for rid in s["requirements"]}
    errors += [
        f"{r['id']}: aucune story"
        for r in reqs
        if r["id"].startswith("EXF") and r["id"] not in covered
    ]
    return errors


def scan_tests() -> dict[str, set[str]]:
    """Index ID → fichiers de test qui le citent (tests/**/*.py et *.feature)."""
    index: dict[str, set[str]] = defaultdict(set)
    for path in (ROOT / "tests").rglob("*"):
        if path.suffix not in {".py", ".feature"} or not path.is_file():
            continue
        rel = str(path.relative_to(ROOT))
        for found in ID_PATTERN.findall(path.read_text(encoding="utf-8")):
            index[found].add(rel)
    return index


def write_requirements(data: dict[str, Any], reqs: list[dict[str, Any]]) -> tuple[Path, Path]:
    """Écrit le tableau des exigences et la matrice de traçabilité."""
    stories_by_req: dict[str, list[str]] = defaultdict(list)
    for s in data["story"]:
        for rid in s["requirements"]:
            stories_by_req[rid].append(s["id"])
    tests = scan_tests()
    by_id = {s["id"]: s for s in data["story"]}
    md = [
        "<!-- Généré par tools/backlog.py — ne pas éditer -->",
        "",
        "| ID | Exigence | Stories |",
        "|---|---|---|",
    ]
    rows = []
    for r in reqs:
        stories = stories_by_req.get(r["id"], [])
        pending = [sid for sid in stories if not by_id[sid].get("implemented", True)]
        files = set(tests.get(r["id"], set()))
        for sid in stories:
            files |= tests.get(sid, set())
        if pending and len(pending) == len(stories):
            files = {f for f in files if not f.endswith(".feature")}
        md.append(f"| {r['id']} | {r['text']} | {', '.join(stories) or '—'} |")
        rows.append(
            {
                "exigence": r["id"],
                "libelle": r["text"],
                "stories": " ".join(stories),
                "tests": " ".join(sorted(files)),
                "composants_c4": " | ".join(r["components"]),
                "couvert_par_test": "oui"
                if files
                else ("non (scénario écrit, non implémenté)" if pending else "non"),
            }
        )
    md_path = ROOT / "docs" / "specs" / "_gen" / "requirements.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    csv_path = ROOT / "docs" / "annexes" / "tracabilite.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return md_path, csv_path


def main() -> int:
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="valider sans générer")
    args = parser.parse_args()
    data = load()
    reqs = load_requirements()
    errors = validate(data) + validate_links(data, reqs)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.check:
        print("backlog valide")
        return 0
    print(write_markdown(data))
    for p in write_features(data):
        print(p)
    print(write_svg(data))
    for p in write_requirements(data, reqs):
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
