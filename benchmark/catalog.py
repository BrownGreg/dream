"""Chargement du catalogue fournisseurs et des hypothèses de coût.

Toutes les valeurs proviennent de `catalog.toml` et `hypotheses.toml` : ce module ne
contient aucun chiffre métier en dur.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CATEGORIES = ["STT", "LLM", "T2I", "TTS", "AMBIANCE", "VIDEO"]


@dataclass(frozen=True)
class Provider:
    """Une ligne du benchmark (un modèle d'un fournisseur)."""

    key: str
    category: str
    vendor: str
    model: str
    price: float
    unit: str
    per_unit_factor: float
    status: str
    url: str
    eu: bool
    price_out: float = math.nan
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def unit_price(self) -> float:
        """Prix converti dans l'unité de calcul de la catégorie (NaN si non publié)."""
        return self.price * self.per_unit_factor


@dataclass(frozen=True)
class Hypotheses:
    """Valeurs numériques des hypothèses, indexées par identifiant (H0…H9)."""

    values: dict[str, float]
    rows: list[dict[str, Any]]
    scenarios: list[dict[str, str]]

    def __getitem__(self, key: str) -> float:
        """Retourne la valeur de l'hypothèse `key`."""
        return self.values[key]


def load_catalog(path: Path = HERE / "catalog.toml") -> tuple[str, list[Provider]]:
    """Charge le catalogue ; retourne (date de consultation, fournisseurs)."""
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    known = {
        "key",
        "category",
        "vendor",
        "model",
        "price",
        "unit",
        "per_unit_factor",
        "status",
        "url",
        "eu",
        "price_out",
    }
    providers = [
        Provider(
            key=p["key"],
            category=p["category"],
            vendor=p["vendor"],
            model=p["model"],
            price=float(p["price"]),
            unit=p["unit"],
            per_unit_factor=float(p["per_unit_factor"]),
            status=p["status"],
            url=p["url"],
            eu=bool(p["eu"]),
            price_out=float(p.get("price_out", math.nan)),
            extra={k: v for k, v in p.items() if k not in known},
        )
        for p in raw["provider"]
    ]
    return str(raw["consulted"]), providers


def load_hypotheses(path: Path = HERE / "hypotheses.toml") -> Hypotheses:
    """Charge les hypothèses et scénarios de coût."""
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return Hypotheses(
        values={h["id"]: float(h["value"]) for h in raw["h"]},
        rows=list(raw["h"]),
        scenarios=list(raw["scenario"]),
    )


def cost_per_dream(p: Provider, h: Hypotheses) -> float:
    """Coût d'appel d'un fournisseur pour un rêve, selon sa catégorie (NaN si inconnu)."""
    match p.category:
        case "STT":
            return p.unit_price * h["H1"]
        case "LLM":
            return (h["H2"] * p.unit_price + h["H3"] * p.price_out) / 1_000_000
        case "T2I":
            return p.unit_price * h["H4"] * (1 + h["H8"])
        case "TTS":
            per_char = p.unit_price / 1_000_000
            return per_char * h["H6"]
        case "AMBIANCE":
            if p.unit == "$/min":
                return p.unit_price * h["H5"] / 60
            return p.unit_price
        case "VIDEO":
            return p.unit_price * h["H7"]
    raise ValueError(f"catégorie inconnue : {p.category}")
