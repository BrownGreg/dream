"""Construit les deux dossiers PDF depuis les sources Markdown (Pandoc → Typst → PDF).

Étapes : rendu PlantUML (SVG), régénération des artefacts dérivés, résolution des
`{{include …}}`, conversion Pandoc en Typst, compilation, contrôle du nombre de pages.

Usage : python tools/build_docs.py [--skip-generators]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
TEMPLATE = ROOT / "docs" / "templates" / "dossier.typ"
INCLUDE = re.compile(r"^\{\{include (?P<path>[^}]+)\}\}[ \t]*$", re.MULTILINE)
IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")

DOSSIERS = {
    "dossier_cadrage": {
        "dir": ROOT / "docs" / "cadrage",
        "title": "Dossier de cadrage",
        "max_pages": 15,
    },
    "specifications_architecture": {
        "dir": ROOT / "docs" / "specs",
        "title": "Spécifications & architecture",
        "max_pages": 10,
    },
}
GENERATORS = [
    ["tools/backlog.py"],
    ["tools/agile.py"],
    ["tools/export_schema.py"],
    ["tools/journey_map.py"],
    ["benchmark/build_report.py"],
    ["benchmark/build_xlsx.py"],
]


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    """Exécute une commande et s'arrête au premier échec."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        sys.exit(f"échec : {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")


def plantuml() -> None:
    """Rend chaque diagramme .puml en SVG."""
    exe = shutil.which("plantuml") or str(Path.home() / ".local" / "bin" / "plantuml")
    sources = sorted((ROOT / "docs" / "diagrams").glob("*.puml"))
    run([exe, "-tsvg", *[str(s) for s in sources]])


LIST_GAP = re.compile(r"(?m)^(?!\s*[-*] |\s*\d+\. |\s*$|\||```)(.+)\n(?=\s*(?:[-*] |\d+\. ))")
SEPARATOR = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def weight_tables(text: str) -> str:
    """Pondère la largeur des colonnes de chaque tableau selon la longueur moyenne du contenu.

    Pandoc lit les largeurs relatives dans le nombre de tirets de la ligne séparatrice ;
    sans cela, il répartit également et les cellules longues deviennent très hautes.
    """
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if i > 0 and SEPARATOR.match(lines[i]) and lines[i - 1].lstrip().startswith("|"):
            header = _cells(lines[i - 1])
            body: list[list[str]] = []
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                body.append(_cells(lines[j]))
                j += 1
            n = len(header)
            weights = []
            for k in range(n):
                column = [row[k] for row in body if k < len(row)] or [header[k]]
                mean = sum(len(c) for c in column) / len(column)
                longest_word = max(
                    len(w) for c in [*column, header[k]] for w in (c.split() or [""])
                )
                weights.append(max(min(mean, 32.0), longest_word * 1.7 + 2, 5.0))
            total = sum(weights)
            dashes = [max(3, round(120 * w / total)) for w in weights]
            lines[i] = "|" + "|".join("-" * d for d in dashes) + "|"
            i = j
        else:
            i += 1
    return "\n".join(lines)


def _include(folder: Path, spec: str) -> str:
    """Contenu d'un fichier inclus ; `chemin::tableN` n'en garde que le N-ième tableau."""
    path, _, part = spec.strip().partition("::")
    text = (folder / path).read_text(encoding="utf-8")
    if not part.startswith("table"):
        return text
    tables, current = [], []
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            current.append(line)
        elif current:
            tables.append("\n".join(current))
            current = []
    if current:
        tables.append("\n".join(current))
    return tables[int(part[5:]) - 1]


def assemble(folder: Path) -> str:
    """Concatène les sections (ordre des noms de fichiers) et résout includes et images."""
    parts = []
    for section in sorted(folder.glob("[0-9][0-9]_*.md")):
        text = section.read_text(encoding="utf-8")
        text = INCLUDE.sub(lambda m: _include(folder, m["path"]), text)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = text.replace("{{root}}", str(ROOT))
        # Pandoc exige une ligne vide avant une liste : on l'ajoute si elle manque.
        text = LIST_GAP.sub(r"\1\n\n", text)
        text = IMAGE.sub(lambda m: f"![{m['alt']}]({(folder / m['path']).resolve()})", text)
        parts.append(weight_tables(text).strip())
    return "\n\n".join(parts) + "\n"


def pages(pdf: Path) -> int:
    """Nombre de pages d'un PDF (pdfinfo)."""
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True)  # noqa: S603, S607
    match = re.search(r"^Pages:\s+(\d+)", out.stdout, re.MULTILINE)
    return int(match.group(1)) if match else -1


def build(name: str, spec: dict[str, object]) -> tuple[Path, int, int]:
    """Construit un dossier ; retourne (pdf, pages, maximum)."""
    work = BUILD / f"_{name}"
    work.mkdir(parents=True, exist_ok=True)
    md = work / "body.md"
    md.write_text(assemble(spec["dir"]), encoding="utf-8")  # type: ignore[arg-type]
    run(
        [
            "pandoc",
            str(md),
            "-f",
            "markdown+pipe_tables",
            "-t",
            "typst",
            "-o",
            str(work / "body.typ"),
        ]
    )
    typ = work / "body.typ"
    typ.write_text(
        re.sub(r"align: \((?:auto,)+\)", "align: left", typ.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    main = work / "main.typ"
    main.write_text(
        f'#import "{TEMPLATE}": dossier\n'
        f'#show: dossier.with(title: "{spec["title"]}")\n'
        '#include "body.typ"\n',
        encoding="utf-8",
    )
    pdf = BUILD / f"{name}.pdf"
    run(["typst", "compile", "--root", "/", str(main), str(pdf)])
    return pdf, pages(pdf), int(spec["max_pages"])  # type: ignore[call-overload]


def main() -> int:
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-generators", action="store_true")
    args = parser.parse_args()
    plantuml()
    if not args.skip_generators:
        for script in GENERATORS:
            run([sys.executable, *script])
    status = 0
    for name, spec in DOSSIERS.items():
        pdf, count, limit = build(name, spec)
        flag = "OK" if count <= limit else "DÉPASSEMENT"
        print(f"{pdf.name}: {count} pages / {limit} max — {flag}")
        status |= count > limit
    return status


if __name__ == "__main__":
    raise SystemExit(main())
