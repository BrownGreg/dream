"""Génère docs/schemas/dream.schema.json (JSON Schema 2020-12) depuis les modèles Pydantic.

Usage : python tools/export_schema.py [--check]
`--check` échoue si le fichier commité diffère du schéma généré (utilisé en CI).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dreamsynth.domain.models import SCHEMA_VERSION, DreamExport

OUT = Path(__file__).resolve().parents[1] / "docs" / "schemas" / "dream.schema.json"


def build() -> str:
    """Schéma sérialisé de l'export des rêves."""
    schema = DreamExport.model_json_schema(mode="serialization")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://dreamsynth.example/schemas/dream/{SCHEMA_VERSION}",
        **schema,
    }
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    """Écrit ou vérifie le schéma."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = build()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            print(
                "dream.schema.json n'est pas à jour : python tools/export_schema.py",
                file=sys.stderr,
            )
            return 1
        print("schéma à jour")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    print(f"→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
