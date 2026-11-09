"""Historique : liste, filtre par émotion, frise, tendance, export, effacement (US-09 à US-17)."""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _shared

from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import AssetKind

st.set_page_config(page_title="Mes rêves", page_icon="📔")
st.title("📔 Mes rêves")
_shared.consent_banner()

repo = _shared.repository()
if len(repo) == 0:
    st.info("Aucun rêve pour l'instant.")
    st.page_link("pages/1_Nouveau_reve.py", label="Raconter un rêve", icon="🎙️")
    st.stop()

selected = st.multiselect(
    "Filtrer par émotion", list(Emotion), format_func=lambda e: f"{e.icon} {e.value}"
)
dreams = repo.history(set(selected) or None)

frame = pd.DataFrame(
    [
        {
            "date": d.created_at,
            "titre": d.title or "Sans titre",
            "émotion": d.emotion.emotion.value if d.emotion else "non classée",
        }
        for d in dreams
    ]
)
if not frame.empty:
    st.subheader("Frise")
    colors = alt.Scale(
        domain=[e.value for e in Emotion] + ["non classée"],
        range=[e.color for e in Emotion] + ["#A0AEC0"],
    )
    chart = (
        alt.Chart(frame)
        .mark_circle(size=160)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("émotion:N", title=None),
            color=alt.Color("émotion:N", scale=colors, legend=None),
            tooltip=["titre", "date"],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)

monthly = repo.monthly_emotions()
if monthly:
    with st.expander("Tendances par mois"):
        table = pd.DataFrame(
            {
                month: {e.value: counts.get(e, 0) for e in Emotion}
                for month, counts in monthly.items()
            }
        )
        st.bar_chart(table.T)
        st.caption(_shared.MEDICAL_DISCLAIMER)

st.subheader(f"{len(dreams)} rêve(s)")
for dream in dreams:
    label = f"{dream.created_at:%d/%m/%Y %H:%M} — {dream.title or 'Sans titre'}"
    with st.expander(label):
        if dream.emotion:
            _shared.emotion_badge(dream.emotion.emotion)
        if dream.transcription:
            st.write(dream.transcription.text)
        for asset in dream.assets:
            if asset.kind is AssetKind.IMAGE:
                st.image(asset.uri, caption=_shared.AI_LABEL, width=320)
        if st.button("Supprimer définitivement", key=f"del-{dream.id}"):
            repo.delete(dream.id)
            st.toast("Rêve et fichiers associés supprimés.")
            st.rerun()

st.divider()
st.download_button(
    "Exporter mes rêves (JSON)",
    data=repo.export().model_dump_json(indent=2),
    file_name="mes_reves.json",
    mime="application/json",
)
with st.expander("Supprimer tout mon journal"):
    st.write("Tous vos rêves et fichiers seront effacés. Cette action est irréversible.")
    if st.button("Je confirme la suppression", type="primary"):
        repo.delete_all()
        st.session_state.pop("last", None)
        st.rerun()
