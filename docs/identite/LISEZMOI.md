# DreamSynth — identité et landing page

## logo/
- `symbole-*` : symbole seul, carré (sombre = lavande #C4B5FD, clair = #5B4BC4, mono blanc, mono nuit). `*-fond` : avec fond.
- `logo-horizontal-*` : symbole + « Synthétiseur de rêves » (texte vectorisé, Inter SemiBold).
- `logo-court-*` : symbole + « DreamSynth », pour l'en-tête mobile.
- `favicon-16`, `favicon-32`, `favicon.ico` (16/32/48) ; `icone-app-512` (coins arrondis), `-maskable` (PWA, zone sûre), `-clair`.
- Zone de protection : un quart de la hauteur du symbole. Tailles minimales : symbole 16 px, logo horizontal 160 px.

## landing/
- `landing.html` : gabarit Django (`{% load static %}`), à placer dans `templates/`. Copier les favicons dans `static/dreamsynth/`.
- Prototype : Tailwind via le CDN Play. En production : `npx tailwindcss -i dreamsynth.input.css -o static/css/dreamsynth.css --minify` avec `tailwind.config.js`, puis remplacer les balises CDN par le lien vers `dreamsynth.css` (commentaire en tête du fichier).
- Les cartes du journal sont des exemples statiques : à remplacer par une boucle `{% for reve in reves %}` si besoin.
- Animations via `motion-safe:` : désactivées automatiquement si « réduire les animations » est actif.
