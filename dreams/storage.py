"""Stockage des fichiers dans PostgreSQL (ADR-010).

Le disque d'un service web gratuit Render est effacé à chaque mise en veille : les
images et l'audio en attente de transcription sont donc gardés en base, à côté des
rêves. Pas de fournisseur de stockage supplémentaire, donc pas de sous-traitant RGPD
de plus ; la suppression d'un rêve supprime ses fichiers dans la même base.
"""

from __future__ import annotations

from typing import Any

from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage, Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    """Backend de stockage Django adossé au modèle :class:`dreams.models.StoredFile`."""

    def _model(self) -> Any:
        from dreams.models import StoredFile

        return StoredFile

    def _open(self, name: str, mode: str = "rb") -> File[bytes]:
        row = self._model().objects.filter(name=name).only("content").first()
        if row is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(row.content), name=name)

    def _save(self, name: str, content: File[Any]) -> str:
        content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()
        self._model().objects.update_or_create(name=name, defaults={"content": data, "size": len(data)})
        return name

    def delete(self, name: str) -> None:
        """Supprime le fichier s'il existe."""
        self._model().objects.filter(name=name).delete()

    def exists(self, name: str) -> bool:
        """Indique si le nom est déjà pris."""
        return bool(self._model().objects.filter(name=name).exists())

    def size(self, name: str) -> int:
        """Taille en octets."""
        row = self._model().objects.filter(name=name).only("size").first()
        if row is None:
            raise FileNotFoundError(name)
        return int(row.size)

    def url(self, name: str | None) -> str:
        """URL de la vue protégée qui sert le fichier à son seul propriétaire."""
        return reverse("dreams:file", args=[name])


@deconstructible
class ProtectedFileSystemStorage(FileSystemStorage):
    """Stockage disque (développement, Docker Compose) servi par la même vue protégée."""

    def url(self, name: str | None) -> str:
        """URL de la vue protégée, jamais un accès direct à ``MEDIA_ROOT``."""
        return reverse("dreams:file", args=[name])
