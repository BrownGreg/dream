"""Échantillonne la file de tâches pendant un test de charge.

Écrit ``horodatage,secondes,prêtes,en_cours,attente_max_s`` toutes les ``--every`` secondes
jusqu'à interruption. Usage : ``uv run python scripts/sample_queue.py load-results/file.csv``.
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")


def main() -> None:
    """Boucle d'échantillonnage."""
    import django

    django.setup()
    from django.utils import timezone

    from dashboard.ops import queue_state

    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--every", type=float, default=2.0)
    args = parser.parse_args()
    start = time.monotonic()
    with Path(args.output).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "elapsed_s", "ready", "running", "oldest_wait_s"])
        while True:
            state = queue_state()
            writer.writerow(
                [
                    timezone.now().isoformat(),
                    round(time.monotonic() - start, 1),
                    state.ready,
                    state.running,
                    state.oldest_wait_s,
                ]
            )
            handle.flush()
            time.sleep(args.every)


if __name__ == "__main__":
    main()
