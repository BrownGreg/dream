"""Plan de charge — rêves simultanés (ENF-12, ENF-11, ENF-03).

Chaque utilisateur virtuel envoie un récit puis interroge l'état du rêve toutes les 2 s
jusqu'à `done` ; la durée « fin d'envoi → done » est publiée comme requête Locust
`dream end-to-end`, ce qui donne directement son p95.

Paliers (DreamSteps) : 1 → 10 → 50 → 100 rêves simultanés, 60 s chacun.
Critères de réussite (cible, durées non mises à l'échelle) :
- p95 `dream end-to-end` ≤ 30 s (ENF-11) ;
- échecs hors 429 ≤ 2 % (ENF-03) ; 429 (quota) et 503 (backpressure) comptés à part ;
- goulot observé = attente des places image (24), pas la saturation CPU de l'API.

Usage :
    python tests/load/stub_api.py &
    locust -f tests/load/locustfile.py --host http://127.0.0.1:8765 --headless \
        --csv benchmark/results/load
"""

from __future__ import annotations

import time
import uuid

from locust import HttpUser, LoadTestShape, between, task

AUDIO = (
    b"RIFF" + b"\0" * 64_000
)  # charge utile représentative (≈ 64 ko), non décodée par le bouchon
POLL_S = 2.0
TIMEOUT_S = 120.0


class Dreamer(HttpUser):
    """Un rêveur : un envoi, puis sondage jusqu'à la fin du traitement."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Identité distincte par utilisateur virtuel (quota de 5 rêves/jour)."""
        self.user_id = str(uuid.uuid4())

    @task
    def tell_a_dream(self) -> None:
        """Envoie un récit et mesure le temps jusqu'à `done`."""
        with self.client.post(
            "/v1/dreams",
            files={"audio": ("micro.wav", AUDIO, "audio/wav")},
            headers={"X-User": self.user_id},
            name="POST /v1/dreams",
            catch_response=True,
        ) as response:
            if response.status_code in (429, 503):
                response.success()  # comportement attendu, compté par son code
                return
            if response.status_code != 202:
                response.failure(f"HTTP {response.status_code}")
                return
            dream_id = response.json()["dream_id"]
        start = time.perf_counter()
        status = "received"
        while status != "done" and time.perf_counter() - start < TIMEOUT_S:
            time.sleep(POLL_S)
            poll = self.client.get(f"/v1/dreams/{dream_id}", name="GET /v1/dreams/{id}")
            status = poll.json().get("status", "?") if poll.ok else "error"
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.environment.events.request.fire(
            request_type="DREAM",
            name="dream end-to-end",
            response_time=elapsed_ms,
            response_length=0,
            exception=None if status == "done" else TimeoutError(status),
            context={},
        )


class DreamSteps(LoadTestShape):
    """Paliers de rêves simultanés : 1 → 10 → 50 → 100, 60 s chacun."""

    stages = ((60, 1), (120, 10), (180, 50), (240, 100))

    def tick(self) -> tuple[int, float] | None:
        """Nombre d'utilisateurs et taux d'arrivée du palier courant."""
        run_time = self.get_run_time()
        for end, users in self.stages:
            if run_time < end:
                return users, max(1.0, users / 10)
        return None
