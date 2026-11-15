"""Audit d'accessibilité axe-core (WCAG 2.2 A/AA) sur les pages clés, en mobile (DREAM-16).

Le rapport complet est écrit dans ``A11Y_REPORT`` s'il est défini (preuve versionnée
dans ``docs/tests/accessibilite/``).
"""

import json
import os
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.base import ContentFile

from dreams.models import Dream, GeneratedAsset
from tests.factories import DreamFactory, EmotionFactory, TranscriptionFactory, UserFactory

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

AXE = (Path(__file__).parent / "vendor" / "axe-4.14.0.min.js").read_text()
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
PASSWORD = "un-Mot-de-passe-solide-42"
AUDITED: list[tuple[str, str, int, list[str]]] = []
INCOMPLETE: list[dict] = []


@pytest.fixture
def browser_context_args(browser_context_args):
    # Mobile d'abord : récit dicté au réveil, au téléphone.
    return {**browser_context_args, "viewport": {"width": 390, "height": 844}, "locale": "fr-FR"}


def audit(page) -> list[dict]:
    page.add_script_tag(content=AXE)
    result = page.evaluate(f"axe.run(document, {{runOnly: {{type: 'tag', values: {TAGS}}}}})")
    # Garde-fou : l'audit doit avoir réellement évalué des règles sur la page.
    assert len(result["passes"]) > 10, page.url
    AUDITED.append((page.url, page.title(), len(result["passes"]), [i["id"] for i in result["incomplete"]]))
    INCOMPLETE.extend(
        {"page": page.url, "id": i["id"], "targets": [n["target"] for n in i["nodes"]][:5]}
        for i in result["incomplete"]
    )
    return [
        {
            "id": v["id"],
            "impact": v["impact"],
            "help": v["help"],
            "targets": [n["target"] for n in v["nodes"]][:5],
        }
        for v in result["violations"]
    ]


def test_pages_cles_sans_violation_wcag(page, live_server, login):
    user = UserFactory(email="a11y@example.org")
    dream = DreamFactory(user=user, status=Dream.Status.DONE, title="La ville de verre")
    TranscriptionFactory(dream=dream, text="Je volais au-dessus d'une ville de verre, la lumière était douce.")
    EmotionFactory(dream=dream, emotion="serein", confidence=Decimal("0.80"))
    asset = GeneratedAsset.objects.create(dream=dream, kind="image", status="ok")
    asset.file.save("image.svg", ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'))
    running = DreamFactory(user=user, status=Dream.Status.ANALYZING)

    anonymous = ["/comptes/connexion/", "/comptes/inscription/", "/comptes/mot-de-passe/oubli/"]
    private = [
        "/",
        "/statistiques/?periode=365",
        "/reves/nouveau/",
        f"/reves/{dream.id}/",
        f"/reves/{running.id}/",
        f"/reves/{dream.id}/supprimer/",
        "/comptes/mon-compte/",
    ]
    report: dict[str, list[dict]] = {}
    for path in anonymous:
        page.goto(live_server.url + path)
        assert "administration" not in page.title(), path
        report[path] = audit(page)
    login(user.email, PASSWORD)
    for path in private:
        page.goto(live_server.url + path)
        assert "/connexion/" not in page.url, f"redirigé vers la connexion : {path}"
        report[f"{path} (connecté)"] = audit(page)

    if os.environ.get("A11Y_REPORT"):
        summary = {
            "outil": "axe-core 4.14.0",
            "regles": TAGS,
            "viewport": "390x844",
            "pages": report,
            "a_verifier": INCOMPLETE,
            "conformes": [{"page": url, "regles_conformes": n} for url, _, n, _ in AUDITED],
        }
        Path(os.environ["A11Y_REPORT"]).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    for url, title, passes, incomplete in AUDITED:
        print(f"{url} | {title} | règles conformes : {passes} | à vérifier : {incomplete}")
    failures = {path: violations for path, violations in report.items() if violations}
    assert not failures, json.dumps(failures, ensure_ascii=False, indent=2)
    # Un contraste que axe ne peut pas mesurer (élément recouvert…) est traité comme un défaut.
    assert not INCOMPLETE, json.dumps(INCOMPLETE, ensure_ascii=False, indent=2)
