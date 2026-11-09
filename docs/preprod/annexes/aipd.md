# Annexe — AIPD synthétique (version pré-production)

Structure alignée sur la méthode PIA de la CNIL (contexte, principes fondamentaux, risques, plan d'action). À reprendre dans l'outil PIA de la CNIL avant l'ouverture de la bêta ; validation par un DPO requise. Rédigée le 2026-11-06.

## 1. Contexte
| Élément | Contenu |
|---|---|
| Traitement | Journal de rêves vocal : transcription, génération d'image et d'ambiance, classement émotionnel, historique personnel |
| Responsable | Éditeur du Synthétiseur de rêves (projet étudiant, pas d'exploitation commerciale à ce stade) |
| Personnes concernées | Utilisateurs majeurs inscrits (bêta : 30 personnes) |
| Données | E-mail ; audio (transitoire) ; transcription ; émotion ; prompt visuel ; image ; consentements ; journaux techniques pseudonymisés |
| Sous-traitants | Mistral AI (UE), Black Forest Labs (UE), hébergeur UE (à choisir) — section 5.3 |
| Cycle de vie | Capture → transcription → suppression de l'audio → analyse → image → stockage → consultation → effacement (section 5.6) |

## 2. Principes fondamentaux
| Principe | Mise en œuvre |
|---|---|
| Finalité déterminée | Restituer et archiver ses propres rêves ; aucune finalité publicitaire, aucun profilage tiers |
| Base légale | Consentement explicite et granulaire (art. 9.2.a) |
| Minimisation | E-mail seul à l'inscription ; audio supprimé ; fournisseur d'image limité au prompt reformulé ; pseudonyme vers les API |
| Exactitude | Transcription et émotion corrigeables par la personne (US-05, US-14) |
| Conservation | Durées chiffrées (section 5.6) |
| Information | Écran de consentement listant chaque sous-traitant, son pays et la donnée transmise |
| Droits | Accès et portabilité (export JSON, US-15), effacement en cascade (US-12, US-17), retrait du consentement sans perte du journal |
| Transferts | Aucun hors UE dans la configuration retenue ; le repli Google l'implique (garanties art. 46 à documenter) |

## 3. Risques
Échelle CNIL : gravité et vraisemblance de 1 (négligeable) à 4 (maximale).

| Événement redouté | Sources de risque | Gravité | Vraisemblance avant / après mesures |
|---|---|---|---|
| Accès illégitime aux rêves | Attaquant externe, employé, sous-traitant | 4 | 3 → 1 |
| Modification non désirée (émotion, image erronées présentées comme vraies) | Erreur de modèle | 2 | 3 → 2 (correction possible, source stockée) |
| Disparition des rêves | Panne, suppression accidentelle | 2 | 2 → 1 (sauvegardes chiffrées quotidiennes) |
| Réutilisation pour entraîner des modèles | Sous-traitant | 3 | 3 → 1 (opt-out prouvé, condition bloquante) |
| Atteinte psychologique (image choquante, lecture médicale) | Conception du produit | 3 | 2 → 1 (US-11, US-22, mentions) |

## 4. Plan d'action (bloquant pour la bêta)
| # | Action | Échéance | Story / ADR |
|---|---|---|---|
| 1 | Activer l'opt-out d'entraînement Mistral (Admin › Privacy) et conserver la capture | Sprint 1 | ADR-002 |
| 2 | Demander la ZDR Mistral (`/v1/audio/transcriptions`, `/v1/chat/completions`, `/v1/audio/speech`) | Sprint 1 | ADR-002 |
| 3 | Obtenir DPA + opt-out écrit de BFL, ou basculer sur le repli | Sprint 2 | ADR-004 |
| 4 | Choisir un hébergeur UE avec DPA, chiffrement au repos | Sprint 2 | Spécifications §1 |
| 5 | Saisir cette AIPD dans l'outil PIA de la CNIL, faire valider | Sprint 3 | — |

## Sources (consultées le 2026-11-06)
- RGPD, art. 9, 28, 35 — texte publié par la CNIL : https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre2 et https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre4
- WP248 rév.01, lignes directrices sur l'AIPD (critères, règle des deux critères) : https://www.cnil.fr/sites/default/files/atoms/files/20171013_wp248_rev01_enpdf_4.pdf
- CNIL, AIPD et outil PIA : https://www.cnil.fr/fr/RGPD-analyse-impact-protection-des-donnees-aipd
- CNIL, Guide RGPD du développeur : https://www.cnil.fr/fr/guide-rgpd-du-developpeur
- CNIL, Les durées de conservation des données : https://www.cnil.fr/fr/passer-laction/les-durees-de-conservation-des-donnees
- CNIL, Intelligence artificielle : https://www.cnil.fr/fr/intelligence-artificielle
- AI Act, art. 3, 50, 113 (version consolidée) : https://artificialintelligenceact.eu/article/3/ · https://artificialintelligenceact.eu/article/50/ · https://artificialintelligenceact.eu/article/113/
- Politiques des fournisseurs : onglet `Sources` de `benchmark.xlsx`
