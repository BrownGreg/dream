"""Génère ``docs/diagrams/erd.puml`` à partir des modèles Django réels (preuve que l'ERD est à jour).

Usage : ``uv run python scripts/export_erd.py && plantuml -tsvg docs/diagrams/erd.puml``.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

APPS = ("accounts", "dreams")
HIDDEN = {"groups", "user_permissions", "password", "is_superuser"}
SENSITIVE = {"EncryptedTextField": " <<chiffré>>"}


def main() -> None:
    """Écrit le fichier PlantUML."""
    import django

    django.setup()
    from django.apps import apps
    from django.db import models

    lines = [
        "@startuml erd",
        "' Généré par scripts/export_erd.py depuis les modèles Django : ne pas modifier à la main.",
        "title Modèle de données de production (généré depuis le code)",
        "hide circle",
        "skinparam linetype ortho",
    ]
    relations = []
    for app in APPS:
        for model in apps.get_app_config(app).get_models():
            lines.append(f"entity {model.__name__} {{")
            for field in model._meta.get_fields():
                if field.auto_created and not field.concrete:
                    continue
                if field.name in HIDDEN or not getattr(field, "concrete", False):
                    continue
                kind = type(field).__name__.replace("Field", "")
                marker = "* " if getattr(field, "primary_key", False) else ""
                extra = SENSITIVE.get(type(field).__name__, "")
                if isinstance(field, models.ForeignKey | models.OneToOneField):
                    target = field.related_model.__name__
                    cardinality = "||--||" if isinstance(field, models.OneToOneField) else "||--o{"
                    on_delete = field.remote_field.on_delete.__name__
                    relations.append(f"{target} {cardinality} {model.__name__} : {field.name} ({on_delete})")
                    lines.append(f"  {marker}{field.name}_id : FK → {target}")
                else:
                    lines.append(f"  {marker}{field.name} : {kind}{extra}")
            lines.append("}")
    lines += [*relations, "@enduml", ""]
    out = Path(__file__).resolve().parents[1] / "docs" / "diagrams" / "erd.puml"
    out.write_text("\n".join(lines))
    print(out)


if __name__ == "__main__":
    main()
