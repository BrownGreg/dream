"""État de session et composants communs aux pages de la maquette.

Aucune logique métier ici : tout passe par `dreamsynth` (pipeline, dépôt, services).
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import ConsentScope
from dreamsynth.labels import AI_LABEL, MEDICAL_DISCLAIMER
from dreamsynth.repository import DreamRepository
from dreamsynth.services.factory import build_services
from dreamsynth.services.mock import Failure
from dreamsynth.services.ports import Services

load_dotenv()

__all__ = ["AI_LABEL", "MEDICAL_DISCLAIMER"]

CONSENT_LABELS: dict[ConsentScope, str] = {
    ConsentScope.TRANSCRIPTION: (
        "J'accepte que ma voix soit transcrite par Mistral AI (hébergement UE). "
        "L'audio est supprimé dès la transcription."
    ),
    ConsentScope.IMAGE: (
        "J'accepte qu'une description reformulée de mon rêve, sans la transcription, "
        "soit envoyée à Black Forest Labs (UE) pour générer une image."
    ),
    ConsentScope.EMOTION_TRACKING: (
        "J'accepte que l'émotion de mes rêves soit classée et conservée pour suivre son "
        "évolution (indicateur personnel, sans valeur médicale)."
    ),
}
CONSENT_TEXT_VERSION = "2026-11-06"


def repository() -> DreamRepository:
    """Historique de la session (créé au premier accès)."""
    if "repo" not in st.session_state:
        st.session_state.repo = DreamRepository()
    repo: DreamRepository = st.session_state.repo
    return repo


def consents() -> frozenset[ConsentScope]:
    """Consentements actuellement donnés."""
    return repository().consents


def services(failure: Failure = Failure.NONE) -> Services:
    """Adapters choisis par l'environnement, avec panne simulée éventuelle."""
    return build_services(failure=failure)


def consent_banner() -> None:
    """Bandeau visible sur chaque page : état du consentement et lien vers les réglages."""
    if ConsentScope.TRANSCRIPTION in consents():
        scopes = ", ".join(sorted(s.value for s in consents()))
        st.caption(f"🔒 Consentements actifs : {scopes} — modifiables depuis l'accueil.")
    else:
        st.warning(
            "Consentement requis avant tout traitement : donnez-le depuis la page d'accueil.",
            icon="🔒",
        )


def emotion_badge(emotion: Emotion, source_label: str = "") -> None:
    """Icône et couleur de l'émotion."""
    suffix = f" <small>({source_label})</small>" if source_label else ""
    st.markdown(
        f"<span style='font-size:1.4rem'>{emotion.icon}</span> "
        f"<span style='color:{emotion.color};font-weight:600'>{emotion.value}</span>{suffix}",
        unsafe_allow_html=True,
    )
