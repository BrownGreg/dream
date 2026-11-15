"""Construit les deux dossiers de rendu (pré-production et production), hors du dépôt Git.

Usage : ``make rendu`` (ou ``uv run python scripts/build_rendu.py``).

Sortie, ignorée par Git :
    rendu/preproduction_hery/   et   rendu/rendu_preproduction_hery.zip
    rendu/production_hery/      et   rendu/rendu_production_hery.zip

Le code n'est pas copié : le rendu du code est le lien du dépôt GitHub. Le script
régénère chaque PDF depuis ses sources, puis signale ce qui manque encore (post-mortem
§6, vidéo de démonstration) dans la section « État du dossier » de chaque LISEZ-MOI.
La vidéo est lue dans ``docs/preprod/maquette/demo/video_demo.<mp4|webm|mov>`` (non versionnée).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "rendu"
EV = ROOT / "docs" / "templates" / "eisvogel"
PREPROD = ROOT / "docs" / "preprod"
MAQUETTE = PREPROD / "maquette"
VIDEO_MAX_S = 180
DIAGRAMMES = [
    "c4_context",
    "c4_container",
    "erd",
    "sequence_reve",
    "flow",
    "wireframes",
    "story_map",
    "roadmap",
    "risk_matrix",
    "journey_lea",
    "journey_karim",
    "journey_ines",
]


def run(cmd: list[str], cwd: Path = ROOT, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """Exécute une commande et s'arrête avec son message si elle échoue.

    Args:
        cmd: Commande et arguments.
        cwd: Répertoire de travail.
        stdin: Texte envoyé sur l'entrée standard.

    Returns:
        Le résultat de la commande.
    """
    # Commandes fixes du script (outils de build locaux), aucune entrée externe.
    result = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        sys.exit(f"Échec : {' '.join(cmd)}\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    return result


def pages(pdf: Path) -> int:
    """Nombre de pages d'un PDF (pdfinfo).

    Args:
        pdf: Chemin du PDF.

    Returns:
        Le nombre de pages.
    """
    info = run(["pdfinfo", str(pdf)]).stdout
    match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
    return int(match.group(1)) if match else 0


def md_to_pdf(source: Path, target: Path, title: str, *, landscape: bool = False, text: str | None = None) -> None:
    """Convertit un Markdown du dépôt en PDF avec le gabarit Eisvogel du projet.

    Args:
        source: Fichier Markdown (ses images sont cherchées dans son dossier).
        target: PDF à écrire.
        title: Titre affiché en tête du document.
        landscape: Page à l'italienne (tableaux larges).
        text: Contenu à utiliser à la place du fichier (LISEZ-MOI complétés).
    """
    cmd = [
        "pandoc",
        f"--metadata-file={EV / 'commun.yaml'}",
        f"--template={EV / 'eisvogel.latex'}",
        f"--lua-filter={EV / 'liens_locaux.lua'}",
        "--pdf-engine=xelatex",
        f"--resource-path={source.parent}",
        "-M",
        f"title={title}",
        "-M",
        "titlepage=false",
        "-M",
        "toc=false",
        "-M",
        f"header-left={title}",
        "-o",
        str(target),
    ]
    if landscape:
        cmd += ["-V", "geometry=landscape", "-V", "geometry=margin=1.5cm"]
    contenu = source.read_text(encoding="utf-8") if text is None else text
    # Les polices du PDF n'ont pas les pictogrammes de statut : on les écrit en toutes lettres.
    for picto, mot in (("✅", "OK"), ("⚠️", "Partiel"), ("⚠", "Partiel"), ("❌", "Absent"), ("⏳", "À venir")):
        contenu = contenu.replace(picto, mot)
    run([*cmd, "-f", "markdown", "-"], stdin=contenu)


def incidents_en_fiches(source: Path) -> str:
    """Réécrit le tableau du journal des incidents en une fiche par incident.

    Le tableau à 8 colonnes du dépôt est illisible sur une page A4 ; les fiches gardent
    exactement le même texte, champ par champ.

    Args:
        source: ``docs/incidents.md``.

    Returns:
        Le Markdown des fiches, précédé de l'introduction du journal.
    """
    lignes = source.read_text(encoding="utf-8").splitlines()
    intro = [ligne for ligne in lignes if not ligne.startswith("|") and not ligne.startswith("# ")]
    entete: list[str] = []
    fiches: list[str] = []
    for ligne in lignes:
        if not ligne.startswith("|") or set(ligne) <= {"|", "-", " "}:
            continue
        cellules = [c.strip() for c in ligne.strip().strip("|").split(" | ")]
        if not entete:
            entete = cellules
            continue
        champs = dict(zip(entete, cellules, strict=False))
        fiches.append(f"## Incident n° {champs['#']} — {champs['Date']} — {champs['Ticket']}")
        for cle in entete[3:]:
            fiches.append(f"**{cle}.** {champs.get(cle, '')}\n")
    return "\n".join(intro).strip() + "\n\n" + "\n".join(fiches) + "\n"


def video() -> Path | None:
    """Vidéo de démonstration du bloc 1, si l'auteur l'a déposée."""
    for ext in ("mp4", "webm", "mov"):
        found = MAQUETTE / "demo" / f"video_demo.{ext}"
        if found.exists():
            return found
    return None


def duree_s(media: Path) -> float:
    """Durée d'un fichier audio ou vidéo, en secondes (ffprobe)."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media)]).stdout
    return float(json.loads(out)["format"]["duration"])


