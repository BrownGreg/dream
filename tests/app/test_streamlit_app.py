"""Tests d'interface avec streamlit.testing.v1.AppTest — EXF-03, EXF-09, EXF-10, EXF-15, EXF-16.

AppTest ne simule ni le micro ni l'envoi de fichier : le parcours audio est couvert par les
scénarios BDD ; ici on vérifie ce que l'utilisateur voit et les garde-fous de l'UI.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import (
    AssetKind,
    ConsentScope,
    Dream,
    DreamStatus,
    EmotionAnalysis,
    GeneratedAsset,
    Transcription,
)
from dreamsynth.labels import AI_LABEL
from dreamsynth.pipeline import ProcessResult
from dreamsynth.repository import DreamRepository

APP = Path(__file__).resolve().parents[2] / "app"


def _dream(emotion: Emotion, days_ago: int, title: str) -> Dream:
    return Dream(
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
        status=DreamStatus.DONE,
        title=title,
        transcription=Transcription(text=f"Récit {title}", provider="mock", model="mock"),
        emotion=EmotionAnalysis(emotion=emotion, confidence=0.8),
        assets=(
            GeneratedAsset(
                kind=AssetKind.IMAGE,
                uri="https://picsum.photos/seed/test/768/768",
                provider="picsum",
                model="placeholder",
            ),
        ),
    )


@pytest.fixture
def repo_with_dreams() -> DreamRepository:
    repo = DreamRepository()
    repo.set_consents(frozenset(ConsentScope))
    repo.save(_dream(Emotion.HEUREUX, 2, "Gâteau"))
    repo.save(_dream(Emotion.STRESSANT, 1, "Couloir"))
    return repo


def test_home_shows_three_separate_consents() -> None:  # EXF-03
    at = AppTest.from_file(str(APP / "streamlit_app.py")).run()
    assert not at.exception
    assert len(at.checkbox) == 3
    assert any("Consentement requis" in w.value for w in at.warning)


def test_saving_consents_updates_banner() -> None:
    at = AppTest.from_file(str(APP / "streamlit_app.py")).run()
    at.checkbox[0].check()
    at.button[0].click().run()
    repo: DreamRepository = at.session_state["repo"]
    assert repo.consents == frozenset({ConsentScope.TRANSCRIPTION})
    assert any("Choix enregistrés" in s.value for s in at.success)


def test_new_dream_page_blocks_without_audio() -> None:  # EXF-10
    at = AppTest.from_file(str(APP / "pages" / "1_Nouveau_reve.py")).run()
    assert not at.exception
    create = next(b for b in at.button if b.label == "Créer mon rêve")
    assert create.disabled
    assert any("Consentement requis" in w.value for w in at.warning)


def test_result_shows_ai_label_and_emotion_selector(repo_with_dreams: DreamRepository) -> None:
    at = AppTest.from_file(str(APP / "pages" / "1_Nouveau_reve.py"))
    at.session_state["repo"] = repo_with_dreams
    at.session_state["last"] = ProcessResult(repo_with_dreams.history()[0])
    at.run()
    assert not at.exception
    assert any(sb.label == "Corriger l'émotion" for sb in at.selectbox)  # sélecteur simulé
    captions = [img.proto.imgs[0].caption for img in at.get("image")]
    assert captions == [AI_LABEL]  # EXF-09 : mention visible sous chaque image
    assert any("stressant" in m.value for m in at.markdown)  # icône + libellé de l'émotion


def test_failure_offers_retry_when_audio_is_kept() -> None:  # EXF-10
    at = AppTest.from_file(str(APP / "pages" / "1_Nouveau_reve.py"))
    failed = Dream(status=DreamStatus.FAILED, error="stt_unavailable")
    at.session_state["last"] = ProcessResult(
        failed, "Transcription indisponible, réessayez dans un instant", True, True
    )
    from dreamsynth.audio import AudioUpload
    from tests.conftest import make_wav

    at.session_state["pending"] = AudioUpload("micro.wav", make_wav(4))
    at.run()
    assert [e.value for e in at.error] == ["Transcription indisponible, réessayez dans un instant"]
    assert any(b.label == "Relancer le traitement" for b in at.button)


def test_history_lists_and_filters(repo_with_dreams: DreamRepository) -> None:  # EXF-15/16
    at = AppTest.from_file(str(APP / "pages" / "2_Mes_reves.py"))
    at.session_state["repo"] = repo_with_dreams
    at.run()
    assert not at.exception
    titles = [e.label for e in at.expander if "—" in e.label]
    assert titles[0].endswith("Couloir") and titles[1].endswith("Gâteau")  # plus récent d'abord
    at.multiselect[0].select(Emotion.HEUREUX).run()
    assert any(s.value == "1 rêve(s)" for s in at.subheader)


def test_history_delete_removes_dream(repo_with_dreams: DreamRepository) -> None:  # EXF-19
    at = AppTest.from_file(str(APP / "pages" / "2_Mes_reves.py"))
    at.session_state["repo"] = repo_with_dreams
    at.run()
    next(b for b in at.button if b.label == "Supprimer définitivement").click().run()
    assert len(at.session_state["repo"]) == 1


def test_empty_history_invites_to_record() -> None:
    at = AppTest.from_file(str(APP / "pages" / "2_Mes_reves.py")).run()
    assert any("Aucun rêve" in i.value for i in at.info)
