"""Exécution des critères d'acceptation Gherkin (générés depuis docs/backlog/stories.toml).

Chaque scénario porte l'étiquette de sa story (@US-xx) ; les étapes pilotent le cœur
métier (pipeline, dépôt, services), pas l'interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema
from pytest_bdd import given, parsers, scenarios, then, when

from dreamsynth.audio import MAX_BYTES, AudioUpload
from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import (
    AssetKind,
    ConsentScope,
    Dream,
    DreamStatus,
    EmotionAnalysis,
    EmotionSource,
    GeneratedAsset,
    Transcription,
)
from dreamsynth.labels import AI_LABEL, MEDICAL_DISCLAIMER
from dreamsynth.pipeline import (
    DreamRequest,
    GenerationOptions,
    ProcessResult,
    correct_emotion,
    process_dream,
    regenerate_from_text,
)
from dreamsynth.repository import DreamRepository
from dreamsynth.services.factory import build_services
from dreamsynth.services.mock import Failure, PlaceholderImageGenerator
from dreamsynth.services.ports import Services
from tests.conftest import CORPUS_MP3, DOCS, make_wav

SCHEMA = DOCS / "schemas" / "dream.schema.json"
SOURCES = {"utilisateur": EmotionSource.USER, "modèle": EmotionSource.MODEL}

scenarios(".")


@dataclass
class Context:
    """État partagé entre les étapes d'un scénario."""

    consents: frozenset[ConsentScope] = frozenset()
    failure: Failure = Failure.NONE
    image_disabled: bool = False
    style: str | None = None
    upload: AudioUpload | None = None
    result: ProcessResult | None = None
    services: Services | None = None
    dream: Dream | None = None
    text: str = ""
    repo: DreamRepository = field(default_factory=DreamRepository)
    shown: list[Dream] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def options(self) -> GenerationOptions:
        return GenerationOptions(self.consents, self.image_disabled, self.style)

    def run(self) -> ProcessResult:
        assert self.upload is not None
        self.services = build_services(env={}, failure=self.failure)
        self.result = process_dream(DreamRequest(self.upload, self.options()), self.services)
        if self.result.ok:
            self.repo.save(self.result.dream)
        return self.result


def _dream(emotion: Emotion, days_ago: int = 0) -> Dream:
    return Dream(
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
        status=DreamStatus.DONE,
        transcription=Transcription(text="un rêve", provider="mock", model="mock"),
        emotion=EmotionAnalysis(emotion=emotion),
        assets=(
            GeneratedAsset(
                kind=AssetKind.IMAGE,
                uri=f"s3://img/{emotion.name}-{days_ago}",
                provider="p",
                model="m",
            ),
        ),
    )


# ------------------------------------------------------------------ consentement et audio
@given("j'ai accepté le consentement", target_fixture="ctx")
def consent_given() -> Context:
    return Context(consents=frozenset(ConsentScope))


@given("je n'ai pas accepté le consentement", target_fixture="ctx")
def consent_refused() -> Context:
    return Context()


@when(parsers.re(r"j'enregistre un récit de (?P<seconds>\d+) secondes? au micro"))
def record(ctx: Context, seconds: str) -> None:
    ctx.upload = AudioUpload("micro.wav", make_wav(float(seconds)))
    ctx.run()


@when(parsers.parse("j'importe le fichier « {name} » de {size:d} Mo"))
def import_file(ctx: Context, name: str, size: int) -> None:
    if size * 1024 * 1024 > MAX_BYTES:
        data = b"\0" * (size * 1024 * 1024)
    elif name.endswith(".mp3"):
        data = CORPUS_MP3.read_bytes()
    elif name.endswith(".wav"):
        data = make_wav(45)
    else:
        data = b"OggS" + b"\0" * 1024
    ctx.upload = AudioUpload(name, data)
    ctx.run()


@then("l'audio est accepté pour traitement")
def audio_accepted(ctx: Context) -> None:
    assert ctx.result is not None and ctx.result.dream.audio is not None
    assert ctx.result.ok, ctx.result.message


@then(parsers.parse("je vois le message « {message} »"))
def message_shown(ctx: Context, message: str) -> None:
    assert ctx.result is not None and ctx.result.message == message


# ------------------------------------------------------------------ traitement
@given("j'ai soumis un récit valide")
def submitted(ctx: Context) -> None:
    ctx.upload = AudioUpload("micro.wav", make_wav(5))


@given("le service de transcription est indisponible")
def stt_down(ctx: Context) -> None:
    ctx.failure = Failure.STT_UNAVAILABLE


@given("le service de transcription dépasse le délai")
def stt_slow(ctx: Context) -> None:
    ctx.failure = Failure.STT_TIMEOUT


@given("le fournisseur d'image refuse le prompt", target_fixture="ctx")
def image_refused() -> Context:
    return Context(consents=frozenset(ConsentScope), failure=Failure.IMAGE_REJECTED)


