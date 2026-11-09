"""Génère les artefacts de pilotage depuis docs/backlog/*.toml.

Sorties :
    docs/diagrams/risk_matrix.svg       matrice probabilité × impact
    docs/diagrams/roadmap.svg           roadmap / release plan par sprint
    docs/cadrage/_gen/risks.md          registre des risques
    docs/cadrage/_gen/sprint1.md        backlog détaillé du Sprint #1
    docs/annexes/jira_import.csv        import CSV Jira (épopées, stories, sous-tâches)

Usage : python tools/agile.py
"""

from __future__ import annotations

import csv
import math
import tomllib
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs" / "backlog"
DIAGRAMS = ROOT / "docs" / "diagrams"
GEN = ROOT / "docs" / "cadrage" / "_gen"
VELOCITY_HYPOTHESIS = 11  # points engagés au Sprint 1 ; remplacée par la vélocité mesurée
LEVELS = [
    (12, "critique", "#C0392B"),
    (6, "élevé", "#E67E22"),
    (3, "modéré", "#F4D03F"),
    (0, "faible", "#82E0AA"),
]
PRIORITY = {"Must": "Highest", "Should": "High", "Could": "Medium", "Won't": "Lowest"}


def load(name: str) -> dict[str, Any]:
    """Charge un fichier TOML du backlog."""
    with (BACKLOG / name).open("rb") as fh:
        return tomllib.load(fh)


def _fr(x: float) -> str:
    """Nombre décimal au format français, sans zéro inutile."""
    return f"{round(x, 2):g}".replace(".", ",")


def level(score: int) -> tuple[str, str]:
    """Libellé et couleur de criticité."""
    for threshold, label, color in LEVELS:
        if score >= threshold:
            return label, color
    return LEVELS[-1][1], LEVELS[-1][2]


