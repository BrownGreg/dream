"""Fabriques factory_boy."""

import factory
from django.conf import settings

from accounts.models import Consent, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"reveur{n}@example.org")
    password = factory.PostGenerationMethodCall("set_password", "un-Mot-de-passe-solide-42")

    @factory.post_generation
    def consents(self, create, extracted, **kwargs):
        if not create:
            return
        self.save()
        image = True if extracted is None else extracted
        Consent.objects.create(
            user=self, scope=Consent.Scope.PROCESSING, granted=True, text_version=settings.CONSENT_TEXT_VERSION
        )
        Consent.objects.create(
            user=self, scope=Consent.Scope.IMAGE_GENERATION, granted=image, text_version=settings.CONSENT_TEXT_VERSION
        )


class DreamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "dreams.Dream"

    user = factory.SubFactory(UserFactory)


class TranscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "dreams.Transcription"

    dream = factory.SubFactory(DreamFactory)
    text = "Je volais au-dessus d'une ville de verre, la lumière était douce."
    provider = "fake"
    model = "fake-stt"


class EmotionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "dreams.EmotionAnalysis"

    dream = factory.SubFactory(DreamFactory)
    emotion = "serein"
    confidence = "0.80"
    provider = "fake"
