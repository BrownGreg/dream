"""Crée les comptes du test de charge, chacun avec quelques rêves déjà traités."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    """Prépare ``charge-001@example.org`` … ``charge-NNN@example.org``."""

    help = "Crée les comptes du test de charge (données synthétiques)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Déclare les options."""
        parser.add_argument("--count", type=int, default=60)
        parser.add_argument("--dreams", type=int, default=8)
        parser.add_argument("--password", default="charge-Reves-2026")
        parser.add_argument("--force", action="store_true", help="Autorise l'exécution hors DEBUG.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Crée les comptes via ``seed_demo``."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusé hors DEBUG : ajoutez --force si c'est bien voulu.")
        for i in range(1, options["count"] + 1):
            call_command(
                "seed_demo",
                email=f"charge-{i:03d}@example.org",
                password=options["password"],
                dreams=options["dreams"],
                seed=i,
                force=True,
                stdout=open("/dev/null", "w"),  # noqa: SIM115 - silence volontaire
            )
        self.stdout.write(self.style.SUCCESS(f"{options['count']} comptes de charge créés"))
