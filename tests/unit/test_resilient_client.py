"""Client résilient (DREAM-5) : retries, journal ApiCall, coupe-circuit."""

from decimal import Decimal

import pytest

from dreams.models import ApiCall
from dreams.services.errors import (
    BudgetExceededError,
    ProviderError,
    ProviderTimeoutError,
    SafetyRejectionError,
)
from dreams.services.http import CallContext, pseudonymize, resilient_call
from tests.factories import DreamFactory

pytestmark = pytest.mark.django_db

STT = CallContext(step="stt", provider="mistral", model="voxtral-mini-transcribe-3")


class Script:
    """Appel simulé : rejoue une suite d'erreurs puis renvoie un résultat."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.fixture(autouse=True)
def no_sleep(mocker):
    return mocker.patch("time.sleep")


def test_succes_premier_essai_journalise_cout_et_latence():
    dream = DreamFactory()
    ctx = CallContext("stt", "mistral", "voxtral-mini-transcribe-3", dream_id=dream.id, user_id=dream.user_id)
    result = resilient_call(ctx, Script("texte"), estimated_units=Decimal("1.5"))
    assert result == "texte"
    call = ApiCall.objects.get()
    assert call.outcome == "ok"
    assert call.http_status == 200
    assert call.attempt == 1
    assert call.unit == "minute"
    assert call.cost_usd == Decimal("0.005250")  # 1,5 min x 0,0035 $
    assert call.dream_id == dream.id
    assert call.user_pseudonym == pseudonymize(dream.user_id)
    assert call.user_pseudonym != str(dream.user_id)


def test_unites_facturees_lues_dans_la_reponse():
    ctx = CallContext("prompt", "mistral", "mistral-small-2603")
    resilient_call(
        ctx, Script({"tokens": 1000}), estimated_units=Decimal(950), billed_units=lambda r: Decimal(r["tokens"])
    )
    call = ApiCall.objects.get()
    assert call.billed_units == Decimal(1000)
    assert call.cost_usd == Decimal("0.000150")


def test_429_puis_succes_deux_lignes_et_respect_du_retry_after(no_sleep):
    fn = Script(ProviderError.from_status(429, retry_after=7), "ok")
    assert resilient_call(STT, fn, estimated_units=Decimal(1)) == "ok"
    assert fn.calls == 2
    assert list(ApiCall.objects.order_by("attempt").values_list("outcome", "http_status", "cost_usd")) == [
        ("error", 429, Decimal(0)),
        ("ok", 200, Decimal("0.003500")),
    ]
    no_sleep.assert_called_once_with(7.0)


def test_500_rejoue_jusqu_a_epuisement_puis_releve_l_erreur(settings):
    settings.AI_MAX_ATTEMPTS = 3
    fn = Script(*(ProviderError.from_status(503) for _ in range(3)))
    with pytest.raises(ProviderError) as exc:
        resilient_call(STT, fn, estimated_units=Decimal(1))
    assert exc.value.status == 503
    assert fn.calls == 3
    assert ApiCall.objects.filter(outcome="error").count() == 3


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_4xx_non_passagere_jamais_rejouee(status):
    fn = Script(ProviderError.from_status(status), "jamais atteint")
    with pytest.raises(ProviderError):
        resilient_call(STT, fn, estimated_units=Decimal(1))
    assert fn.calls == 1
    assert ApiCall.objects.get().http_status == status


def test_delai_depasse_rejoue_et_compte_comme_facture():
    fn = Script(ProviderTimeoutError(), "ok")
    resilient_call(STT, fn, estimated_units=Decimal(2))
    timeout = ApiCall.objects.get(outcome="timeout")
    assert timeout.cost_usd == Decimal("0.007000")
    assert timeout.http_status is None


def test_refus_de_securite_non_rejoue_et_trace():
    ctx = CallContext("image", "bfl", "flux-2-klein")
    fn = Script(SafetyRejectionError())
    with pytest.raises(SafetyRejectionError):
        resilient_call(ctx, fn, estimated_units=Decimal(1))
    assert fn.calls == 1
    assert ApiCall.objects.get().outcome == "rejected"


def test_backoff_exponentiel(no_sleep, settings):
    settings.AI_RETRY_BASE_SECONDS = 1.0
    settings.AI_MAX_ATTEMPTS = 4
    fn = Script(ProviderTimeoutError(), ProviderTimeoutError(), ProviderTimeoutError(), "ok")
    resilient_call(STT, fn, estimated_units=Decimal(0))
    assert [c.args[0] for c in no_sleep.call_args_list] == [1.0, 2.0, 4.0]


def test_coupe_circuit_bloque_sans_appeler_le_fournisseur(settings):
    settings.AI_BUDGET_EUR = 0.01
    ApiCall.objects.create(step="image", provider="bfl", model="flux-2-klein", outcome="ok", cost_usd="0.009")
    fn = Script("jamais appelé")
    with pytest.raises(BudgetExceededError):
        resilient_call(CallContext("image", "bfl", "flux-2-klein"), fn, estimated_units=Decimal(1))
    assert fn.calls == 0
    blocked = ApiCall.objects.get(outcome="blocked")
    assert blocked.cost_usd == 0
    assert blocked.error_type == "BudgetExceededError"


def test_adapter_fake_gratuit_meme_budget_epuise(settings):
    settings.AI_BUDGET_EUR = 0.01
    ApiCall.objects.create(step="image", provider="bfl", model="flux-2-klein", outcome="ok", cost_usd="0.02")
    with pytest.raises(BudgetExceededError):
        resilient_call(CallContext("stt", "fake", "fake-stt"), Script("x"), estimated_units=Decimal(1))


def test_modele_sans_prix_refuse():
    with pytest.raises(KeyError, match="aucun prix"):
        resilient_call(CallContext("image", "bfl", "flux-inconnu"), Script("x"), estimated_units=Decimal(1))


def test_pseudonyme_stable_et_vide_sans_utilisateur():
    assert pseudonymize(None) == ""
    assert pseudonymize(42) == pseudonymize(42) != pseudonymize(43)
    assert len(pseudonymize(42)) == 64
