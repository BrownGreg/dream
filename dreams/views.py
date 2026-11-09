"""Vues des rêves."""

from __future__ import annotations

import mimetypes
import uuid

from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpRequest
from django.views.decorators.http import require_GET

from dreams.models import Dream


@login_required
@require_GET
def serve_file(request: HttpRequest, path: str) -> FileResponse:
    """Sert une image ou un audio, uniquement à l'utilisateur propriétaire du rêve.

    Les chemins ont la forme ``<audio|assets>/<dream_id>/<nom>`` ; tout autre chemin,
    ou un rêve d'un autre utilisateur, donne 404 (sans révéler l'existence du fichier).

    Args:
        request: Requête authentifiée.
        path: Chemin du fichier dans le stockage.

    Returns:
        Le fichier, en cache privé.

    Raises:
        Http404: Chemin invalide, rêve d'un autre utilisateur ou fichier absent.
    """
    parts = path.split("/")
    if len(parts) != 3 or parts[0] not in ("audio", "assets") or ".." in parts:
        raise Http404
    try:
        dream_id = uuid.UUID(parts[1])
    except ValueError as exc:
        raise Http404 from exc
    if not Dream.objects.filter(id=dream_id, user_id=int(request.user.pk or 0)).exists():
        raise Http404
    try:
        handle = default_storage.open(path)
    except FileNotFoundError as exc:
        raise Http404 from exc
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    response = FileResponse(handle, content_type=content_type)
    response["Cache-Control"] = "private, max-age=86400"
    response["X-Content-Type-Options"] = "nosniff"
    if content_type == "image/svg+xml":
        # Une image SVG ne doit jamais exécuter de script, même servie depuis notre domaine.
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response
