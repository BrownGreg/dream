"""Raconter un rêve : micro ou fichier, traitement par étapes, résultat (US-01 à US-11)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _shared

from dreamsynth.audio import AudioUpload
from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import AssetKind, Dream, EmotionSource
from dreamsynth.pipeline import (
    DreamRequest,
    GenerationOptions,
    ProcessResult,
    Step,
    correct_emotion,
    process_dream,
    regenerate_from_text,
)
from dreamsynth.services.mock import Failure

STEPS = list(Step)
FAILURE_LABELS = {
    Failure.NONE: "Aucune panne",
    Failure.STT_UNAVAILABLE: "Service de transcription indisponible",
    Failure.STT_TIMEOUT: "Délai de transcription dépassé",
    Failure.IMAGE_REJECTED: "Image refusée par le filtre de sécurité",
}

st.set_page_config(page_title="Nouveau rêve", page_icon="🎙️")
st.title("🎙️ Raconter un rêve")
_shared.consent_banner()

recorded = st.audio_input("Enregistrer au micro")
uploaded = st.file_uploader("… ou importer un fichier", type=["wav", "mp3"])
image_disabled = st.checkbox(
    "Ne pas générer d'image", help="Pour un rêve que vous ne voulez pas revoir."
)
style = st.selectbox("Style visuel", ["aucun", "aquarelle", "photo", "croquis"], index=0)
with st.expander("Mode démonstration : simuler une panne"):
    failure = st.selectbox(
        "Panne simulée", list(FAILURE_LABELS), format_func=lambda f: FAILURE_LABELS[f]
    )

upload: AudioUpload | None = None
if uploaded is not None:
    upload = AudioUpload(uploaded.name, uploaded.getvalue())
elif recorded is not None:
    upload = AudioUpload("micro.wav", recorded.getvalue())


def _options() -> GenerationOptions:
    return GenerationOptions(
        consents=_shared.consents(),
        image_disabled=image_disabled,
        style=None if style == "aucun" else style,
    )


def _run(audio: AudioUpload) -> None:
    progress = st.progress(0.0)
    with st.status("Traitement de votre rêve…", expanded=True) as status:

        def on_step(step: Step) -> None:
            progress.progress(STEPS.index(step) / len(STEPS), text=step.value)
            st.write(f"⏳ {step.value}")

        result = process_dream(DreamRequest(audio, _options()), _shared.services(failure), on_step)
        progress.progress(1.0, text="Terminé" if result.ok else "Interrompu")
        status.update(
            label="Rêve prêt" if result.ok else "Traitement interrompu",
            state="complete" if result.ok else "error",
            expanded=False,
        )
    st.session_state.last = result
    st.session_state.pending = audio if result.audio_retained else None
    if result.ok:
        _shared.repository().save(result.dream)


if st.button("Créer mon rêve", type="primary", disabled=upload is None) and upload is not None:
    _run(upload)


def _show_failure(result: ProcessResult) -> None:
    st.error(result.message or "Traitement impossible")
    pending: AudioUpload | None = st.session_state.get("pending")
    if result.retryable and pending is not None:
        st.caption("Votre enregistrement est conservé : vous pouvez relancer sans le refaire.")
        if st.button("Relancer le traitement"):
            _run(pending)
            st.rerun()
    else:
        st.caption("Réenregistrez votre récit ou choisissez un autre fichier.")


def _show_dream(dream: Dream, result: ProcessResult) -> None:
    st.subheader(dream.title or "Votre rêve")
    for warning in result.warnings:
        st.warning(warning)
    text = dream.transcription.text if dream.transcription else ""
    edited = st.text_area("Transcription (modifiable)", value=text, height=120)
    if edited.strip() and edited != text and st.button("Régénérer à partir du texte corrigé"):
        new = regenerate_from_text(dream, edited.strip(), _options(), _shared.services())
        _shared.repository().save(new.dream)
        st.session_state.last = new
        st.rerun()

    if dream.emotion is not None:
        source = "corrigée par vous" if dream.emotion.source is EmotionSource.USER else "proposée"
        _shared.emotion_badge(dream.emotion.emotion, source)
        options = list(Emotion)
        choice = st.selectbox(
            "Corriger l'émotion",
            options,
            index=options.index(dream.emotion.emotion),
            format_func=lambda e: f"{e.icon} {e.value}",
        )
        if choice is not dream.emotion.emotion:
            corrected = correct_emotion(dream, choice)
            _shared.repository().save(corrected)
            st.session_state.last = ProcessResult(corrected, warnings=result.warnings)
            st.rerun()
    else:
        st.caption("Émotion non classée : suivi des émotions non consenti.")

    for asset in dream.assets:
        if asset.kind is AssetKind.IMAGE:
            st.image(asset.uri, caption=_shared.AI_LABEL)
        elif asset.kind is AssetKind.AMBIANCE and Path(asset.uri).exists():
            st.caption("Ambiance sonore")
            st.audio(asset.uri, loop=True)
    if not any(a.kind is AssetKind.IMAGE for a in dream.assets) and dream.image_disabled:
        st.caption("Aucune image générée, comme demandé.")


last: ProcessResult | None = st.session_state.get("last")
if last is not None:
    st.divider()
    if last.ok:
        _show_dream(last.dream, last)
    else:
        _show_failure(last)
