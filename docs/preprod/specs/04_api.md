# 4. API : choix argumenté et contrats internes

## API externes retenues
Le benchmark complet (coûts, latences, RGPD, scoring pondéré) est en annexe `benchmark.xlsx` et en section 4 du dossier de cadrage ; chaque choix est une décision tracée.

| Étape | Fournisseur / modèle | Raison principale | Repli | ADR |
|---|---|---|---|---|
| STT | Mistral Voxtral Mini Transcribe 3 | 1ᵉʳ du scoring STT (4,69/5) : moins cher à égalité, UE, DPA publié | Voxtral Small (WER > 10 %) · faster-whisper | ADR-002 |
| Prompt + émotion | Mistral Small 4, JSON Schema | Un seul appel, ≈ 1,4 % du coût, texte seul (AI Act) | mDeBERTa (émotion seule) | ADR-001, 003 |
| Image | BFL FLUX.2 [klein], `api.eu.bfl.ai` | 1ᵉʳ du scoring image (3,45/5), seul acteur UE | FLUX.2 [pro] · Nano Banana 2.1 | ADR-004 |
| Ambiance | Bibliothèque CC0 interne | Coût nul, aucun transfert | — | ADR-005 |
| Voix (R2) | Mistral Voxtral TTS | Même contrat, voix FR | Azure Neural TTS (UE) | ADR-005 |

Tous les fournisseurs sont derrière des **ports** (`Transcriber`, `DreamAnalyzer`, `ImageGenerator`, `SpeechSynthesizer`) : remplacer un modèle déprécié revient à écrire un adapter, sans toucher au métier ni à l'UI.

## Contrats de l'API interne (REST, préfixe `/v1`, JSON UTF-8)
| Méthode et chemin | Rôle | Réponse nominale | Story |
|---|---|---|---|
| `POST /auth/magic-link` | `{email}` → envoi du lien | `204` | — |
| `PUT /me/consents` | `{transcription, image_generation, emotion_tracking, text_version}` | `200` + état courant | US-03 |
| `POST /dreams` | multipart `audio` + `image_disabled` | `202 {dream_id, status_url}` | US-01, 02, 11 |
| `GET /dreams/{id}` | état et contenu d'un rêve | `200 Dream` (URL de médias signées 15 min) | US-04, 06, 07, 08 |
| `PATCH /dreams/{id}` | `{transcription?, emotion?}` ; une transcription modifiée relance l'analyse | `200 Dream` | US-05, 14 |
| `POST /dreams/{id}/retry` | relance l'étape en échec | `202` | US-08 |
| `GET /dreams?emotion=&from=&to=&cursor=` | historique paginé, du plus récent au plus ancien | `200 {items[], next_cursor}` | US-09, 10 |
| `GET /me/stats/emotions?months=6` | répartition mensuelle | `200` | US-16 |
| `DELETE /dreams/{id}` | suppression en cascade | `204` | US-12 |
| `GET /me/export` | export complet | `200 DreamExport` (`dream.schema.json`) | US-15 |
| `DELETE /me` | suppression du compte | `202` (effacement < 24 h) | US-17 |

Exemple — `GET /v1/dreams/{id}` :
```json
{"id": "3f1c…", "status": "done", "title": "Le train sous la mer",
 "transcription": {"text": "J'étais dans un train…", "edited_by_user": false},
 "emotion": {"emotion": "étrange", "confidence": 0.82, "source": "model"},
 "image_disabled": false,
 "assets": [{"kind": "image", "url": "https://cdn…/sig…", "ai_generated": true}]}
```

## Codes d'erreur
Format unique : `{"error": {"code": "…", "message": "texte affichable en français", "action": "retry|record_again|consent|wait"}}`.

| HTTP | `code` | Cas | Action proposée |
|---|---|---|---|
| 400 | `validation_error` | JSON non conforme au schéma | corriger la saisie |
| 401 | `unauthenticated` | session absente ou expirée | se reconnecter |
| 403 | `consent_required` | finalité non consentie | ouvrir les réglages de consentement |
| 404 | `not_found` | rêve inexistant **ou appartenant à un autre compte** (pas de 403, pour ne rien révéler) | — |
| 413 | `audio_too_large` | > 20 Mo | réenregistrer plus court |
| 415 | `audio_unsupported` | ni WAV ni MP3 (signature d'octets) | convertir ou réenregistrer |
| 422 | `audio_invalid` | durée < 3 s ou > 300 s, fichier illisible | réenregistrer |
| 429 | `quota_exceeded` | 5 rêves/jour atteints (`reset_at` fourni) | attendre |
| 503 | `busy` | file saturée (`retry_after`) | réessayer |
| — | `stt_unavailable`, `llm_invalid_output`, `image_rejected_safety`, `image_budget_exhausted` | statut d'échec d'étape dans `dreams.error_code` | relancer ou continuer sans image |
