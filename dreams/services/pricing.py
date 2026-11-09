"""Prix unitaires des fournisseurs, source unique du calcul de coût (ADR-009).

Repris du catalogue sourcé du bloc 1 (``docs/preprod/maquette/benchmark/catalog.toml``,
consulté le 2026-11-02). Statuts : ``SOURCÉ`` (page officielle), ``ESTIMÉ`` (méthode
dans ``note``), ``NON PUBLIÉ`` (coût compté 0, à vérifier sur la facture).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Price:
    """Prix d'un modèle.

    Attributes:
        usd_per_unit: Prix en dollars pour une unité ``unit``.
        unit: Unité facturée (``minute``, ``token``, ``image``, ``request``).
        status: ``SOURCÉ``, ``ESTIMÉ`` ou ``NON PUBLIÉ``.
        source: URL de la page tarifaire.
        consulted: Date de consultation.
        note: Méthode d'estimation éventuelle.
    """

    usd_per_unit: Decimal
    unit: str
    status: str
    source: str
    consulted: str = "2026-11-02"
    note: str = ""


_MISTRAL = "https://docs.mistral.ai/inference/pricing"

PRICES: dict[tuple[str, str], Price] = {
    ("mistral", "voxtral-mini-transcribe-3"): Price(Decimal("0.0035"), "minute", "SOURCÉ", _MISTRAL),
    ("mistral", "voxtral-small-transcribe-3"): Price(Decimal("0.004"), "minute", "SOURCÉ", _MISTRAL),
    # 0,15 $ par million de tokens (entrée et sortie au même tarif dans le catalogue).
    ("mistral", "mistral-small-2603"): Price(Decimal("0.00000015"), "token", "SOURCÉ", _MISTRAL),
    ("bfl", "flux-2-klein"): Price(
        Decimal("0.014"),
        "image",
        "ESTIMÉ",
        "https://docs.bfl.ai/quick_start/pricing",
        note="1er mégapixel ; tarif affiché seulement par le calculateur bfl.ai/pricing (ADR-004).",
    ),
    # L'API renvoie le coût de chaque requête en crédits : le coût journalisé est mesuré.
    ("bfl", "flux-2-klein-4b"): Price(
        Decimal("0.01"),
        "credit",
        "SOURCÉ",
        "https://docs.bfl.ai/api_integration/integration_guidelines",
        consulted="2026-11-09",
        note="« 1 credit equals $0.01 USD » ; nombre de crédits lu dans la réponse (champ cost).",
    ),
    ("huggingface", "*"): Price(
        Decimal(0),
        "request",
        "NON PUBLIÉ",
        "https://huggingface.co/docs/inference-providers/pricing",
        note="Facturé au temps de calcul selon le fournisseur d'inférence ; à relever sur la facture HF.",
    ),
}

FREE = Price(Decimal(0), "request", "SOURCÉ", "", note="Adapter fake ou local : aucun coût.")


def price_for(provider: str, model: str) -> Price:
    """Retourne le prix d'un modèle.

    Args:
        provider: Fournisseur (``mistral``, ``bfl``, ``huggingface``, ``fake``, ``local``).
        model: Identifiant du modèle.

    Returns:
        Le prix connu ; gratuit pour les adapters ``fake`` et ``local``.

    Raises:
        KeyError: Si un modèle payant n'a pas de prix : on refuse d'appeler un modèle
            dont on ne sait pas compter le coût.
    """
    if provider in ("fake", "local"):
        return FREE
    if (provider, model) in PRICES:
        return PRICES[(provider, model)]
    if (provider, "*") in PRICES:
        return PRICES[(provider, "*")]
    raise KeyError(f"aucun prix pour {provider}/{model} : ajoutez-le à dreams/services/pricing.py")


def cost_usd(provider: str, model: str, units: Decimal) -> Decimal:
    """Calcule le coût d'un appel.

    Args:
        provider: Fournisseur.
        model: Modèle.
        units: Quantité facturée, dans l'unité du prix.

    Returns:
        Coût en dollars, arrondi à 6 décimales.
    """
    return (price_for(provider, model).usd_per_unit * units).quantize(Decimal("0.000001"))
