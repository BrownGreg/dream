# Bloc 1 — Pré-production (archive de référence)

Livrables du bloc 1, figés au 2026-11-06. Ils servent de base à la production ; tout écart est tracé par un ADR « Évolution » dans [`../decisions/`](../decisions/).

| Dossier | Contenu |
|---|---|
| `livrables/` | `dossier_cadrage.pdf` (15 p.), `specifications_architecture.pdf` (10 p.) et leurs sources Typst |
| `cadrage/`, `specs/` | Sources Markdown des deux dossiers |
| `decisions/` | ADR-001 à ADR-007 tels qu'acceptés en pré-production |
| `diagrams/` | C4, ERD, séquence, parcours, wireframes (PlantUML + SVG) |
| `backlog/` | User stories `US-xx`, exigences `EXF/ENF`, risques `R-xx`, sprint 1 (TOML) |
| `annexes/` | `benchmark.xlsx`, `jira_import.csv`, AIPD, Kano, entretiens, traçabilité |
| `schemas/` | `dream.schema.json` généré depuis les modèles Pydantic |
| `maquette/` | Maquette Streamlit, benchmark de latence, outils et tests du bloc 1 (projet Python autonome) |
| `CONFORMITE.md`, `PLAN_TACHES.md` | Conformité au sujet du bloc 1 et plan de tâches |

Les chemins cités à l'intérieur de ces documents sont ceux d'origine (racine du dépôt au bloc 1) : `app/` = `maquette/app/`, `build/` = `livrables/`, `docs/cadrage/` = `cadrage/`, etc.
