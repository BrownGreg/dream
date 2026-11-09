"""Génère docs/annexes/benchmark.xlsx à partir du catalogue, des hypothèses et des mesures.

Principes :
- aucune valeur calculée n'est figée : coûts, scénarios et scores sont des formules Excel ;
- les hypothèses sont des cellules nommées (Hyp_H0…Hyp_H9) modifiables ;
- seules les mesures `live` alimentent les colonnes de latence ; sinon « NON MESURÉ — mock ».

Usage : python benchmark/build_xlsx.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from catalog import CATEGORIES, Hypotheses, Provider, load_catalog, load_hypotheses
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.worksheet import Worksheet

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "annexes" / "benchmark.xlsx"
RESULTS = HERE / "results"

HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="4B3F72")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
EST_FILL = PatternFill("solid", fgColor="FCE4D6")
WRAP = Alignment(wrap_text=True, vertical="top")
NOT_MEASURED = "NON MESURÉ — mock"

SHEET_NAMES = {
    "STT": "STT",
    "LLM": "LLM émotion",
    "T2I": "Texte-image",
    "VIDEO": "Vidéo",
    "TTS": "TTS",
    "AMBIANCE": "Ambiance",
}
# Colonnes des onglets catégorie (lettre → (en-tête, largeur)).
COLUMNS = [
    ("A", "Clé", 24),
    ("B", "Fournisseur", 22),
    ("C", "Modèle", 26),
    ("D", "Siège", 12),
    ("E", "Prix publié", 11),
    ("F", "Prix sortie (LLM)", 11),
    ("G", "Unité publiée", 14),
    ("H", "Facteur → unité de calcul", 12),
    ("I", "Prix unitaire de calcul", 12),
    ("J", "Coût par rêve ($)", 12),
    ("K", "Coût 10 rêves/jour ($)", 12),
    ("L", "Statut prix", 12),
    ("M", "p50 total (s)", 10),
    ("N", "p95 total (s)", 10),
    ("O", "p50 TTFB (s)", 10),
    ("P", "Taux d'erreur", 10),
    ("Q", "Source mesure", 30),
    ("R", "WER corpus FR", 10),
    ("S", "Quota / rate limit", 22),
    ("T", "Qualité FR (constat)", 30),
    ("U", "Localisation des données", 30),
    ("V", "Entraînement sur les données", 30),
    ("W", "Rétention / ZDR", 30),
    ("X", "DPA", 16),
    ("Y", "Transfert hors UE", 18),
    ("Z", "SDK Python", 18),
    ("AA", "Licence", 14),
    ("AB", "Acteur / hébergement UE", 10),
    ("AC", "Source prix (URL)", 40),
    ("AD", "Note", 50),
    ("AE", "Fin de vie annoncée", 10),
]
COST_FORMULA = {
    "STT": "=I{r}*Hyp_H1",
    "LLM": '=IF(ISNUMBER(I{r}),(Hyp_H2*I{r}+Hyp_H3*F{r})/1000000,"")',
    "T2I": "=I{r}*Hyp_H4*(1+Hyp_H8)",
    "TTS": "=I{r}/1000000*Hyp_H6",
    "AMBIANCE": '=IF(G{r}="$/min",I{r}*Hyp_H5/60,I{r})',
    "VIDEO": "=I{r}*Hyp_H7",
}


def latest(pattern: str) -> Path | None:
    """Dernier fichier de résultats correspondant au motif."""
    files = sorted(RESULTS.glob(pattern))
    return files[-1] if files else None


def read_rows(path: Path | None) -> dict[str, dict[str, str]]:
    """Lit un CSV de résultats indexé par fournisseur."""
    if path is None:
        return {}
    with path.open(encoding="utf-8") as fh:
        return {row["provider"]: row for row in csv.DictReader(fh)}


def header(ws: Worksheet, titles: list[tuple[str, int]], row: int = 1) -> None:
    """Écrit une ligne d'en-tête stylée et règle les largeurs."""
    for i, (title, width) in enumerate(titles, start=1):
        cell = ws.cell(row=row, column=i, value=title)
        cell.font, cell.fill, cell.alignment = HEAD, HEAD_FILL, WRAP
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = ws.cell(row=row + 1, column=2)


