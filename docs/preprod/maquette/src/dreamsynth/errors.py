"""Erreurs métier et messages affichables (libellés repris des critères d'acceptation)."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Codes d'erreur partagés par le pipeline, l'API cible et l'UI (specs §4)."""

    AUDIO_TOO_SHORT = "audio_too_short"
    AUDIO_TOO_LONG = "audio_too_long"
    AUDIO_TOO_LARGE = "audio_too_large"
    AUDIO_UNSUPPORTED = "audio_unsupported"
    AUDIO_INVALID = "audio_invalid"
    CONSENT_REQUIRED = "consent_required"
    STT_UNAVAILABLE = "stt_unavailable"
    TIMEOUT = "timeout"
    LLM_INVALID_OUTPUT = "llm_invalid_output"
    IMAGE_REJECTED_SAFETY = "image_rejected_safety"
    IMAGE_UNAVAILABLE = "image_unavailable"


MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.AUDIO_TOO_SHORT: "Enregistrement trop court (minimum 3 s)",
    ErrorCode.AUDIO_TOO_LONG: "Enregistrement trop long (maximum 5 min)",
    ErrorCode.AUDIO_TOO_LARGE: "Fichier trop volumineux (maximum 20 Mo)",
    ErrorCode.AUDIO_UNSUPPORTED: "Format non pris en charge : utilisez .wav ou .mp3",
    ErrorCode.AUDIO_INVALID: "Fichier audio illisible : réenregistrez votre récit",
    ErrorCode.CONSENT_REQUIRED: "Consentement requis avant tout traitement",
    ErrorCode.STT_UNAVAILABLE: "Transcription indisponible, réessayez dans un instant",
    ErrorCode.TIMEOUT: "Le service met trop de temps à répondre",
    ErrorCode.LLM_INVALID_OUTPUT: "Analyse du rêve impossible, réessayez dans un instant",
    ErrorCode.IMAGE_REJECTED_SAFETY: "Image non générée : le service a refusé ce contenu",
    ErrorCode.IMAGE_UNAVAILABLE: "Image indisponible pour le moment : votre rêve est enregistré",
}

RETRYABLE: frozenset[ErrorCode] = frozenset(
    {ErrorCode.STT_UNAVAILABLE, ErrorCode.TIMEOUT, ErrorCode.LLM_INVALID_OUTPUT}
)


class DreamError(Exception):
    """Erreur portant un code métier et son message utilisateur."""

    def __init__(self, code: ErrorCode, detail: str = "") -> None:
        """Construit l'erreur à partir de son code."""
        super().__init__(f"{code}: {detail}" if detail else str(code))
        self.code = code
        self.detail = detail

    @property
    def user_message(self) -> str:
        """Message affichable, en français, sans détail technique."""
        return MESSAGES[self.code]

    @property
    def retryable(self) -> bool:
        """Vrai si relancer le traitement a une chance d'aboutir."""
        return self.code in RETRYABLE


class ServiceUnavailableError(DreamError):
    """Le fournisseur ne répond pas ou répond en erreur."""


class ServiceTimeoutError(DreamError):
    """Le fournisseur a dépassé le délai imparti."""


class ContentRejectedError(DreamError):
    """Le filtre de sécurité du fournisseur a refusé la demande."""