def risk_matrix(risks: list[dict[str, Any]]) -> Path:
    """Matrice 4 × 4, chaque risque placé dans sa case."""
    plt.rcParams["svg.fonttype"] = "none"
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for p in range(1, 5):
        for i in range(1, 5):
            _, color = level(p * i)
            ax.add_patch(
                Rectangle((i - 0.5, p - 0.5), 1, 1, fc=color, ec="white", lw=2, alpha=0.85)
            )
    cells: dict[tuple[int, int], list[str]] = {}
    for r in risks:
        cells.setdefault((r["impact"], r["probability"]), []).append(r["id"])
    for (i, p), ids in cells.items():
        ax.text(i, p, "\n".join(ids), ha="center", va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(0.5, 4.5)
    ax.set_ylim(0.5, 4.5)
    ticks = ["1 faible", "2 moyen", "3 élevé", "4 très élevé"]
    ax.set_xticks(range(1, 5), ticks, fontsize=8)
    ax.set_yticks(range(1, 5), ticks, fontsize=8)
    ax.set_xlabel("Impact", fontsize=9)
    ax.set_ylabel("Probabilité", fontsize=9)
    handles = [Rectangle((0, 0), 1, 1, fc=c) for _, _, c in LEVELS]
    labels = [f"{lab} (≥ {t})" if t else lab for t, lab, _ in LEVELS]
    ax.legend(
        handles,
        labels,
        title="Criticité P × I",
        fontsize=7,
        title_fontsize=7,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
    )
    ax.set_title("Matrice des risques", fontsize=10, loc="left")
    fig.tight_layout()
    out = DIAGRAMS / "risk_matrix.svg"
    fig.savefig(out, format="svg")
    plt.close(fig)
    return out


def roadmap(stories: list[dict[str, Any]]) -> Path:
    """Release plan : releases → sprints d'une semaine, à vélocité hypothétique."""
    plt.rcParams["svg.fonttype"] = "none"
    points = {
        r: sum(s["points"] for s in stories if s["release"] == r) for r in ("MVP", "R2", "R3")
    }
    colors = {"MVP": "#4B3F72", "R2": "#7B68AE", "R3": "#B8AEDC"}
    content = {
        "MVP": "Parcours complet d'un rêve, consentement, effacement",
        "R2": "Correction émotion, lecture vocale, export, suppression compte — bêta 30 pers.",
        "R3": "Style visuel, micro-vidéo à la demande, rappel",
    }
    fig, ax = plt.subplots(figsize=(9, 2.4))
    start = 0.0
    for i, release in enumerate(("MVP", "R2", "R3")):
        sprints = math.ceil(points[release] / VELOCITY_HYPOTHESIS)
        ax.barh(i, sprints, left=start, color=colors[release], height=0.55)
        ax.text(
            start + 0.1,
            i,
            release,
            va="center",
            color="white",
            fontsize=8,
            fontweight="bold",
        )
        ax.text(
            start + sprints + 0.1,
            i,
            f"{points[release]} pts · {sprints} sprints — {content[release]}",
            va="center",
            fontsize=7,
        )
        start += sprints
    ax.axvline(4, color="#C0392B", ls="--", lw=1)
    ax.text(4.05, -0.45, "fin MVP : conditions BFL et AIPD validées", fontsize=6.5, color="#C0392B")
    ax.set_yticks([])
    ax.set_xticks(
        [x + 0.5 for x in range(int(start))], [f"S{x + 1}" for x in range(int(start))], fontsize=7
    )
    ax.set_xlim(0, start + 6)
    ax.set_ylim(2.5, -0.7)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_title(
        f"Release plan — sprints d'une semaine, vélocité hypothèse {VELOCITY_HYPOTHESIS} pts",
        fontsize=9,
        loc="left",
    )
    fig.tight_layout()
    out = DIAGRAMS / "roadmap.svg"
    fig.savefig(out, format="svg")
    plt.close(fig)
    return out


def risks_md(risks: list[dict[str, Any]]) -> Path:
    """Tableau du registre des risques, trié par criticité."""
    lines = [
        "<!-- Généré par tools/agile.py — ne pas éditer -->",
        "",
        "| ID | Risque (catégorie) | P × I | Déclencheur | Prévention | Correction | Resp. |",
        "|-----|----------------|--------|--------------------|-------------------------|"
        "----------------------|-----|",
    ]
    for r in sorted(risks, key=lambda x: -x["probability"] * x["impact"]):
        score = r["probability"] * r["impact"]
        lines.append(
            f"| {r['id']} | {r['title']} ({r['category'].lower()}) | "
            f"{r['probability']} × {r['impact']} = **{score}** {level(score)[0]} | "
            f"{r['trigger']} | {r['prevention']} | "
            f"{r['correction']} | {r['owner']} |"
        )
    out = GEN / "risks.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def sprint_md(sprint: dict[str, Any], stories: dict[str, dict[str, Any]]) -> Path:
    """Backlog détaillé du Sprint #1."""
    hours = sum(t[1] for item in sprint["item"] for t in item["tasks"])
    pts = sum(stories[i["story"]]["points"] for i in sprint["item"] if i["story"] in stories)
    ceremonies = float(sprint["ceremonies_hours"])
    lines = [
        "<!-- Généré par tools/agile.py — ne pas éditer -->",
        "",
        f"**Objectif** : {sprint['goal']}",
        "",
        f"**Capacité** : {sprint['capacity_hours']} h ({sprint['capacity_method']}). "
        f"Planifié : {pts} points, {_fr(hours)} h de tâches + {_fr(ceremonies)} h de "
        f"cérémonies ; marge {_fr(sprint['capacity_hours'] - hours - ceremonies)} h.",
        "",
        "| Story | Pts | Tâche technique | h |",
        "|---|---|---|---|",
    ]
    for item in sprint["item"]:
        label = (
            item["story"] if item["story"] not in stories else f"{item['story']} {item['summary']}"
        )
        if item["story"] in ("TECH", "RGPD"):
            label = item["summary"]
        p = stories[item["story"]]["points"] if item["story"] in stories else "—"
        for k, (task, h) in enumerate(item["tasks"]):
            lines.append(
                f"| {label if k == 0 else ''} | {p if k == 0 else ''} | {task} | {_fr(h)} |"
            )
    lines += [
        "",
        "**Cérémonies** : "
        + " · ".join(
            f"{c['name']} ({c['when']}, {c['duration']}) → {c['output']}"
            for c in sprint["ceremony"]
        ),
        "",
        "**Reporté au Sprint 2** : " + " ; ".join(sprint["next_sprint"]) + ".",
    ]
    out = GEN / "sprint1.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def jira_csv(data: dict[str, Any], sprint: dict[str, Any]) -> Path:
    """Import CSV Jira : épopées (activités), stories liées, sous-tâches du Sprint 1."""
    rows: list[dict[str, str]] = []
    for act in data["activity"]:
        rows.append(
            {
                "Issue ID": act["id"],
                "Issue Type": "Epic",
                "Summary": act["name"],
                "Description": f"Activité {act['id']} de la User Story Map",
                "Priority": "",
                "Story Points": "",
                "Parent": "",
                "Labels": "dreamsynth",
                "Sprint": "",
            }
        )
    in_sprint = {i["story"] for i in sprint["item"]}
    for s in data["story"]:
        if s["moscow"] == "Won't":
            continue
        desc = (
            f"En tant que {s['role']}, je veux {s['want']} afin de {s['so_that']}.\n\n"
            f"Critères d'acceptation :\n{s['gherkin'].strip()}\n\nExigences : "
            f"{', '.join(s['requirements'])}"
        )
        rows.append(
            {
                "Issue ID": s["id"],
                "Issue Type": "Story",
                "Summary": f"{s['id']} — {s['want']}",
                "Description": desc,
                "Priority": PRIORITY[s["moscow"]],
                "Story Points": str(s["points"]),
                "Parent": s["activity"],
                "Labels": f"{s['release']} kano-{s['kano']} {s['id']}",
                "Sprint": "Sprint 1" if s["id"] in in_sprint else "",
            }
        )
    n = 0
    for item in sprint["item"]:
        parent = item["story"] if item["story"] not in ("TECH", "RGPD") else ""
        issue_type = "Sub-task" if parent else "Task"
        for task, hours in item["tasks"]:
            n += 1
            rows.append(
                {
                    "Issue ID": f"T-{n:02d}",
                    "Issue Type": issue_type,
                    "Summary": task,
                    "Description": f"Estimation : {hours:g} h",
                    "Priority": "High",
                    "Story Points": "",
                    "Parent": parent,
                    "Labels": f"sprint-1 {item['story'].lower()}",
                    "Sprint": "Sprint 1",
                }
            )
    out = ROOT / "docs" / "annexes" / "jira_import.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return out


def main() -> None:
    """Génère tous les artefacts de pilotage."""
    GEN.mkdir(parents=True, exist_ok=True)
    data = load("stories.toml")
    risks = load("risks.toml")["risk"]
    sprint = load("sprint1.toml")
    by_id = {s["id"]: s for s in data["story"]}
    for path in (
        risk_matrix(risks),
        roadmap(data["story"]),
        risks_md(risks),
        sprint_md(sprint, by_id),
        jira_csv(data, sprint),
    ):
        print(path)


if __name__ == "__main__":
    main()