@given("j'ai coché « Ne pas générer d'image »")
def no_image(ctx: Context) -> None:
    ctx.image_disabled = True


@given(parsers.parse("j'ai choisi le style « {style} »"), target_fixture="ctx")
def style_chosen(style: str) -> Context:
    return Context(consents=frozenset(ConsentScope), style=style)


@when("le traitement se termine")
@when("je soumets un récit valide")
def submit(ctx: Context) -> None:
    ctx.upload = ctx.upload or AudioUpload("micro.wav", make_wav(5))
    ctx.run()


@then("je vois une transcription non vide")
def transcription_shown(ctx: Context) -> None:
    assert ctx.result and ctx.result.dream.transcription and ctx.result.dream.transcription.text


@then("mon audio n'est pas perdu")
def audio_kept(ctx: Context) -> None:
    assert ctx.result is not None and ctx.result.audio_retained


@then("je peux relancer le traitement")
def can_retry(ctx: Context) -> None:
    assert ctx.result is not None and ctx.result.retryable and ctx.result.audio_retained
    ctx.failure = Failure.NONE
    assert ctx.run().ok


@then(parsers.parse("je vois une image accompagnée de la mention « {label} »"))
def image_shown(ctx: Context, label: str) -> None:
    assert ctx.result is not None
    images = [a for a in ctx.result.dream.assets if a.kind is AssetKind.IMAGE]
    assert images and all(a.ai_generated for a in images)
    assert label == AI_LABEL


@then("mon rêve est enregistré sans image")
def saved_without_image(ctx: Context) -> None:
    assert ctx.result is not None and ctx.result.ok
    assert ctx.repo.get(ctx.result.dream.id) is not None
    assert AssetKind.IMAGE not in {a.kind for a in ctx.result.dream.assets}


@then("aucun appel au générateur d'image n'est effectué")
def no_image_call(ctx: Context) -> None:
    assert ctx.services is not None
    image = ctx.services.image
    assert isinstance(image, PlaceholderImageGenerator) and image.calls == 0


@then("mon rêve est enregistré avec sa transcription et son émotion")
def saved_with_text_and_emotion(ctx: Context) -> None:
    assert ctx.result is not None
    stored = ctx.repo.get(ctx.result.dream.id)
    assert stored is not None and stored.transcription is not None and stored.emotion is not None


@then(parsers.parse("le prompt visuel contient le style « {style} »"))
def prompt_has_style(ctx: Context, style: str) -> None:
    assert ctx.result and ctx.result.dream.visual_prompt and style in ctx.result.dream.visual_prompt


# ------------------------------------------------------------------ transcription et émotion
@given(parsers.parse("une transcription « {text} »"), target_fixture="ctx")
def a_transcription(text: str) -> Context:
    ctx = Context(consents=frozenset(ConsentScope))
    ctx.upload = AudioUpload("micro.wav", make_wav(5))
    ctx.run()
    ctx.text = text
    return ctx


@when(parsers.parse("je la corrige en « {text} »"))
def correct_text(ctx: Context, text: str) -> None:
    assert ctx.result is not None and ctx.services is not None
    ctx.result = regenerate_from_text(ctx.result.dream, text, ctx.options(), ctx.services)


@then(parsers.parse("la génération utilise « {text} »"))
def generation_uses(ctx: Context, text: str) -> None:
    assert ctx.result and ctx.result.dream.visual_prompt and text in ctx.result.dream.visual_prompt


@given(parsers.parse("la transcription « {text} »"), target_fixture="ctx")
def the_transcription(text: str) -> Context:
    return Context(text=text)


@when("l'émotion est classée")
def classify_emotion(ctx: Context) -> None:
    ctx.extra["analysis"] = build_services(env={}).analyzer.analyze(ctx.text)


@then(parsers.parse("je vois l'émotion « {emotion} » avec son icône et sa couleur"))
def emotion_shown(ctx: Context, emotion: str) -> None:
    found = ctx.extra["analysis"].emotion
    assert found.value == emotion and found.icon and found.color


@given(parsers.parse("un rêve classé « {emotion} »"), target_fixture="ctx")
def classified_dream(emotion: str) -> Context:
    ctx = Context()
    ctx.dream = _dream(Emotion(emotion))
    ctx.repo.save(ctx.dream)
    return ctx


@when(parsers.parse("je choisis l'émotion « {emotion} »"))
def choose_emotion(ctx: Context, emotion: str) -> None:
    assert ctx.dream is not None
    ctx.dream = correct_emotion(ctx.dream, Emotion(emotion))
    ctx.repo.save(ctx.dream)


@then(
    parsers.parse("le rêve est enregistré avec l'émotion « {emotion} » et la source « {source} »")
)
def stored_emotion(ctx: Context, emotion: str, source: str) -> None:
    assert ctx.dream is not None
    stored = ctx.repo.get(ctx.dream.id)
    assert stored is not None and stored.emotion is not None
    assert stored.emotion.emotion is Emotion(emotion) and stored.emotion.source is SOURCES[source]


