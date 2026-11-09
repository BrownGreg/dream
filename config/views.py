"""Vues techniques transverses."""

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def health(request: HttpRequest) -> JsonResponse:
    """Indique si l'application et sa base de données répondent.

    Utilisée par le contrôle de santé de Render et le test de fumée de la CI.

    Args:
        request: Requête HTTP entrante.

    Returns:
        ``200`` avec ``{"status": "ok"}`` si la base répond, ``503`` sinon.
    """
    checks: dict[str, str] = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 - toute panne de base doit donner 503, pas une page d'erreur
        checks["database"] = "error"
    healthy = all(value == "ok" for value in checks.values())
    return JsonResponse({"status": "ok" if healthy else "error", "checks": checks}, status=200 if healthy else 503)
