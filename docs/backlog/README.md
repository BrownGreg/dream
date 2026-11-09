# Backlog de production

`jira_production.csv` : 24 tickets à importer dans le projet Jira **DREAM** (Paramètres système → Import externe → CSV). Importés dans cet ordre dans un projet vide, ils reçoivent les clés DREAM-1 à DREAM-24, celles utilisées par les branches et les PR. La description de chaque ticket rappelle la clé attendue et les stories `US-xx` du bloc 1 ([`../preprod/backlog/stories.toml`](../preprod/backlog/stories.toml)).

Correspondance des colonnes à l'import : `Summary` → Résumé, `Issue Type` → Type, `Description`, `Priority`, `Story Points`, chaque `Labels` → Étiquettes. Sprint : un sprint d'une semaine « Production » couvrant les jours 1 à 6 (étiquettes `jour-n`).
