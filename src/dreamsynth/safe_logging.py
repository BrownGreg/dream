"""Journalisation sans contenu de rêve (ENF-10, section 5.6).

Un filtre `logging` masque tout champ sensible passé en `extra=` et refuse les messages qui
contiennent une transcription connue. Les journaux ne portent que des identifiants
pseudonymes, des étapes, des durées et des codes d'erreur.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

SENSITIVE_FIELDS = frozenset({"text", "transcription", "prompt", "visual_prompt", "title", "email"})
REDACTED = "[masqué]"


def pseudonymize(user_id: str, secret: bytes) -> str:
    """Identifiant pseudonyme stable (HMAC-SHA256), jamais réversible sans la clé."""
    return hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()


class RedactDreamContent(logging.Filter):
    """Masque les attributs sensibles d'un enregistrement de journal."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Remplace la valeur des champs sensibles ; l'enregistrement est conservé."""
        for name in SENSITIVE_FIELDS:
            if hasattr(record, name):
                setattr(record, name, REDACTED)
        return True


def get_logger(name: str = "dreamsynth") -> logging.Logger:
    """Logger applicatif muni du filtre de masquage."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, RedactDreamContent) for f in logger.filters):
        logger.addFilter(RedactDreamContent())
    return logger
