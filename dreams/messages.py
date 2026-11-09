"""Messages affichés à l'utilisateur pour chaque code d'erreur (jamais le message du fournisseur)."""

MESSAGES: dict[str, str] = {
    "audio_empty": "L'enregistrement est vide. Réessayez en parlant près du micro.",
    "audio_invalid": "L'enregistrement est illisible. Réessayez, ou importez un fichier .wav, .mp3, .m4a ou .webm.",
    "audio_too_long": "L'enregistrement dépasse la durée maximale.",
    "audio_too_short": "L'enregistrement est trop court pour être transcrit.",
    "audio_too_large": "Le fichier dépasse la taille maximale.",
    "audio_tool_missing": "Le traitement audio est momentanément indisponible. Réessayez plus tard.",
    "audio_missing": "L'enregistrement n'est plus disponible. Racontez à nouveau votre rêve.",
    "transcription_empty": "Aucune parole n'a été reconnue. Réessayez dans un endroit plus calme.",
    "provider_error": "Le service de transcription ne répond pas. Votre enregistrement est conservé : réessayez dans quelques minutes.",
    "provider_timeout": "Le service de transcription met trop de temps à répondre. Réessayez dans quelques minutes.",
    "budget_exceeded": "Le service a atteint sa limite de dépenses. Réessayez plus tard.",
    "quota_exceeded": "Vous avez atteint la limite de rêves pour aujourd'hui. Elle sera remise à zéro à minuit.",
    "image_disabled": "Vous avez choisi de ne pas générer d'image.",
    "image_no_consent": "Aucune image n'est générée sans votre accord (modifiable dans votre compte).",
    "image_rejected": "Le générateur d'image a refusé ce rêve, même reformulé. Le reste de l'analyse est disponible.",
    "image_failed": "L'image n'a pas pu être créée. Le reste de l'analyse est disponible ; vous pourrez la régénérer.",
    "image_budget": "Les images sont suspendues : le budget du service est atteint. Le reste de l'analyse est disponible.",
    "image_attempts": "Le nombre maximal d'images pour ce rêve est atteint.",
    "internal_error": "Une erreur inattendue est survenue. Nous avons été prévenus ; réessayez plus tard.",
}


def message_for(code: str) -> str:
    """Retourne le message lisible d'un code d'erreur.

    Args:
        code: Code stocké dans ``Dream.error_code`` ou ``GeneratedAsset.rejection_reason``.

    Returns:
        Un message en français ; le message générique si le code est inconnu.
    """
    return MESSAGES.get(code, MESSAGES["internal_error"])
