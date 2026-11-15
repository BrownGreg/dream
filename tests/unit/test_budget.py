"""Coupe-circuit et quota quotidien (ADR-009)."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from dreams.models import ApiCall, Dream
from dreams.services import budget, pricing
from dreams.services.errors import BudgetExceededError, ProviderError, QuotaExceededError
from tests.factories import DreamFactory

pytestmark = pytest.mark.django_db
PARIS = ZoneInfo("Europe/Paris")


def _spend(usd: str):
    ApiCall.objects.create(step="image", provider="bfl", model="flux-2-klein", outcome="ok", cost_usd=usd)


def test_budget_vide():
    status = budget.budget_status()
    assert status.spent_eur == 0
    assert not status.alert
    assert not status.exceeded


def test_alerte_a_80_pourcent_et_conversion(settings):
    settings.AI_BUDGET_EUR = 10
    settings.AI_USD_EUR_RATE = 0.9
    _spend("9.00")  # 8,10 €
    status = budget.budget_status()
    assert status.spent_eur == Decimal("8.1000")
    assert status.ratio == Decimal("0.8100")
    assert status.alert
    assert not status.exceeded


def test_depassement_atteint(settings):
    settings.AI_BUDGET_EUR = 1
    _spend("1.00")
    assert budget.budget_status().exceeded
    with pytest.raises(BudgetExceededError):
        budget.ensure_budget()


def test_un_appel_qui_ferait_depasser_est_refuse(settings):
    settings.AI_BUDGET_EUR = 1
    _spend("0.99")
    budget.ensure_budget(Decimal("0.01"))
    with pytest.raises(BudgetExceededError):
        budget.ensure_budget(Decimal("0.02"))


def test_budget_nul_toujours_depasse(settings):
    settings.AI_BUDGET_EUR = 0
    assert budget.budget_status().ratio == 1


def test_quota_quotidien(settings, user):
    settings.AI_USER_DAILY_DREAMS = 2
    DreamFactory.create_batch(2, user=user)
    DreamFactory()  # un autre utilisateur ne compte pas
    with pytest.raises(QuotaExceededError) as exc:
        budget.ensure_user_quota(user.id)
    assert exc.value.resets_at.hour == 0
    assert exc.value.code == "quota_exceeded"


@pytest.mark.parametrize("code", sorted(budget.SERVICE_FAILURE_CODES))
def test_echec_du_service_ne_consomme_pas_le_quota(settings, user, code):
    settings.AI_USER_DAILY_DREAMS = 1
    DreamFactory(user=user, status=Dream.Status.FAILED, error_code=code)
    budget.ensure_user_quota(user.id)


def test_echec_imputable_a_l_enregistrement_consomme_le_quota(settings, user):
    # Transcription facturée : le rêve compte, même sans parole reconnue.
    settings.AI_USER_DAILY_DREAMS = 1
    DreamFactory(user=user, status=Dream.Status.FAILED, error_code="transcription_empty")
    with pytest.raises(QuotaExceededError):
        budget.ensure_user_quota(user.id)


def test_reve_en_cours_consomme_le_quota(settings, user):
    settings.AI_USER_DAILY_DREAMS = 1
    DreamFactory(user=user, status=Dream.Status.RECEIVED)
    with pytest.raises(QuotaExceededError):
        budget.ensure_user_quota(user.id)


def test_quota_remis_a_zero_a_minuit_heure_de_paris(settings, user):
    settings.AI_USER_DAILY_DREAMS = 1
    dream = DreamFactory(user=user)
    Dream.objects.filter(pk=dream.pk).update(created_at=datetime(2026, 11, 9, 23, 30, tzinfo=PARIS))
    budget.ensure_user_quota(user.id, now=datetime(2026, 11, 10, 0, 5, tzinfo=PARIS))
    with pytest.raises(QuotaExceededError):
        budget.ensure_user_quota(user.id, now=datetime(2026, 11, 9, 23, 59, tzinfo=PARIS))


def test_quota_reset_at_par_defaut_dans_le_futur():
    assert budget.quota_reset_at() > timezone.now()


def test_prix_et_statuts():
    assert pricing.price_for("fake", "x").usd_per_unit == 0
    assert pricing.price_for("huggingface", "un-modele").status == "NON PUBLIÉ"
    assert pricing.price_for("bfl", "flux-2-klein").status == "ESTIMÉ"
    assert pricing.cost_usd("mistral", "voxtral-mini-transcribe-3", Decimal("0.5")) == Decimal("0.001750")


@pytest.mark.parametrize(
    ("status", "transient"), [(400, False), (404, False), (408, True), (429, True), (500, True), (503, True)]
)
def test_classement_des_codes_http(status, transient):
    assert ProviderError.from_status(status).transient is transient
