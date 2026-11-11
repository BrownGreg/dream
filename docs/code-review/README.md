# Dossier de code review

Préparation de la code review live de 15 minutes. Trois tickets réellement résolus pendant le projet, chacun avec sa PR, le diff commenté, la méthode de debug, les alternatives écartées et l'impact.

| Fiche | Type | Ticket | PR | En une phrase |
|---|---|---|---|---|
| [1. Enregistrement micro refusé](01-bug-mediarecorder.md) | bug critique | DREAM-19 (corrige DREAM-6) | [#25](https://github.com/BrownGreg/dream/pull/25) | MediaRecorder écrit le webm en flux, sans durée totale : décodage complet si la durée manque |
| [2. File de tâches invisible](02-bug-file-de-taches.md) | bug | DREAM-20 (corrige DREAM-17) | [#28](https://github.com/BrownGreg/dream/pull/28) | `run_after` vaut la date maximale pour une tâche sans délai ; la fixture partageait l'hypothèse fausse |
| [3. Client résilient et coupe-circuit](03-story-client-resilient.md) | story | DREAM-5 | [#10](https://github.com/BrownGreg/dream/pull/10) | un point de passage unique pour délais, retries, journal des coûts et budget |

Et [10 questions probables du jury](questions.md), avec des réponses courtes et le fichier à ouvrir pour chaque preuve.

Autres incidents documentés : [`docs/incidents.md`](../incidents.md) (11 entrées).