@when("j'ouvre le rêve")
def open_dream(ctx: Context) -> None:
    assert ctx.dream is not None and ctx.dream.emotion is not None
    ctx.extra["ambiance"] = build_services(env={}).ambiance.for_emotion(ctx.dream.emotion.emotion)


@then(parsers.parse("une ambiance sonore « {emotion} » est proposée en lecture"))
def ambiance_offered(ctx: Context, emotion: str) -> None:
    path = Path(ctx.extra["ambiance"])
    assert path.exists() and path.stem == Emotion(emotion).name.lower()


# ------------------------------------------------------------------ historique
@given(parsers.parse("j'ai enregistré {count:d} rêves"), target_fixture="ctx")
def saved_dreams(count: int) -> Context:
    ctx = Context()
    for days in range(count):
        ctx.repo.save(_dream(Emotion.NEUTRE, days))
    return ctx


@given(
    parsers.parse("j'ai enregistré {happy:d} rêves « heureux » et {stress:d} rêve « stressant »"),
    target_fixture="ctx",
)
def mixed_dreams(happy: int, stress: int) -> Context:
    ctx = Context()
    for i in range(happy):
        ctx.repo.save(_dream(Emotion.HEUREUX, i))
    for i in range(stress):
        ctx.repo.save(_dream(Emotion.STRESSANT, 10 + i))
    return ctx


@given("j'ai enregistré des rêves sur 2 mois", target_fixture="ctx")
def two_months() -> Context:
    ctx = Context()
    ctx.repo.save(_dream(Emotion.HEUREUX, 0))
    ctx.repo.save(_dream(Emotion.STRESSANT, 40))
    return ctx


@when("j'ouvre « Mes rêves »")
def open_history(ctx: Context) -> None:
    ctx.shown = ctx.repo.history()


@when(parsers.parse("je filtre sur « {emotion} »"))
def filter_history(ctx: Context, emotion: str) -> None:
    ctx.shown = ctx.repo.history({Emotion(emotion)})


@then(parsers.parse("je vois {count:d} rêves du plus récent au plus ancien"))
def history_sorted(ctx: Context, count: int) -> None:
    dates = [d.created_at for d in ctx.shown]
    assert len(dates) == count and dates == sorted(dates, reverse=True)


@then(parsers.parse("je vois {count:d} rêve"))
def history_count(ctx: Context, count: int) -> None:
    assert len(ctx.shown) == count


@when("j'ouvre la vue « Tendances »")
def open_trends(ctx: Context) -> None:
    ctx.extra["monthly"] = ctx.repo.monthly_emotions()


@then("je vois une répartition des émotions par mois")
def monthly_shown(ctx: Context) -> None:
    assert len(ctx.extra["monthly"]) == 2


@then(parsers.parse("je vois la mention « {label} »"))
def disclaimer_shown(label: str) -> None:
    assert label == MEDICAL_DISCLAIMER


# ------------------------------------------------------------------ contrôle des données
@given("un rêve avec transcription, émotion et image", target_fixture="ctx")
def full_dream() -> Context:
    ctx = Context()
    ctx.dream = _dream(Emotion.SEREIN)
    ctx.repo.save(ctx.dream)
    return ctx


@when("je le supprime")
def delete_dream(ctx: Context) -> None:
    assert ctx.dream is not None and ctx.repo.delete(ctx.dream.id)


@then("le rêve n'apparaît plus dans « Mes rêves »")
def not_listed(ctx: Context) -> None:
    assert ctx.dream is not None and ctx.dream.id not in {d.id for d in ctx.repo.history()}


@then("aucun fichier associé ne subsiste")
def no_file_left(ctx: Context) -> None:
    assert ctx.dream is not None and ctx.repo.files_of(ctx.dream.id) == []


@when("je demande l'export")
def export(ctx: Context) -> None:
    ctx.extra["export"] = json.loads(ctx.repo.export().model_dump_json())


@then(
    parsers.parse(
        "je reçois un fichier JSON valide contre « dream.schema.json » contenant {count:d} rêves"
    )
)
def export_valid(ctx: Context, count: int) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(ctx.extra["export"])
    assert len(ctx.extra["export"]["dreams"]) == count


@given(parsers.parse("un compte avec {count:d} rêves"), target_fixture="ctx")
def account(count: int) -> Context:
    ctx = saved_dreams(count)
    ctx.repo.set_consents(frozenset(ConsentScope))
    return ctx


@when("je supprime mon compte")
def delete_account(ctx: Context) -> None:
    ctx.repo.delete_all()


@then("aucun rêve, fichier ni consentement rattaché ne subsiste hors journal d'audit anonymisé")
def nothing_left(ctx: Context) -> None:
    assert len(ctx.repo) == 0 and ctx.repo.consents == frozenset()
    assert ctx.repo.audit[-1].action == "account.delete"
