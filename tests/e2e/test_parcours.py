"""Parcours complet dans Chromium : inscription → enregistrement au micro → résultat → historique (DREAM-19).

Le micro est simulé par Chromium (`--use-file-for-fake-audio-capture`) : MediaRecorder,
envoi `fetch`, validation serveur, pipeline (adapters fake) et polling HTMX sont réels.
"""

import re

import pytest
from playwright.sync_api import expect

from dreams.models import ApiCall, Dream

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 390, "height": 844}, "locale": "fr-FR"}


@pytest.fixture(autouse=True)
def fake_ai(settings):
    settings.AI_MODE = "fake"
    settings.AI_RETRY_BASE_SECONDS = 0


def test_inscription_enregistrement_resultat_historique(page, live_server):
    base = live_server.url
    # Inscription avec les deux consentements.
    page.goto(f"{base}/comptes/inscription/")
    page.fill("#id_email", "parcours@example.org")
    page.fill("#id_password1", "un-Mot-de-passe-solide-42")
    page.fill("#id_password2", "un-Mot-de-passe-solide-42")
    page.check("#id_consent_processing")
    page.check("#id_consent_image_generation")
    page.click("button[type=submit]")
    page.wait_for_url(f"{base}/")
    expect(page.get_by_role("heading", name="Mes rêves")).to_be_visible()

    # Enregistrement au micro (faux périphérique Chromium), réécoute, envoi.
    page.get_by_role("link", name="Raconter un rêve").first.click()
    record = page.locator("[data-rec-toggle]")
    expect(record).to_be_visible()
    record.click()
    expect(record).to_have_attribute("aria-pressed", "true")
    expect(page.locator("[data-rec-status]")).to_contain_text("Enregistrement en cours")
    page.wait_for_timeout(2500)
    record.click()
    expect(page.locator("[data-rec-review]")).to_be_visible()
    expect(page.locator("[data-rec-preview]")).to_have_attribute("src", re.compile(r"^blob:"))
    page.locator("[data-rec-send]").click()

    # Résultat : avancement puis page complète (rafraîchie par HTMX).
    page.wait_for_url(lambda url: "/reves/" in url and "/nouveau/" not in url)
    expect(page.get_by_text("Image générée par IA")).to_be_visible(timeout=15_000)
    expect(page.get_by_role("heading", name="Émotion dominante")).to_be_visible()
    expect(page.get_by_text("L'enregistrement audio a été supprimé")).to_be_visible()

    dream = Dream.objects.get(user__email="parcours@example.org")
    assert dream.status == "done"
    assert dream.audio_mime in ("video/webm", "audio/webm", "audio/ogg")
    assert dream.audio_duration_s > 1
    steps = set(ApiCall.objects.filter(dream=dream).values_list("step", flat=True))
    assert steps == {"stt", "emotion", "prompt", "image"}

    # Historique : le rêve apparaît avec sa vignette, et le filtre par humeur le retrouve.
    page.goto(f"{base}/")
    card = page.locator("#dream-list li").first
    expect(card).to_contain_text(dream.title)
    expect(card.locator("img")).to_be_visible()
    page.get_by_text("Filtrer").click()
    page.locator(f"input[name=humeur][value={dream.current_emotion.emotion}]").check()
    expect(page).to_have_url(re.compile(r"humeur="))
    expect(page.locator("#dream-list li")).to_have_count(1)


def test_micro_refuse_propose_l_import(page, live_server, browser):
    from tests.factories import UserFactory

    UserFactory(email="sansmicro@example.org")
    context = browser.new_context(viewport={"width": 390, "height": 844}, permissions=[])
    page = context.new_page()
    page.add_init_script(
        "navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('refus', 'NotAllowedError'));"
    )
    page.goto(f"{live_server.url}/comptes/connexion/")
    page.fill("#id_username", "sansmicro@example.org")
    page.fill("#id_password", "un-Mot-de-passe-solide-42")
    page.click("button[type=submit]")
    page.goto(f"{live_server.url}/reves/nouveau/")
    page.locator("[data-rec-toggle]").click()
    expect(page.locator("[data-rec-status]")).to_contain_text("L'accès au micro a été refusé")
    expect(page.get_by_text("Importer un fichier audio")).to_be_visible()
    context.close()
