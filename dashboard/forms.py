"""Filtres de l'historique : plage de dates et humeurs, combinables, portés par l'URL."""

from __future__ import annotations

from datetime import date
from typing import Any

from django import forms

from dreams.emotions import Emotion


class DreamFilterForm(forms.Form):
    """Formulaire GET : ``?du=2026-11-01&au=2026-11-09&humeur=serein&humeur=heureux``."""

    du = forms.DateField(required=False, label="Du", widget=forms.DateInput(attrs={"type": "date"}))
    au = forms.DateField(required=False, label="Au", widget=forms.DateInput(attrs={"type": "date"}))
    humeur = forms.MultipleChoiceField(
        required=False, label="Humeur", choices=Emotion.choices, widget=forms.CheckboxSelectMultiple
    )

    def clean(self) -> dict[str, Any]:
        """Remet dans l'ordre une plage saisie à l'envers plutôt que de renvoyer une erreur.

        Returns:
            Les données nettoyées.
        """
        data = super().clean() or {}
        start: date | None = data.get("du")
        end: date | None = data.get("au")
        if start and end and start > end:
            data["du"], data["au"] = end, start
        return data

    @property
    def active(self) -> bool:
        """Indique si au moins un filtre valide est appliqué."""
        return self.is_valid() and any(self.cleaned_data.get(name) for name in ("du", "au", "humeur"))