def sheet_readme(wb: Workbook, consulted: str, live: Path | None) -> None:
    """Onglet de lecture."""
    ws = wb.active
    if ws is None:
        raise RuntimeError("classeur sans feuille active")
    ws.title = "Lisez-moi"
    lines = [
        ("Benchmark — Synthétiseur de rêves", True),
        (
            f"Prix et clauses consultés le {consulted} sur les pages officielles (onglet Sources).",
            False,
        ),
        (
            "Fichier généré par benchmark/build_xlsx.py — ne pas éditer à la main hors cellules jaunes.",
            False,
        ),
        ("Cellules jaunes : paramètres modifiables (hypothèses, pondérations).", False),
        (
            "Statut SOURCÉ : lu sur la page officielle. ESTIMÉ (orange) : non publié en clair, méthode en note.",
            False,
        ),
        (
            "NON PUBLIÉ : le fournisseur ne publie pas la valeur ; cellule vide, exclue des calculs.",
            False,
        ),
        (
            f"Latences : {'mesures live ' + live.name if live else NOT_MEASURED + ' (aucune clé API au moment de la génération)'}.",
            False,
        ),
        (
            "Scoring : seuls les critères renseignés comptent ; un critère vide est exclu du dénominateur.",
            False,
        ),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=text).font = Font(bold=bold, size=14 if bold else 11)
    ws.column_dimensions["A"].width = 120


def sheet_hypotheses(wb: Workbook, h: Hypotheses) -> None:
    """Onglet Hypothèses avec noms définis Hyp_H0…Hyp_H9."""
    ws = wb.create_sheet("Hypothèses")
    header(
        ws,
        [
            ("ID", 6),
            ("Hypothèse", 32),
            ("Valeur", 10),
            ("Unité", 18),
            ("Statut", 12),
            ("Méthode", 90),
        ],
    )
    for r, row in enumerate(h.rows, start=2):
        ws.cell(row=r, column=1, value=row["id"])
        ws.cell(row=r, column=2, value=row["name"])
        val = ws.cell(row=r, column=3, value=row["value"])
        val.fill = INPUT_FILL
        ws.cell(row=r, column=4, value=row["unit"])
        ws.cell(row=r, column=5, value=row["status"])
        ws.cell(row=r, column=6, value=row["method"]).alignment = WRAP
        wb.defined_names[f"Hyp_{row['id']}"] = DefinedName(
            f"Hyp_{row['id']}", attr_text=f"'Hypothèses'!$C${r}"
        )


