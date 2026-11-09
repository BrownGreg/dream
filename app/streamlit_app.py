"""Accueil de la maquette : présentation et consentements granulaires (US-03)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _shared

from dreamsynth.domain.models import ConsentScope

st.set_page_config(page_title="Synthétiseur de rêves", page_icon="🌙", layout="centered")

st.title("🌙 Synthétiseur de rêves")
st.write(
    "Racontez votre rêve à voix haute : il est transcrit, illustré, accompagné d'une "
    "ambiance sonore et rangé dans votre journal. **Maquette de pré-production** : "
    "transcription et image sont simulées par défaut."
)

st.subheader("Vos consentements")
st.caption(
    f"Version du texte : {_shared.CONSENT_TEXT_VERSION}. Chaque finalité est séparée et "
    "révocable à tout moment ; refuser l'image ou le suivi n'empêche pas d'utiliser le journal."
)
current = _shared.consents()
with st.form("consents"):
    choices = {
        scope: st.checkbox(label, value=scope in current, key=f"consent_{scope.value}")
        for scope, label in _shared.CONSENT_LABELS.items()
    }
    submitted = st.form_submit_button("Enregistrer mes choix")
if submitted:
    _shared.repository().set_consents(frozenset(s for s, ok in choices.items() if ok))
    if ConsentScope.TRANSCRIPTION in _shared.consents():
        st.success("Choix enregistrés. Vous pouvez raconter un rêve.")
    else:
        st.info("Sans consentement à la transcription, aucun rêve ne peut être traité.")

_shared.consent_banner()
st.page_link("pages/1_Nouveau_reve.py", label="Raconter un rêve", icon="🎙️")
st.page_link("pages/2_Mes_reves.py", label="Mes rêves", icon="📔")

with st.expander("Ce que devient votre rêve"):
    st.markdown(
        "- **Audio** : supprimé dès la transcription (24 h au plus en cas d'échec).\n"
        "- **Émotion** : déduite du **texte** uniquement, jamais de votre voix.\n"
        "- **Image** : générée à partir d'une description reformulée, marquée « "
        f"{_shared.AI_LABEL} ».\n"
        "- **Aucune interprétation** psychologique ou médicale.\n"
        "- **Effacement** d'un rêve ou de tout votre journal depuis « Mes rêves »."
    )
