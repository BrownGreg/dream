"""Vues techniques transverses."""

from django.conf import settings
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
        ``200`` avec ``ok`` (ou ``degraded`` si le worker est en retard), ``503`` si la base ne répond pas.
        Le champ ``release`` donne le commit déployé : la CI attend qu'il soit celui qu'elle vient de tester.
    """
    checks: dict[str, str] = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 - toute panne de base doit donner 503, pas une page d'erreur
        checks["database"] = "error"
    if checks["database"] == "ok":
        # Un worker en retard dégrade le service sans le rendre indisponible : 200, statut « degraded ».
        from dashboard.ops import queue_state

        queue = queue_state()
        checks["worker"] = "ok" if queue.worker_ok else "stale"
    if checks["database"] != "ok":
        return JsonResponse({"status": "error", "checks": checks, "release": settings.RELEASE}, status=503)
    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return JsonResponse({"status": status, "checks": checks, "release": settings.RELEASE}, status=200)