def sheet_category(
    wb: Workbook,
    cat: str,
    providers: list[Provider],
    summary: dict[str, dict[str, str]],
    wer: dict[str, dict[str, str]],
) -> None:
    """Un onglet par catégorie avec coûts en formules et mesures live éventuelles."""
    ws = wb.create_sheet(SHEET_NAMES[cat])
    header(ws, [(t, w) for _, t, w in COLUMNS])
    for r, p in enumerate(providers, start=2):
        x = p.extra
        values: dict[str, object] = {
            "A": p.key,
            "B": p.vendor,
            "C": p.model,
            "D": x.get("hq", ""),
            "E": None if math.isnan(p.price) else p.price,
            "F": None if math.isnan(p.price_out) else p.price_out,
            "G": p.unit,
            "H": p.per_unit_factor,
            "I": f'=IF(ISNUMBER(E{r}),E{r}*H{r},"")',
            "J": f'=IF(ISNUMBER(I{r}),{COST_FORMULA[cat].format(r=r)[1:]},"")',
            "K": f'=IF(ISNUMBER(J{r}),J{r}*Hyp_H0,"")',
            "L": p.status,
            "S": x.get("rate_limit", ""),
            "T": x.get("fr_quality", ""),
            "U": x.get("data_location", ""),
            "V": x.get("training", ""),
            "W": x.get("retention", ""),
            "X": x.get("dpa", ""),
            "Y": x.get("transfer", ""),
            "Z": x.get("sdk_python", ""),
            "AA": x.get("license", ""),
            "AB": "Oui" if p.eu else "Non",
            "AC": p.url,
            "AD": x.get("note", ""),
            "AE": "Oui" if x.get("deprecated") else "Non",
        }
        m = summary.get(p.key)
        if m and m["mode"] in {"live", "local"}:
            values |= {
                "M": float(m["p50_total_s"]),
                "N": float(m["p95_total_s"]),
                "O": float(m["p50_ttfb_s"]),
                "P": float(m["error_rate"]),
                "Q": f"{m['calls']} appels — {m['source']}",
            }
        else:
            values["Q"] = NOT_MEASURED
        if p.key in wer:
            values["R"] = float(wer[p.key]["wer"])
        for col, value in values.items():
            cell = ws[f"{col}{r}"]
            cell.value = value
            cell.alignment = WRAP
        for col in ("I", "J", "K"):
            ws[f"{col}{r}"].number_format = "0.00000"
        ws[f"P{r}"].number_format = "0.0%"
        ws[f"R{r}"].number_format = "0.0%"
        if p.status == "ESTIMÉ":
            for col in ("E", "L"):
                ws[f"{col}{r}"].fill = EST_FILL


def sheet_costs(wb: Workbook, h: Hypotheses, providers: dict[str, Provider]) -> None:
    """Onglet « Coût 10 rêves/jour » : scénarios en formules INDEX/MATCH."""
    ws = wb.create_sheet("Coût 10 rêves-jour")
    cols = [("Scénario", 30)] + [(f"{c} ($/rêve)", 12) for c in CATEGORIES]
    cols += [
        ("$/rêve", 10),
        ("$/jour", 10),
        ("$/mois", 10),
        ("$/an", 10),
        ("$/mois bêta (H10 × H11)", 12),
        ("≤ CS-03 (0,05 $) ?", 12),
        ("Contient ESTIMÉ", 12),
        ("Fournisseurs", 70),
    ]
    header(ws, cols)
    for r, sc in enumerate(h.scenarios, start=2):
        ws.cell(row=r, column=1, value=f"{sc['id']} {sc['name']}")
        names = []
        estimated = False
        for i, cat in enumerate(CATEGORIES, start=2):
            key = sc.get(cat, "")
            sheet = SHEET_NAMES[cat]
            if key:
                formula = f"=IFERROR(INDEX('{sheet}'!$J$2:$J$40,MATCH(\"{key}\",'{sheet}'!$A$2:$A$40,0)),0)"
                names.append(f"{cat}: {providers[key].vendor} {providers[key].model}")
                estimated |= providers[key].status == "ESTIMÉ"
            else:
                formula = "=0"
            cell = ws.cell(row=r, column=i, value=formula)
            cell.number_format = "0.00000"
        last = get_column_letter(1 + len(CATEGORIES))
        base = 2 + len(CATEGORIES)
        refs = {
            "dream": f"{get_column_letter(base)}{r}",
            "day": f"{get_column_letter(base + 1)}{r}",
        }
        ws.cell(row=r, column=base, value=f"=SUM(B{r}:{last}{r})").number_format = "0.0000"
        ws.cell(row=r, column=base + 1, value=f"={refs['dream']}*Hyp_H0").number_format = "0.000"
        ws.cell(row=r, column=base + 2, value=f"={refs['day']}*Hyp_H9").number_format = "0.00"
        ws.cell(row=r, column=base + 3, value=f"={refs['day']}*365").number_format = "0.00"
        beta = f"={refs['dream']}*Hyp_H10*Hyp_H11*Hyp_H9"
        ws.cell(row=r, column=base + 4, value=beta).number_format = "0.00"
        ws.cell(row=r, column=base + 5, value=f'=IF({refs["dream"]}<=0.05,"Oui","Non")')
        ws.cell(row=r, column=base + 6, value="Oui" if estimated else "Non")
        ws.cell(row=r, column=base + 7, value=" · ".join(names)).alignment = WRAP
    note_row = len(h.scenarios) + 3
    ws.cell(
        row=note_row,
        column=1,
        value=(
            "Formules : chaque coût d'étape est lu dans l'onglet de la catégorie (colonne J) ; "
            "modifier une hypothèse ou un prix recalcule tout le classeur."
        ),
    )


