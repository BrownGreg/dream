# Bibliothèques front hébergées localement

Servies par whitenoise depuis notre domaine : aucun appel à un CDN tiers (pas de fuite d'adresse IP vers un tiers).

| Fichier | Source | Licence | SHA-256 |
|---|---|---|---|
| `chart-4.6.1.umd.min.js` | https://cdn.jsdelivr.net/npm/chart.js@4.6.1/dist/chart.umd.min.js (publié le 2026-10-22) | MIT | original `87364cc2…6925d2` ; servi `c17f2ce49fb9c71ef7fb39c03f868804ac5ab34730149976eebe6b7f807bef0c` |

Seule modification : suppression de la dernière ligne `//# sourceMappingURL=chart.umd.min.js.map`. Le fichier `.map` n'est pas
servi, et le stockage `CompressedManifestStaticFilesStorage` de whitenoise refuse une référence vers un fichier absent
(incident #8).
