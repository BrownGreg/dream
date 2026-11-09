"""Test de charge Locust (DREAM-20) — toujours sur les adapters fake (aucun coût).

Paliers : 5 → 20 → 50 utilisateurs, 90 s chacun. Chaque utilisateur virtuel se connecte
avec un compte préparé (`seed_load_users`), consulte son historique, ses statistiques et ses
rêves, et de temps en temps raconte un rêve puis suit son traitement comme le navigateur
(polling toutes les 2 s). Le temps « envoi → rêve terminé » est remonté comme une requête
Locust nommée « pipeline : bout en bout ».
"""

from __future__ import annotations

import itertools
import os
import re
import time
from pathlib import Path

from locust import HttpUser, LoadTestShape, between, events, task

AUDIO = (Path(__file__).parents[1] / "fixtures" / "reve_court.wav").read_bytes()
PASSWORD = os.environ.get("LOAD_PASSWORD", "charge-Reves-2026")
USERS = itertools.count(1)
DREAM_URL = re.compile(r"/reves/([0-9a-f-]{36})/")
PIPELINE_TIMEOUT_S = float(os.environ.get("LOAD_PIPELINE_TIMEOUT_S", "120"))


class Dreamer(HttpUser):
    """Utilisateur qui consulte surtout, et raconte parfois un rêve."""

    wait_time = between(2, 5)

    def on_start(self) -> None:
        """Se connecte avec un compte préparé."""
        self.email = f"charge-{next(USERS):03d}@example.org"
        self.dreams: list[str] = []
        self.client.get("/comptes/connexion/", name="connexion (GET)")
        self.client.post(
            "/comptes/connexion/",
            {"username": self.email, "password": PASSWORD, "csrfmiddlewaretoken": self._csrf()},
            name="connexion (POST)",
        )

    def _csrf(self) -> str:
        return self.client.cookies.get("csrftoken", "")

    @task(5)
    def history(self) -> None:
        """Historique (page la plus vue)."""
        self.client.get("/", name="historique")

    @task(2)
    def filtered_history(self) -> None:
        """Historique filtré par humeur (HTMX)."""
        self.client.get("/?humeur=serein&humeur=heureux", headers={"HX-Request": "true"}, name="historique filtré")

    @task(2)
    def stats(self) -> None:
        """Statistiques sur 12 mois."""
        self.client.get("/statistiques/?periode=365", name="statistiques")

    @task(2)
    def detail(self) -> None:
        """Page d'un rêve déjà raconté."""
        if self.dreams:
            self.client.get(f"/reves/{self.dreams[-1]}/", name="détail d'un rêve")

    @task(1)
    def tell_a_dream(self) -> None:
        """Envoie un enregistrement puis suit son traitement comme le navigateur."""
        self.client.get("/reves/nouveau/", name="enregistrement (GET)")
        started = time.perf_counter()
        with self.client.post(
            "/reves/nouveau/",
            files={"audio": ("reve.wav", AUDIO, "audio/wav")},
            headers={"X-CSRFToken": self._csrf(), "HX-Request": "true"},
            name="envoi d'un rêve",
            catch_response=True,
        ) as response:
            target = response.headers.get("HX-Redirect", "")
            match = DREAM_URL.search(target)
            if not match:
                response.failure(f"pas de redirection (HTTP {response.status_code})")
                return
        dream_id = match.group(1)
        self.dreams.append(dream_id)
        while time.perf_counter() - started < PIPELINE_TIMEOUT_S:
            time.sleep(2)
            status = self.client.get(f"/reves/{dream_id}/statut/", name="statut (polling)")
            if status.headers.get("HX-Refresh") == "true":
                events.request.fire(
                    request_type="PIPELINE",
                    name="pipeline : bout en bout",
                    response_time=(time.perf_counter() - started) * 1000,
                    response_length=0,
                    exception=None,
                    context={},
                )
                return
        events.request.fire(
            request_type="PIPELINE",
            name="pipeline : bout en bout",
            response_time=(time.perf_counter() - started) * 1000,
            response_length=0,
            exception=TimeoutError(f"rêve non terminé en {PIPELINE_TIMEOUT_S:.0f} s"),
            context={},
        )


class Stages(LoadTestShape):
    """Paliers 5 → 20 → 50 utilisateurs (durée par palier : LOAD_STAGE_S, 90 s par défaut)."""

    stage_s = int(os.environ.get("LOAD_STAGE_S", "90"))
    stages = ((5, 1), (20, 2), (50, 5))

    def tick(self) -> tuple[int, float] | None:
        """Nombre d'utilisateurs et vitesse d'arrivée pour l'instant courant."""
        index = int(self.get_run_time() // self.stage_s)
        if index >= len(self.stages):
            return None
        return self.stages[index]