SCORED = ["STT", "LLM", "T2I", "TTS", "AMBIANCE"]
CRITERIA = [
    # (nom, poids par défaut, formule de score 0–5 sur la ligne source)
    ("Coût", 25, "cost"),
    ("Latence p95", 20, "latency"),
    ("Qualité FR (WER)", 20, "wer"),
    ("RGPD", 25, "gdpr"),
    ("Intégration / pérennité", 10, "integration"),
]


def score_formula(kind: str, sheet: str, r: int) -> str:
    """Formule de score (0–5) d'un critère pour la ligne `r` de l'onglet `sheet`."""
    s = f"'{sheet}'!"
    match kind:
        case "cost":
            return (
                f"=IF(AND(ISNUMBER({s}J{r}),{s}J{r}>0),5*MIN({s}$J$2:$J$40)/{s}J{r},"
                f'IF({s}J{r}=0,5,""))'
            )
        case "latency":
            return f'=IF(ISNUMBER({s}N{r}),5*MIN({s}$N$2:$N$40)/{s}N{r},"")'
        case "wer":
            return f'=IF(ISNUMBER({s}R{r}),MAX(0,5-25*{s}R{r}),"")'
        case "gdpr":
            return (
                f'=IF({s}AB{r}="Oui",2,0)'
                f'+IF(OR({s}X{r}="Oui",{s}X{r}="Sans objet",LEFT({s}X{r},3)="Oui",LEFT({s}X{r},8)="Mentionn"),1.5,0)'
                f'+IF(OR(LEFT({s}V{r},3)="Non",{s}V{r}="Sans objet"),1.5,'
                f'IF(ISNUMBER(SEARCH("opt-out",{s}V{r})),0.75,0))'
            )
        case "integration":
            return f'=IF({s}AE{r}="Oui",1,IF(ISNUMBER(SEARCH("officiel",{s}Z{r})),5,4))'
    raise ValueError(kind)


