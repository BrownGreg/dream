# Fiche 1 — Bug critique : enregistrement micro refusé sous Chrome et Firefox

| | |
|---|---|
| Ticket | DREAM-19 (corrige DREAM-6) · incident n° 9 de [`docs/incidents.md`](../incidents.md) |
| PR | [#25](https://github.com/BrownGreg/dream/pull/25) |
| Fichiers | `dreams/audio.py`, `tests/unit/test_audio.py`, `tests/fixtures/reve_mediarecorder.webm` |
| Gravité | critique : le geste principal de l'application (US-01) échouait sur les deux navigateurs les plus répandus |

## Symptôme

Premier parcours E2E (Playwright, Chromium avec micro simulé) : après « Envoyer », la page affiche « Impossible de mesurer la durée de l'enregistrement ». L'import d'un fichier `.wav` ou `.mp3` fonctionne. Les tests unitaires et d'intégration étaient verts.

## Méthode de debug

1. **Reproduire** : le parcours E2E échoue après « Envoyer ».
2. **Lire le message réel** renvoyé par le serveur : il vient de `probe_duration`, appelé pendant la validation du formulaire.
3. **Isoler l'entrée** : `ffprobe` sur un webm écrit en flux → la clé `format.duration` est absente.
4. **Hypothèse** : MediaRecorder écrit le webm **en flux**, segment par segment, et ne revient jamais au début du fichier pour inscrire la durée. Les fixtures de test, produites par `ffmpeg` dans un fichier, ont toujours cette durée : aucun test ne pouvait voir le problème.
5. **Test rouge** : nouvelle fixture `reve_mediarecorder.webm` écrite en flux (`ffmpeg … -f webm -` vers un tube), puis `test_webm_de_mediarecorder_sans_duree_dans_les_metadonnees` → rouge.
6. **Correctif**, puis **test vert**, et parcours E2E vert.

## Diff commenté

Avant : la durée déclarée est lue, sans alternative si elle manque.

```python
try:
    duration = Decimal(str(json.loads(out)["format"]["duration"])).quantize(Decimal("0.01"))
except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
    raise AudioError("audio_invalid", "Impossible de mesurer la durée de l'enregistrement.") from exc
```

Après : la durée déclarée reste le chemin rapide ; si elle manque, le fichier est décodé en entier.

```python
declared = json.loads(out).get("format", {}).get("duration")
if declared in (None, "N/A"):          # webm de MediaRecorder : pas de durée totale
    return _decoded_duration(data)     # ffmpeg -f null : décode sans rien écrire
return Decimal(str(declared)).quantize(Decimal("0.01"))
```

`_decoded_duration` lance `ffmpeg -i fichier -vn -f null -` et lit le **dernier** `time=hh:mm:ss.cc` de la sortie d'erreur, c'est-à-dire la position atteinte à la fin du décodage. Ce sont les garde-fous de l'appel ffmpeg existant : binaire résolu par `shutil.which` sans shell, délai `FFMPEG_TIMEOUT_S`, code `audio_tool_missing` si ffmpeg manque.

## Alternatives écartées

| Alternative | Pourquoi non |
|---|---|
| Se fier à la durée envoyée par le navigateur | le serveur ne doit pas croire le client : la durée sert au quota et à la limite de 3 min |
| Réécrire le webm avec ses métadonnées (`ffmpeg -c copy`) puis relire | deux passes et un fichier de plus pour obtenir la même information |
| Imposer un autre format d'enregistrement côté navigateur | dépend du navigateur ; le serveur doit de toute façon accepter ce qu'on lui envoie |

## Impact

- **Performance** : le chemin rapide reste inchangé pour les fichiers qui portent leur durée. Pour un webm sans durée, mesuré sur le poste de développement : 84 ms pour 3 s d'audio, **745 ms pour 180 s**, la durée maximale autorisée. Cette mesure a lieu **dans la requête d'envoi** (validation du formulaire), alors que l'objectif est un accusé de réception en moins de 1 s au p95 : le pire cas en consomme les trois quarts. Les tests de charge ont utilisé des fixtures à durée déclarée et ne couvrent pas ce cas. Piste : déplacer la mesure dans le worker et ne garder dans la requête qu'un contrôle de taille.
- **Lisibilité** : une fonction de 20 lignes, docstring qui explique *pourquoi* (MediaRecorder écrit en flux).
- **Testabilité** : la fixture reproduit le format réel, et non une hypothèse ; trois tests couvrent ffmpeg absent, délai dépassé et fichier illisible.

## Ce que le bug enseigne (factuel)

Les tests unitaires utilisaient des fichiers propres. Seul un test avec un vrai navigateur et un vrai encodeur a révélé l'écart. La fixture a été ajoutée au corpus de tests.
