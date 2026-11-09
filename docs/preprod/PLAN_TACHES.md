# Liste de tâches — pré-production « Synthétiseur de rêves »

Suivi d'avancement de l'agent (cf. `context/PROMPT_MAITRE.md` §4). `[x]` = fait, `[~]` = en cours.

## Mise en place
- [x] Sujet en `docs/source/sujet.pdf`, `CLAUDE.md` + `AGENTS.md` à la racine
- [x] `pyproject.toml`, `.env.example`, pre-commit, CI GitHub Actions

## Phase 1 — Analyse du besoin (C1-1)
- [x] Vision produit + critères SMART
- [x] Interviews éclair simulées (2) + insights
- [x] 3 personae (dont 1 utilisateur vulnérable)
- [x] Journey maps illustrées
- [x] Matrice de Kano
- [x] User Story Map + stories Gherkin + points + MoSCoW

## Phase 2 — Benchmark (C1-2)
- [x] Shortlist + relevé des tarifs/quotas/RGPD sourcés et datés
- [x] Corpus synthétique (5 récits + 5 prompts)
- [x] Scripts `run_latency.py` (mock/live), `cost_model.py`
- [x] `build_xlsx.py` → `benchmark.xlsx` (formules vivantes)
- [x] KPIs + ADR de choix
- [x] 🛑 Jalon 1 — validé le 2026-11-06 (option A : FLUX.2 [klein])
- [~] Mesures : faster-whisper local mesuré (p95 3,81 s, WER 13,2 %) ; live Mistral en attente de clé
- [x] Recalcul LibreOffice de `benchmark.xlsx` (0 erreur de formule)

## Phase 3 — RGPD & éthique IA (C1-3)
- [x] Section 5 (nature des données, base légale, AIPD, sous-traitants, AI Act, éthique, durées)
- [x] Annexe `aipd.md`
## Phase 4 — Architecture & spécifications (C1-3)
- [x] C4 contexte + conteneurs, ERD, séquence (PlantUML → SVG)
- [x] Modèles Pydantic + `dream.schema.json` généré
- [x] Exigences EXF/ENF (`requirements.toml`), traçabilité générée, ADR-006 SLO
- [x] Sections 1–6 des spécifications
- [x] 🛑 Jalon 2 — validé le 2026-11-06
## Phase 5 — Maquette Streamlit
- [x] Cœur métier `src/` (validation audio, ports, adapters mock + Mistral, pipeline, dépôt)
- [x] 3 pages Streamlit, ambiances générées, README, script vidéo
- [ ] Enregistrement de la vidéo (micro réel : à faire par l'auteur)
## Phase 6 — Qualité & tests
- [x] 89 tests (unitaires, intégration respx, 23 scénarios BDD, 8 AppTest), 3 scénarios ignorés et signalés, couverture 98,0 %
- [x] Plan de charge (bouchon + Locust, paliers 1→100)
- [x] Plan qualité rédigé (section 8)
## Phase 7 — Pilotage agile (C2-1)
- [x] Release plan, Sprint #1, 11 risques + matrice, import Jira
## Phase 8 — PDF
- [x] Dossiers générés (15/15 et 10/10 pages)
- [x] 🛑 Jalon 3 — validé le 2026-11-06
## Vérification finale + rapport
- [x] CONFORMITE.md, pdfinfo, qualité, maquette, recalcul xlsx, chiffres sourcés, relecture jury (corrections appliquées)