def sheet_scoring(wb: Workbook, by_cat: dict[str, list[Provider]]) -> None:
    """Onglet Scoring : pondérations modifiables, scores et total en formules."""
    ws = wb.create_sheet("Scoring")
    ws.cell(row=1, column=1, value="Pondérations (modifiables)").font = Font(bold=True)
    for i, (name, weight, _) in enumerate(CRITERIA):
        ws.cell(row=2, column=2 + i, value=name).font = Font(bold=True)
        w = ws.cell(row=3, column=2 + i, value=weight)
        w.fill = INPUT_FILL
    ws.cell(row=3, column=1, value="Poids")
    ws.cell(
        row=4,
        column=1,
        value=(
            "Règles : coût = 5 × moins cher / coût ; latence = 5 × meilleur p95 / p95 (mesuré) ; "
            "WER = 5 − 25 × WER ; RGPD = UE 2 + DPA 1,5 + pas d'entraînement 1,5 (opt-out 0,75) ; "
            "intégration = SDK officiel 5, sinon 4, fin de vie annoncée 1. Critère vide = exclu ; "
            "classement seulement si au moins 3 critères sont renseignés (sinon « non classé »)."
        ),
    )
    titles = [("Catégorie", 12), ("Clé", 24), ("Fournisseur / modèle", 36)]
    titles += [(c[0], 12) for c in CRITERIA] + [
        ("Score pondéré /5", 12),
        ("Critères renseignés", 12),
        ("Score classable", 12),
        ("Rang catégorie", 10),
    ]
    header(ws, titles, row=6)
    r = 7
    first_rows: dict[str, tuple[int, int]] = {}
    for cat in SCORED:
        start = r
        for idx, p in enumerate(by_cat[cat], start=2):
            ws.cell(row=r, column=1, value=cat)
            ws.cell(row=r, column=2, value=p.key)
            ws.cell(row=r, column=3, value=f"{p.vendor} — {p.model}")
            for i, (_, _, kind) in enumerate(CRITERIA):
                c = ws.cell(row=r, column=4 + i, value=score_formula(kind, SHEET_NAMES[cat], idx))
                c.number_format = "0.00"
            first = get_column_letter(4)
            last = get_column_letter(3 + len(CRITERIA))
            weights = f"$B$3:${get_column_letter(1 + len(CRITERIA))}$3"
            scores = f"{first}{r}:{last}{r}"
            weighted = (
                f"=IFERROR(SUMPRODUCT({weights},IFERROR({scores}*1,0))"
                f'/SUMPRODUCT({weights},--ISNUMBER({scores})),"")'
            )
            ws.cell(row=r, column=4 + len(CRITERIA), value=weighted).number_format = "0.00"
            ws.cell(row=r, column=5 + len(CRITERIA), value=f"=COUNT({first}{r}:{last}{r})")
            r += 1
        first_rows[cat] = (start, r - 1)
    score_col = get_column_letter(4 + len(CRITERIA))
    count_col = get_column_letter(5 + len(CRITERIA))
    elig_col = get_column_letter(6 + len(CRITERIA))
    for a, b in first_rows.values():
        for row in range(a, b + 1):
            ws.cell(
                row=row,
                column=6 + len(CRITERIA),
                value=f'=IF({count_col}{row}>=3,{score_col}{row},"non classé")',
            ).number_format = "0.00"
            ws.cell(
                row=row,
                column=7 + len(CRITERIA),
                value=f'=IF(ISNUMBER({elig_col}{row}),RANK({elig_col}{row},${elig_col}${a}:${elig_col}${b}),"")',
            )


