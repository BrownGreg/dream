"""Bouchon de l'API cible pour le plan de charge (ENF-12) — bibliothèque standard uniquement.

Reproduit le contrat REST des specs §4 (`POST /v1/dreams` → 202, `GET /v1/dreams/{id}`) et le
traitement asynchrone : chaque étape dort la durée de son budget SLO (ADR-006), multipliée
par STUB_SCALE. L'étape image passe par un sémaphore de 24 places, la limite de concurrence
documentée par BFL : c'est le goulot attendu, pas le CPU.

Les durées sont SIMULÉES : ce bouchon valide la méthode de test, pas la performance réelle.
Usage : python tests/load/stub_api.py  (port 8765, STUB_SCALE=0.1 par défaut)
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCALE = float(os.environ.get("STUB_SCALE", "0.1"))
WORKERS = int(os.environ.get("STUB_WORKERS", "8"))
STEPS_S = {"stt": 8.0, "llm": 4.0, "image": 15.0}  # budgets p95 d'ADR-006
IMAGE_SLOTS = threading.BoundedSemaphore(24)
QUEUE_LIMIT = 200
QUOTA_PER_USER = 5

dreams: dict[str, dict[str, object]] = {}
per_user: dict[str, int] = {}
lock = threading.Lock()
pool = ThreadPoolExecutor(max_workers=WORKERS)
pending = 0


def _process(dream_id: str) -> None:
    global pending
    for step, seconds in STEPS_S.items():
        if step == "image":
            with IMAGE_SLOTS:
                time.sleep(seconds * SCALE)
        else:
            time.sleep(seconds * SCALE)
    with lock:
        dreams[dream_id]["status"] = "done"
        pending -= 1


class Handler(BaseHTTPRequestHandler):
    """Implémente les deux routes utilisées par le scénario de charge."""

    def _json(self, code: int, body: dict[str, object]) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        global pending
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        user = self.headers.get("X-User", "anonyme")
        with lock:
            if per_user.get(user, 0) >= QUOTA_PER_USER:
                return self._json(429, {"error": {"code": "quota_exceeded"}})
            if pending >= QUEUE_LIMIT:
                return self._json(503, {"error": {"code": "busy", "retry_after": 2}})
            per_user[user] = per_user.get(user, 0) + 1
            dream_id = str(uuid.uuid4())
            dreams[dream_id] = {"id": dream_id, "status": "received"}
            pending += 1
        pool.submit(_process, dream_id)
        return self._json(202, {"dream_id": dream_id, "status_url": f"/v1/dreams/{dream_id}"})

    def do_GET(self) -> None:
        dream_id = self.path.rsplit("/", 1)[-1]
        with lock:
            dream = dreams.get(dream_id)
        if dream is None:
            return self._json(404, {"error": {"code": "not_found"}})
        return self._json(200, dream)

    def log_message(self, format: str, *args: object) -> None:
        """Silence : les métriques viennent de Locust."""


if __name__ == "__main__":
    port = int(os.environ.get("STUB_PORT", "8765"))
    print(f"Bouchon API sur :{port} — échelle {SCALE}, {WORKERS} workers, 24 places image")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
