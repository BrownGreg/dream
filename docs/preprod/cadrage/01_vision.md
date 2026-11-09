# 1. Vision produit

## Elevator pitch

> **Pour** les personnes qui se souviennent de leurs rêves au réveil et veulent les garder,
> **qui** n'ont ni le temps ni l'énergie d'écrire un journal de rêves à 7 h du matin,
> **le Synthétiseur de rêves est** une application web de journal onirique vocal
> **qui** transforme un récit dicté en 60 secondes en une image, une ambiance sonore et une humeur, rangés dans un historique personnel ;
> **contrairement aux** journaux de rêves textuels (carnet papier, applications de notes) qui demandent d'écrire et ne restituent rien,
> **notre produit** ne demande qu'un récit dicté, le restitue en image et en ambiance, et efface tout en un clic : ni interprétation psychologique, ni partage.

## Périmètre

| Dans le produit | Hors produit (décidé) |
|---|---|
| Récit vocal ou fichier audio → transcription → image + ambiance → émotion → historique | Interprétation « psychologique » des rêves (US-22, *Won't* — prétention diagnostique) |
| Émotion inférée du **texte** transcrit | Analyse de la voix (prosodie) — cf. ADR-001 et section 5 |
| Suivi personnel de l'humeur dans le temps | Partage public (US-21, *Won't* — Kano inverse) |

## Critères de succès (SMART)

Ces critères sont **la** définition du succès ; les SLO techniques (ADR-006) et le budget (ADR-007) en découlent.

| ID | Critère | Cible | Mesure | Échéance |
|---|---|---|---|---|
| CS-01 | Réutilisation | ≥ 40 % des bêta-testeurs ayant raconté un rêve en racontent un 2ᵉ sous 7 jours | Événements `dream.created` par utilisateur, bêta privée de 30 personnes | Fin R2 |
| CS-02 | Latence perçue | p95 « fin d'envoi → image affichée » ≤ 30 s | Traces par étape (`api_calls`), 100 rêves consécutifs en préproduction | Fin MVP |
| CS-03 | Coût unitaire | ≤ 0,05 $ d'appels API par rêve, tous fournisseurs confondus | Somme `api_calls.cost_usd` / nombre de rêves, sur 30 jours | Fin MVP |
| CS-04 | Conformité | 0 donnée de rêve envoyée à un fournisseur sans DPA signé ni opt-out d'entraînement actif | Registre des sous-traitants vérifié à chaque release (checklist DoD) | Chaque release |
| CS-05 | Fiabilité | ≥ 98 % des rêves soumis aboutissent (avec ou sans image) | `dreams.status = done` / rêves soumis, 30 jours glissants | Fin R2 |
| CS-06 | Fidélité perçue | Note moyenne ≥ 4/5 à « l'image ressemble à mon rêve » | Notation facultative après affichage, ≥ 50 rêves notés | Fin R2 |

Les cibles sont des **hypothèses de pilotage** posées en pré-production ; CS-02 et CS-03 sont confrontées au benchmark (section 4), les autres seront mesurées en bêta.
