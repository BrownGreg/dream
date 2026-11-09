# Accessibilité — preuves

Audit automatique **axe-core 4.14.0**, règles wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa, écran mobile 390 x 844, Chromium (Playwright).
Test : [`tests/e2e/test_accessibilite.py`](../../../tests/e2e/test_accessibilite.py), exécuté en CI (job « E2E navigateur »).
Rapport brut : [`axe-2026-11-09.json`](axe-2026-11-09.json). Relancer : `A11Y_REPORT=docs/tests/accessibilite/axe-$(date +%F).json make e2e`.

| Page | Règles conformes | Violations |
|---|---|---|
| `comptes/connexion/` | 22 | 0 |
| `comptes/inscription/` | 25 | 0 |
| `comptes/mot-de-passe/oubli/` | 22 | 0 |
| `/` (historique) | 27 | 0 |
| `statistiques/?periode=365` | 24 | 0 |
| `reves/nouveau/` | 23 | 0 |
| `reves/<id>/` (rêve terminé) | 22 | 0 |
| `reves/<id>/` (rêve en cours, suivi) | 24 | 0 |
| `reves/<id>/supprimer/` | 18 | 0 |
| `comptes/mon-compte/` | 23 | 0 |

Éléments « à vérifier » (contraste non mesurable) : 0. Le test échoue s'il en apparaît.

## Corrigé grâce à l'audit
- En-tête mobile qui débordait à 390 px : bouton « Déconnexion » partiellement recouvert (contraste non mesurable) → marque raccourcie sur mobile, éléments qui passent à la ligne.
- Coche des étapes en caractère de police (contraste non mesurable) → icône SVG.
- Pages « mot de passe oublié » servies avec les gabarits de l'administration Django (titre et mise en page incohérents) → ordre des applications corrigé (incident #7).

## Vérifié à la main (non couvert par axe)
- Navigation au clavier : tous les contrôles sont des éléments natifs (`button`, `a`, `input`, `details`) ; focus visible par un contour de 3 px (`:focus-visible`).
- Bouton micro : libellé visible (« Enregistrer » / « Arrêter »), `aria-pressed`, minuteur `role=timer`, messages d'état `aria-live=polite`.
- `prefers-reduced-motion` : animations CSS et graphiques Chart.js désactivés.
- Graphiques : tableau de données sous chaque graphique ; palette catégorielle validée (contraste ≥ 3:1, daltonisme ΔE ≥ 8).
