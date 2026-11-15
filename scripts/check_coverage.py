"""Vérifie la couverture **par module critique**, pas seulement en global.

Lit ``coverage.json`` (``coverage json``) et échoue si un module de la liste
tombe sous son seuil. La liste suit ``docs/tests/strategie.md``.

Usage:
    uv run python scripts/check_coverage.py [chemin/vers/coverage.json]
"""

import json
import sys
from fnmatch import fnmatch
from pathlib import Path

THRESHOLD = 70.0

# Fonctionnalités critiques (sujet) → motifs de fichiers. Un motif sans fichier
# correspondant est signalé : la liste doit rester alignée sur le code réel.
CRITICAL: dict[str, list[str]] = {
    "Authentification et consentement": ["accounts/forms.py", "accounts/services.py", "accounts/views.py"],
    "Santé de l'application": ["config/views.py"],
    "Observabilité (journaux, Sentry, /ops)": ["config/observability.py", "config/middleware.py", "dashboard/ops.py"],
    "Garde-fou budget et quotas": ["dreams/services/budget.py", "dreams/services/pricing.py"],
    "Client résilient (timeouts, retries)": ["dreams/services/http.py", "dreams/services/errors.py"],
    "Données sensibles chiffrées": ["dreams/fields.py"],
    "Upload et validation audio": ["dreams/audio.py", "dreams/forms.py"],
    "Stockage et accès aux fichiers": ["dreams/storage.py", "dreams/views.py"],
    "Suppression et export RGPD": ["dreams/deletion.py", "accounts/gdpr.py"],
    "Tableau de bord : historique, filtres, statistiques": [
        "dashboard/forms.py",
        "dashboard/queries.py",
        "dashboard/views.py",
        "dashboard/stats.py",
    ],
    "Pipeline et reprise par étape": ["dreams/pipeline.py", "dreams/tasks.py", "dreams/locks.py"],
    "Pipeline IA : adapters": [
        "dreams/services/adapters/*.py",
        "dreams/services/registry.py",
        "dreams/services/emotion.py",
    ],
}


def main(path: str = "coverage.json") -> int:
    """Calcule la couverture agrégée de chaque fonctionnalité critique.

    Args:
        path: Rapport JSON produit par ``coverage json``.

    Returns:
        ``0`` si chaque fonctionnalité atteint le seuil, ``1`` sinon.
    """
    files = json.loads(Path(path).read_text())["files"]
    failed = False
    print(f"{'Fonctionnalité critique':<40} {'Couverture':>10}  Fichiers")
    for feature, patterns in CRITICAL.items():
        matched = {name: data for name, data in files.items() if any(fnmatch(name, p) for p in patterns)}
        if not matched:
            print(f"{feature:<40} {'ABSENT':>10}  {', '.join(patterns)}")
            failed = True
            continue
        statements = sum(d["summary"]["num_statements"] + d["summary"].get("num_branches", 0) for d in matched.values())
        covered = sum(d["summary"]["covered_lines"] + d["summary"].get("covered_branches", 0) for d in matched.values())
        percent = 100.0 * covered / statements if statements else 100.0
        status = "OK " if percent >= THRESHOLD else "KO "
        failed |= percent < THRESHOLD
        print(f"{feature:<40} {percent:>9.1f}%  {status}{', '.join(sorted(matched))}")
    print(f"\nSeuil : {THRESHOLD:.0f} % par fonctionnalité critique.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
