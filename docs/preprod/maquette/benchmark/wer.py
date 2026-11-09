"""Calcule le WER des transcriptions STT mesurées (mode live) contre les références.

Usage : python benchmark/wer.py [benchmark/results/latency_live_<horodatage>.csv]
Sans argument : dernier fichier live. Écrit benchmark/results/wer_<horodatage>.csv.
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import jiwer

HERE = Path(__file__).resolve().parent
REFS = HERE / "corpus" / "references"
RESULTS = HERE / "results"


def normalize(text: str) -> str:
    """Minuscules, apostrophes unifiées, ponctuation retirée, espaces compactés."""
    text = unicodedata.normalize("NFC", text.lower()).replace("’", "'")
    text = re.sub(r"[^\w\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    """Agrège le WER par fournisseur STT."""
    files = sorted(
        [*RESULTS.glob("latency_live_*.csv"), *RESULTS.glob("latency_local_*.csv")],
        key=lambda f: f.stat().st_mtime,
    )
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else (files[-1] if files else None)
    if path is None:
        print("Aucun résultat live : le WER n'est pas mesurable en mode mock.", file=sys.stderr)
        return 2
    refs = {p.stem: normalize(p.read_text("utf-8")) for p in REFS.glob("*.txt")}
    per_provider: dict[str, tuple[list[str], list[str]]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["category"] != "STT" or row["ok"] != "True":
                continue
            hyps, truths = per_provider.setdefault(row["provider"], ([], []))
            hyps.append(normalize(row["output_text"]))
            truths.append(refs[row["item_id"]])
    rows = [
        {"provider": k, "source": path.name, "utterances": len(h), "wer": round(jiwer.wer(t, h), 4)}
        for k, (h, t) in sorted(per_provider.items())
    ]
    if not rows:
        print("Aucune transcription STT réussie dans ce fichier.", file=sys.stderr)
        return 1
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"wer_{stamp}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(f"{r['provider']:28} WER={r['wer']:.2%} ({r['utterances']} énoncés)")
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
