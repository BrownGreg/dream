"""Crée un compte de démonstration rempli de rêves synthétiques (jamais de vrais récits).

Usage : ``uv run python manage.py seed_demo --email demo@example.org --dreams 60``.
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from accounts.models import Consent, User
from dreams.models import ApiCall, Dream, EmotionAnalysis, GeneratedAsset, Transcription
from dreams.services.adapters.fake import FAKE_DREAMS, FakeImageGenerator, FakePromptBuilder
from dreams.services.adapters.lexicon import LexiconEmotionClassifier
from dreams.services.ports import Caller


class Command(BaseCommand):
    """Remplit un compte de démonstration."""

    help = "Crée un utilisateur de démonstration et des rêves synthétiques sur 12 mois."

    def add_arguments(self, parser: CommandParser) -> None:
        """Déclare les options de la commande."""
        parser.add_argument("--email", default="demo@example.org")
        parser.add_argument("--password", default="demo-Reves-2026")
        parser.add_argument("--dreams", type=int, default=60)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--force", action="store_true", help="Autorise l'exécution hors DEBUG.")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        """Crée (ou recrée) le compte et ses rêves."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusé hors DEBUG : ajoutez --force si c'est bien voulu.")
        # Données préparées : ni latence ni panne simulées (réservées au test de charge lui-même).
        with override_settings(AI_FAKE_LATENCY_MS=0, AI_FAKE_FAIL_STEPS=[]):
            self._seed(options)

    def _seed(self, options: dict[str, Any]) -> None:
        rng = random.Random(options["seed"])  # noqa: S311 - données de démo reproductibles, pas de sécurité
        User.objects.filter(email=options["email"]).delete()
        user = User.objects.create_user(options["email"], options["password"])
        for scope in Consent.Scope.values:
            Consent.objects.create(user=user, scope=scope, granted=True, text_version=settings.CONSENT_TEXT_VERSION)
        now = timezone.now()
        caller = Caller()
        for i in range(options["dreams"]):
            text = rng.choice(FAKE_DREAMS)
            emotion = LexiconEmotionClassifier().classify(text, caller).emotion
            dream = Dream.objects.create(user=user, status=Dream.Status.DONE, audio_purged_at=now)
            created = now - timedelta(days=rng.randint(0, 364), hours=rng.randint(0, 5))
            visual = FakePromptBuilder().build(text, emotion, caller)
            Dream.objects.filter(pk=dream.pk).update(created_at=created, title=visual.title)
            Transcription.objects.create(dream=dream, text=text, provider="fake", model="fake-stt")
            EmotionAnalysis.objects.create(dream=dream, emotion=emotion, confidence=Decimal("0.80"), provider="fake")
            image = FakeImageGenerator().generate(f"{visual.prompt} #{i}", caller)
            asset = GeneratedAsset(dream=dream, kind="image", status="ok", visual_prompt=visual.prompt)
            asset.file.save(f"image.{image.extension}", ContentFile(image.data), save=True)
        # Les adapters fake journalisent leurs appels : on les retire, ce ne sont pas des appels du service.
        ApiCall.objects.filter(provider="fake", dream__isnull=True, created_at__gte=now).delete()
        self.stdout.write(self.style.SUCCESS(f"{options['dreams']} rêves créés pour {user.email}"))
