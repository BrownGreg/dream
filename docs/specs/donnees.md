# Modèle de données de production — écarts avec l'ERD du bloc 1

Référence : [`../preprod/specs/02_donnees.md`](../preprod/specs/02_donnees.md). Code : [`dreams/models.py`](../../dreams/models.py), [`accounts/models.py`](../../accounts/models.py).

| Bloc 1 | Production | Raison |
|---|---|---|
| `users.pseudonym` stocké | Calculé à la volée (HMAC-SHA256 de l'id avec une clé secrète) et écrit dans `ApiCall.user_pseudonym` | Rien à maintenir en base ; même garantie dans les journaux |
| `users.last_seen_at`, `deletion_requested_at` | `last_login` (Django) ; suppression immédiate et synchrone du compte | La suppression est faite dans la requête (US-17), sans délai de 24 h à suivre |
| `consents.scope` : `transcription`, `image_generation`, `emotion_tracking` | `processing` (transcription + analyse), `image_generation` | L'émotion est calculée sur le texte déjà consenti ; deux cases claires à l'inscription au lieu de trois |
| `dreams.status` : `received → transcribed → analyzed → done / failed` | `received → transcribing → analyzing → generating → done / partial / failed` | Étape en cours visible pendant le polling ; `partial` garde ce qui a réussi si l'image échoue |
| Table `audio_assets` | Champs `audio*` sur `Dream` | Un seul audio par rêve, supprimé après transcription : une table de plus n'apporte rien |
| Tables `generations` + `generation_assets` | `GeneratedAsset` | Un fichier au plus par génération |
| `generations.kind` : `image`, `ambiance`, `speech`, `video` | `image`, `ambiance` | `speech` (US-23) et `video` (US-20) sont des « Could » hors du périmètre de production |
| `generation_assets.c2pa_manifest` | non implémenté | Release 2 du bloc 1 ; la mention « générée par IA » est affichée sur chaque image |
| Valeurs d'émotion `étrange`, `mélancolique` | `etrange`, `melancolique` (libellés accentués conservés) | Valeurs stables dans les URL des filtres |
| Table `audit_log` | non implémentée à ce stade | À trancher avec l'export et la suppression RGPD (DREAM-14) |
| `api_calls.retries` | `ApiCall.attempt` (une ligne par tentative) | Chaque retry est facturable et doit apparaître dans le coût |

Maintenu : identifiants UUID des rêves, `ApiCall` en entier séquentiel, `ON DELETE CASCADE` sauf `ApiCall.dream` (`SET NULL`, le coût survit au rêve), une seule émotion courante par rêve (contrainte partielle), confiance entre 0 et 1, chiffrement applicatif de `transcription.text`, du titre et du prompt visuel (Fernet, clés hors base, rotation possible).