def zipper(folder: Path) -> Path:
    """Archive un dossier de rendu à côté de lui.

    Args:
        folder: Dossier à archiver.

    Returns:
        Le chemin de l'archive.
    """
    archive = OUT / f"rendu_{folder.name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zf.write(path, Path(folder.name) / path.relative_to(folder))
    return archive


def preproduction() -> tuple[Path, list[str]]:
    """Construit le dossier de rendu du bloc 1.

    Returns:
        Le dossier construit et la liste des manques.
    """
    dest = OUT / "preproduction_hery"
    annexes = dest / "annexes"
    (annexes / "diagrammes").mkdir(parents=True)
    # Rendu Pandoc + Eisvogel (skill pdf-generation), mise en page compacte pour tenir les
    # limites du sujet ; schémas C4 et séquence en version Excalidraw.
    livrables = PREPROD / "livrables"
    run(["make", "eisvogel"])
    for nom, num in (("dossier_cadrage", "01"), ("specifications_architecture", "02")):
        shutil.copy2(livrables / f"{nom}_eisvogel.pdf", dest / f"{num}_{nom}.pdf")
    shutil.copy2(PREPROD / "annexes" / "benchmark.xlsx", dest / "03_benchmark.xlsx")

    lock_existait = (MAQUETTE / "uv.lock").exists()
    tests = subprocess.run(  # noqa: S603
        [
            shutil.which("uv") or "uv",
            "run",
            "-q",
            "--all-extras",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--cov=src",
            "--cov-report=term",
        ],
        cwd=MAQUETTE,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": "src:benchmark"},
    )
    if not lock_existait:
        (MAQUETTE / "uv.lock").unlink(missing_ok=True)
    entete = "Tests de la maquette du bloc 1 (docs/preprod/maquette/tests), exécutés par `make rendu`.\n\n"
    (dest / "04_tests_maquette.txt").write_text(entete + tests.stdout + tests.stderr, encoding="utf-8")
    if tests.returncode != 0:
        sys.exit("Les tests de la maquette échouent : voir rendu/preproduction_hery/04_tests_maquette.txt")

    for src, nom, titre in (
        ("interviews.md", "entretiens.pdf", "Entretiens éclair"),
        ("kano.md", "kano.pdf", "Matrice de Kano"),
        ("aipd.md", "aipd.pdf", "Analyse d'impact (AIPD)"),
    ):
        md_to_pdf(PREPROD / "annexes" / src, annexes / nom, titre)
    for src in ("jira_import.csv", "tracabilite.csv"):
        shutil.copy2(PREPROD / "annexes" / src, annexes / src)
    shutil.copy2(PREPROD / "schemas" / "dream.schema.json", annexes / "dream.schema.json")
    for nom in DIAGRAMMES:
        shutil.copy2(PREPROD / "diagrams" / f"{nom}.svg", annexes / "diagrammes" / f"{nom}.svg")

    manques: list[str] = []
    etat: list[str] = []
    found = video()
    if found is None:
        manques.append("vidéo de démonstration")
        etat.append(
            "- **À compléter : vidéo de démonstration (≤ 3 min).** Script et minutage : "
            "`script_video.md`, dans le dossier `maquette/demo/` du dépôt."
        )
    else:
        duree = duree_s(found)
        shutil.copy2(found, dest / f"05_video_demo{found.suffix}")
        etat.append(f"- Vidéo de démonstration : {int(duree // 60)} min {int(duree % 60):02d} s.")
        if duree > VIDEO_MAX_S:
            manques.append("vidéo de plus de 3 min")
            etat[-1] += " **Dépasse la limite de 3 min du sujet.**"
    dc, sp = pages(dest / "01_dossier_cadrage.pdf"), pages(dest / "02_specifications_architecture.pdf")
    etat.append(f"- Dossier de cadrage : {dc} pages (limite 15) ; spécifications : {sp} pages (limite 10).")
    if dc > 15 or sp > 10:
        manques.append("limite de pages dépassée")
    resume = re.search(r"(\d+ passed[^=\n]*?)\s*=*$", tests.stdout, re.MULTILINE)
    total = re.search(r"^TOTAL\s.*?(\d+%)\s*$", tests.stdout, re.MULTILINE)
    tests_txt = "voir 04_tests_maquette.txt"
    if resume:
        tests_txt = re.sub(r"\s+in [\d.]+s$", "", resume.group(1).strip())
        tests_txt = tests_txt.replace("passed", "réussis").replace("skipped", "ignorés")
    if total:
        tests_txt += f", couverture {total.group(1)}"
    etat.append(f"- Tests de la maquette : {tests_txt}.")
    if not manques:
        etat.insert(0, "Dossier complet.")

    lisez = (ROOT / "docs" / "rendu" / "LISEZ-MOI_preproduction.md").read_text(encoding="utf-8")
    lisez = lisez.replace("{{ETAT}}", "\n".join(etat)).replace("{{PAGES_DC}}", str(dc)).replace("{{PAGES_SP}}", str(sp))
    if found is None:
        lisez = lisez.replace("| `05_video_demo.mp4` |", "| `05_video_demo.mp4` (à ajouter) |")
    md_to_pdf(
        ROOT / "docs" / "rendu" / "LISEZ-MOI_preproduction.md",
        dest / "00_LISEZ-MOI.pdf",
        "Rendu pré-production",
        text=lisez,
    )
    return dest, manques