def sheet_kpis(wb: Workbook, summary: dict[str, dict[str, str]]) -> None:
    """Onglet KPIs retenus."""
    ws = wb.create_sheet("KPIs")
    header(
        ws,
        [
            ("ID", 6),
            ("KPI", 30),
            ("Définition / calcul", 60),
            ("Cible", 22),
            ("Lien", 12),
            ("Valeur pré-production", 30),
        ],
    )
    measured_llm = summary.get("mistral_small_4", {}).get("mode") == "live"
    kpis = [
        (
            "K1",
            "Latence p95 bout-en-bout",
            "p95 de (fin d'envoi → image affichée) sur 100 rêves",
            "≤ 30 s",
            "CS-02 / ENF-01",
            "Somme des p95 par étape (onglets catégorie)" if measured_llm else NOT_MEASURED,
        ),
        (
            "K2",
            "Coût par rêve",
            "Σ api_calls.cost_usd / nombre de rêves",
            "≤ 0,05 $",
            "CS-03 / ADR-007",
            "='Coût 10 rêves-jour'!H2",
        ),
        (
            "K3",
            "WER français",
            "WER (jiwer) des transcriptions vs références du corpus",
            "≤ 10 %",
            "ADR-002",
            "Onglet STT, colonne R"
            if any(s.get("category") == "STT" and s.get("mode") == "live" for s in summary.values())
            else NOT_MEASURED,
        ),
        (
            "K4",
            "Taux d'échec API",
            "Appels en erreur après retries / appels, par fournisseur",
            "≤ 2 %",
            "CS-05 / ENF-03",
            "Onglets catégorie, colonne P" if summary else NOT_MEASURED,
        ),
        (
            "K5",
            "Taux de rejet filtre sécurité",
            "Images refusées par le filtre fournisseur / demandes",
            "≤ 5 % (H8)",
            "US-07",
            "NON MESURÉ — pas de clé T2I",
        ),
        (
            "K6",
            "Part des traitements dans l'UE",
            "Appels vers un endpoint UE / appels totaux",
            "100 % au MVP",
            "CS-04",
            "Par construction du scénario S1 (onglet Coût, colonne Fournisseurs)",
        ),
        (
            "K7",
            "Taux de sortie structurée valide",
            "Réponses LLM conformes à DreamAnalysis / réponses",
            "≥ 99 %",
            "ADR-003",
            "Onglet LLM, colonne P (erreurs = schéma invalide)" if measured_llm else NOT_MEASURED,
        ),
        (
            "K8",
            "Accord émotion modèle / utilisateur",
            "Rêves dont l'émotion n'est pas corrigée / rêves",
            "≥ 80 %",
            "US-14",
            "Mesurable en bêta (R2)",
        ),
    ]
    for r, row in enumerate(kpis, start=2):
        for c, v in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=v).alignment = WRAP
    ws["F3"].number_format = "0.0000 $"


def sheet_sources(wb: Workbook, consulted: str, providers: list[Provider]) -> None:
    """Onglet Sources : chaque URL consultée et sa date."""
    ws = wb.create_sheet("Sources")
    header(
        ws,
        [
            ("Fournisseur / modèle", 40),
            ("Information", 22),
            ("URL", 90),
            ("Consulté le", 12),
            ("Statut", 12),
        ],
    )
    rows: list[tuple[str, str, str, str]] = []
    for p in providers:
        label = f"{p.vendor} — {p.model}"
        rows.append((label, "Prix", p.url, p.status))
        for field, info in (
            ("data_location_url", "Localisation"),
            ("training_url", "Entraînement"),
            ("retention_url", "Rétention / ZDR"),
            ("dpa_url", "DPA"),
            ("rate_limit_url", "Quota"),
            ("fr_quality_url", "Voix FR"),
        ):
            url = str(p.extra.get(field, ""))
            if url:
                rows.append((label, info, url, "SOURCÉ"))
    for r, (label, info, url, status) in enumerate(rows, start=2):
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=info)
        ws.cell(row=r, column=3, value=url)
        ws.cell(row=r, column=4, value=consulted)
        ws.cell(row=r, column=5, value=status)


def main() -> None:
    """Construit le classeur."""
    consulted, providers = load_catalog()
    h = load_hypotheses()
    summary: dict[str, dict[str, str]] = {}
    sources = []
    for pattern in ("summary_local_*.csv", "summary_live_*.csv"):
        found = latest(pattern)
        if found:
            sources.append(found.name)
            for key, row in read_rows(found).items():
                row["source"] = found.name
                summary[key] = row
    live = latest("summary_live_*.csv") or latest("summary_local_*.csv")
    wer = read_rows(latest("wer_*.csv"))
    by_cat = {c: [p for p in providers if p.category == c] for c in CATEGORIES}
    wb = Workbook()
    sheet_readme(wb, consulted, live)
    sheet_hypotheses(wb, h)
    for cat in CATEGORIES:
        sheet_category(wb, cat, by_cat[cat], summary, wer)
    sheet_costs(wb, h, {p.key: p for p in providers})
    sheet_scoring(wb, by_cat)
    sheet_kpis(wb, summary)
    sheet_sources(wb, consulted, providers)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"→ {OUT} ({'mesures ' + live.name if live else NOT_MEASURED})")


if __name__ == "__main__":
    main()
