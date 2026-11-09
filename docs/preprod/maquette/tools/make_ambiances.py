"""Génère les 6 boucles d'ambiance de la maquette (ADR-005) avec ffmpeg.

Sons de synthèse produits localement (aucun échantillon tiers) : diffusables sans
restriction, en attendant la bibliothèque CC0 curée de la production.
Usage : python tools/make_ambiances.py → app/assets/ambiance/<émotion>.mp3
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "assets" / "ambiance"
SECONDS = 12

# Graphes de filtres lavfi : accords doux, bruit filtré, trémolo.
RECIPES: dict[str, str] = {
    "heureux": "sine=f=440:d={d},volume=0.25[a];sine=f=554.37:d={d},volume=0.2[b];"
    "sine=f=659.25:d={d},volume=0.2[c];[a][b][c]amix=inputs=3,tremolo=f=0.5:d=0.3",
    "serein": "anoisesrc=d={d}:c=pink:a=0.15,lowpass=f=400[n];sine=f=220:d={d},volume=0.15[s];"
    "[n][s]amix=inputs=2",
    "neutre": "anoisesrc=d={d}:c=brown:a=0.2,lowpass=f=800",
    "etrange": "sine=f=311:d={d},volume=0.3,tremolo=f=6:d=0.8,aphaser[a];"
    "sine=f=466:d={d},volume=0.15,vibrato=f=0.7:d=0.6[b];[a][b]amix=inputs=2",
    "melancolique": "sine=f=220:d={d},volume=0.25[a];sine=f=261.63:d={d},volume=0.2[b];"
    "sine=f=329.63:d={d},volume=0.2[c];[a][b][c]amix=inputs=3,lowpass=f=1200,tremolo=f=0.25:d=0.4",
    "stressant": "sine=f=55:d={d},volume=0.5[a];anoisesrc=d={d}:c=white:a=0.05,highpass=f=2000,"
    "tremolo=f=3:d=0.9[b];[a][b]amix=inputs=2",
}


def main() -> None:
    """Écrit une boucle MP3 par émotion."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg requis")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, graph in RECIPES.items():
        target = OUT / f"{name}.mp3"
        fade = f",afade=t=in:d=1,afade=t=out:st={SECONDS - 1}:d=1"
        subprocess.run(  # noqa: S603
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                graph.format(d=SECONDS) + fade,
                "-ac",
                "1",
                "-ar",
                "22050",
                "-b:a",
                "64k",
                str(target),
            ],
            check=True,
        )
        print(target)


if __name__ == "__main__":
    main()