def production() -> tuple[Path, list[str]]:
    """Construit le dossier de rendu du bloc 3.

    Returns:
        Le dossier construit et la liste des manques.
    """
    dest = OUT / "production_hery"
    annexes = dest / "annexes"
    annexes.mkdir(parents=True)
    run(["make", "rapport", "postmortem", "code-review"])
    shutil.copy2(ROOT / "docs" / "rapport" / "rapport_hery.pdf", dest / "rapport_hery.pdf")
    shutil.copy2(ROOT / "docs" / "postmortem" / "postmortem_gregory.pdf", dest / "postmortem_gregory.pdf")
    shutil.copy2(ROOT / "docs" / "code-review" / "dossier_code_review.pdf", dest / "dossier_code_review.pdf")

    docs = ROOT / "docs"
    md_to_pdf(docs / "CONFORMITE.md", annexes / "conformite.pdf", "Conformité au sujet de production", landscape=True)
    md_to_pdf(
        docs / "incidents.md",
        annexes / "incidents.pdf",
        "Journal des incidents",
        text=incidents_en_fiches(docs / "incidents.md"),
    )
    md_to_pdf(docs / "tests" / "strategie.md", annexes / "strategie_tests.pdf", "Stratégie de tests")
    md_to_pdf(docs / "tests" / "performance.md", annexes / "performance.pdf", "Performance mesurée", landscape=True)
    md_to_pdf(docs / "backlog" / "README.md", annexes / "backlog_jira.pdf", "Backlog et correspondance Jira")
    shutil.copy2(
        docs / "tests" / "production" / "apicall_2026-11-15.json", annexes / "mesures_production_2026-11-15.json"
    )
    shutil.copy2(docs / "diagrams" / "c4_container_excalidraw.excalidraw.png", annexes / "architecture.png")

    pm = (docs / "postmortem" / "postmortem.md").read_text(encoding="utf-8")
    a_rediger = pm.count("**À rédiger.**")
    manques: list[str] = []
    etat: list[str] = []
    if a_rediger:
        manques.append(f"post-mortem §6 ({a_rediger} encadrés)")
        etat.append(
            f"- **À compléter : post-mortem §6, {a_rediger} encadrés « À rédiger »** "
            "(auto-évaluation, recul critique, leçons), réservés à l'auteur."
        )
    else:
        etat.append("- Post-mortem complet.")
    r, p, c = (pages(dest / f) for f in ("rapport_hery.pdf", "postmortem_gregory.pdf", "dossier_code_review.pdf"))
    etat.append(f"- Rapport : {r} pages ; post-mortem : {p} pages ; dossier de code review : {c} pages.")
    if not manques:
        etat.insert(0, "Dossier complet.")

    lisez = (docs / "rendu" / "LISEZ-MOI_production.md").read_text(encoding="utf-8")
    for cle, val in (
        ("{{ETAT}}", "\n".join(etat)),
        ("{{PAGES_RAPPORT}}", str(r)),
        ("{{PAGES_PM}}", str(p)),
        ("{{PAGES_CR}}", str(c)),
    ):
        lisez = lisez.replace(cle, val)
    md_to_pdf(docs / "rendu" / "LISEZ-MOI_production.md", dest / "00_LISEZ-MOI.pdf", "Rendu production", text=lisez)
    return dest, manques


def main() -> int:
    """Point d'entrée : reconstruit les deux dossiers et leurs archives."""
    for tool in ("pandoc", "xelatex", "pdfinfo", "ffprobe", "plantuml", "rsvg-convert", "uv"):
        if shutil.which(tool) is None:
            sys.exit(f"Outil manquant : {tool}")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    bilan = []
    for construire in (preproduction, production):
        dossier, manques = construire()
        archive = zipper(dossier)
        taille = archive.stat().st_size / 1_000_000
        statut = "complet" if not manques else "à compléter : " + ", ".join(manques)
        bilan.append(f"{archive.relative_to(ROOT)} ({taille:.1f} Mo) — {statut}")
    print("\n".join(bilan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
