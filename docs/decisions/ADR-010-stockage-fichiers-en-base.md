# ADR-010 — Stockage des images et de l'audio dans PostgreSQL

- **Statut** : accepté · 2026-11-09
- **Type** : Évolution (tranche le point ouvert « stockage des images » d'ADR-008 ; révise le stockage objet S3 du bloc 1)
- **Liens** : ADR-008, `dreams/storage.py`, `dreams/views.py::serve_file`, `docs/preprod/specs/01_c4.md`

## Contexte
Le bloc 1 prévoyait un stockage objet S3-compatible hébergé dans l'UE. En production :
- le disque du service web gratuit Render est effacé à chaque mise en veille (15 min sans trafic) : une image écrite sur disque disparaîtrait ;
- les URL d'image renvoyées par BFL expirent au bout de 10 minutes : il faut copier l'image chez nous tout de suite ;
- chaque fournisseur de plus est un sous-traitant RGPD de plus (DPA, AIPD à mettre à jour) ;
- volume attendu : une image JPEG 1024 x 1024 par rêve, de l'ordre de quelques centaines de Ko (à mesurer sur les premières images réelles), et un audio de quelques centaines de Ko supprimé après transcription.

## Options
| Option | Persistance sur Render gratuit | Nouveau sous-traitant | Coût | Complexité |
|---|---|---|---|---|
| Disque local | non | non | 0 | nulle |
| Stockage objet UE (Scaleway, Cloudflare R2 juridiction UE) via `django-storages` | oui | **oui** (DPA, AIPD) | offre gratuite ou quelques centimes | clés, bucket, CORS |
| **Base PostgreSQL** (Neon UE) | oui | non (déjà sous-traitant) | inclus dans l'offre gratuite tant que le volume reste sous son quota | un backend `Storage` d'une centaine de lignes |

## Décision
Les fichiers sont stockés dans la table `StoredFile` par un backend Django `DatabaseStorage` (`STORAGE_BACKEND=database`, valeur par défaut). En développement et sous Docker Compose, `STORAGE_BACKEND=filesystem` reste possible. Dans les deux cas, **aucun fichier n'est servi directement** : l'URL pointe vers `serve_file`, qui exige une session et vérifie que le rêve appartient à l'utilisateur (404 sinon), en cache privé, avec `nosniff` et une CSP bloquante pour les SVG.

## Conséquences
- Une sauvegarde de la base contient tout ; supprimer un rêve et ses fichiers se fait dans une seule base (US-12, US-17).
- Chaque image servie passe par Django et la base : acceptable au volume de la bêta, à mesurer par le test de charge (TTFB de `serve_file`). Au-delà, la bascule vers un stockage objet ne demande que de changer `STORAGES["default"]`, le code applicatif ne dépendant que de l'API `Storage`.
- Le quota de stockage de l'offre gratuite Neon devient une limite de capacité, suivie sur `/ops` (taille cumulée de `StoredFile`).
