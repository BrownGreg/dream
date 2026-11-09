"""Génère les journey maps (SVG) des trois personae.

Usage : python tools/journey_map.py  → docs/diagrams/journey_<persona>.svg
Les scores d'émotion (−2 à +2) sont qualitatifs, issus des entretiens simulés.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams"
STAGES = ["Réveil", "Enregistrement", "Attente", "Découverte", "Archivage", "Relecture hebdo"]

JOURNEYS: dict[str, dict[str, object]] = {
    "lea": {
        "title": "Léa — la collectionneuse de rêves",
        "actions": [
            "Se souvient d'un train dans l'eau",
            "Dicte à voix basse, 45 s",
            "Regarde la progression",
            "Découvre l'image",
            "Rêve rangé avec émotion",
            "Parcourt la frise",
        ],
        "thoughts": [
            "« Vite, avant d'oublier »",
            "« Pourvu qu'il comprenne »",
            "« Ça prend combien de temps ? »",
            "« C'est mon train ! »",
            "« Rien à faire, parfait »",
            "« Encore de l'eau… »",
        ],
        "scores": [0, -1, -1, 2, 1, 2],
        "frictions": ["", "Voix ensommeillée", "Attente > 30 s", "Image générique", "", ""],
        "opportunities": [
            "",
            "US-01 un geste",
            "US-08 progression",
            "US-05 corriger le texte",
            "US-06 émotion auto",
            "US-10 frise",
        ],
    },
    "karim": {
        "title": "Karim — le veilleur d'humeur",
        "actions": [
            "Rentre de garde à 8 h",
            "Envoie un mémo vocal",
            "Range son téléphone",
            "Voit « stressant »",
            "Corrige en « neutre »",
            "Compare au mois dernier",
        ],
        "thoughts": [
            "« Encore ce couloir »",
            "« J'ai déjà le fichier »",
            "« Je regarderai plus tard »",
            "« Pas tout à fait »",
            "« C'est moi qui sais »",
            "« Semaine chargée »",
        ],
        "scores": [-1, 0, 0, -1, 1, 1],
        "frictions": ["", "Import non prévu", "", "Classement erroné", "", "Pas de tendance"],
        "opportunities": [
            "",
            "US-02 import",
            "Traitement asynchrone",
            "US-14 corriger",
            "Source stockée",
            "US-16 tendance",
        ],
    },
    "ines": {
        "title": "Inès — la rêveuse inquiète (vulnérable)",
        "actions": [
            "Se réveille en sursaut",
            "Raconte le cauchemar",
            "Coche « pas d'image »",
            "Lit transcription + émotion",
            "Rêve archivé",
            "Supprime un vieux rêve",
        ],
        "thoughts": [
            "« Je dois le sortir de ma tête »",
            "« Qui va entendre ça ? »",
            "« Je ne veux pas le revoir »",
            "« C'est posé, c'est fait »",
            "« Il est à l'abri ? »",
            "« Plus rien ne reste ? »",
        ],
        "scores": [-2, -1, 0, 1, 0, 1],
        "frictions": [
            "",
            "Peur pour la confidentialité",
            "Image imposée",
            "",
            "Doute sur la conservation",
            "Effacement incomplet",
        ],
        "opportunities": [
            "",
            "US-03 consentement clair",
            "US-11 sans image",
            "Ton neutre, pas d'avis",
            "Durées affichées",
            "US-12 cascade",
        ],
    },
}


def render(key: str, data: dict[str, object]) -> Path:
    """Dessine la journey map d'un persona et l'écrit en SVG."""
    scores = list(data["scores"])  # type: ignore[call-overload]
    fig, ax = plt.subplots(figsize=(11, 3.5))
    xs = range(len(STAGES))
    ax.plot(xs, scores, marker="o", color="#4B3F72", linewidth=2)
    ax.axhline(0, color="#BBBBBB", linewidth=0.8)
    ax.set_ylim(-4.6, 3.4)
    ax.set_xlim(-0.5, len(STAGES) - 0.5)
    ax.set_yticks([-2, -1, 0, 1, 2])
    ax.set_yticklabels(["−2", "−1", "0", "+1", "+2"], fontsize=8)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(STAGES, fontsize=9, fontweight="bold")
    ax.xaxis.tick_top()
    for spine in ("right", "bottom"):
        ax.spines[spine].set_visible(False)
    for i in xs:
        ax.annotate(
            f"{data['actions'][i]}\n{data['thoughts'][i]}",  # type: ignore[index]
            (i, scores[i]),
            textcoords="offset points",
            xytext=(0, 9),
            ha="center",
            fontsize=7,
            bbox={"fc": "white", "ec": "none", "alpha": 0.85, "pad": 1},
        )
        friction = data["frictions"][i]  # type: ignore[index]
        if friction:
            ax.text(i, -3.1, f"⚠ {friction}", ha="center", fontsize=7, color="#B03A2E")
        opp = data["opportunities"][i]  # type: ignore[index]
        if opp:
            ax.text(i, -3.9, f"→ {opp}", ha="center", fontsize=7, color="#1E7B4F")
    ax.text(-0.48, -3.1, "Frictions", fontsize=7, color="#B03A2E", ha="left", va="bottom")
    ax.text(-0.48, -3.9, "Opportunités", fontsize=7, color="#1E7B4F", ha="left", va="bottom")
    ax.set_ylabel("Émotion", fontsize=8)
    ax.set_title(str(data["title"]), fontsize=11, loc="left", pad=28)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"journey_{key}.svg"
    fig.savefig(path, format="svg")
    plt.close(fig)
    return path


if __name__ == "__main__":
    plt.rcParams["svg.fonttype"] = "none"
    for persona, journey in JOURNEYS.items():
        print(render(persona, journey))
