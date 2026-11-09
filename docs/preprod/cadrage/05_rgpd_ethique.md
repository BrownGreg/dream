# 5. Analyse RGPD & éthique IA

Références consultées le 2026-11-06 : RGPD (texte publié par la CNIL, `cnil.fr/fr/reglement-europeen-protection-donnees`) ; AI Act, règlement (UE) 2024/1689 (version consolidée `artificialintelligenceact.eu` ; à vérifier sur le texte du Journal officiel avant soutenance) ; lignes directrices WP248 rév.01 sur l'AIPD ; *Guide RGPD du développeur* et fiche *Les durées de conservation des données* de la CNIL. URLs complètes en annexe `aipd.md`.

## 5.1 Nature des données et base légale

| Donnée | Qualification | Position |
|---|---|---|
| Récit transcrit, émotion, image | Peut révéler santé, vie sexuelle, convictions, traumatismes : **catégories particulières** (art. 9.1) | Traitée par défaut comme sensible, pour tous les rêves, sans tri automatique |
| Audio de la voix | Donnée personnelle ; devient **biométrique** seulement si traitée « aux fins d'identifier une personne physique de manière unique » (art. 9.1) | Jamais traitée pour identifier ni pour en extraire des émotions (ADR-001) ; supprimée après transcription |
| Compte, consentements, journaux | Données personnelles ordinaires | Minimisées (e-mail seul, identifiant pseudonyme vers les API) |

**Base légale : consentement explicite** (art. 9.2.a, « pour une ou plusieurs finalités spécifiques »). Il est **granulaire** (trois cases distinctes : transcription · génération d'image · suivi des émotions dans le temps), donné avant le premier envoi (US-03), **révocable** à tout moment depuis les réglages, et horodaté dans la table `consents` (version du texte affiché incluse). Refuser la génération d'image ou le suivi n'empêche pas d'utiliser le journal.

## 5.2 AIPD : requise

L'art. 35.1 impose une analyse d'impact lorsqu'un traitement, « en particulier par le recours à de nouvelles technologies », est susceptible d'engendrer un risque élevé. Selon WP248, un traitement qui remplit **deux critères** requiert en général une AIPD. Le nôtre en remplit quatre :

| Critère WP248 | Application au produit |
|---|---|
| 4 — données sensibles ou à caractère hautement personnel | Contenu des rêves (art. 9) |
| 1 — évaluation / notation | Classement émotionnel de chaque rêve et tendance mensuelle (US-06, US-16) |
| 8 — usage innovant de nouvelles technologies | Chaîne de modèles d'IA génératifs (STT, LLM, image) |
| 7 — personnes vulnérables | Utilisateurs sujets aux cauchemars ou traumatismes (persona Inès) |

AIPD synthétique (annexe `aipd.md`, à conduire avec l'outil PIA de la CNIL avant la bêta) — risques principaux et mesures :

| Risque pour la personne | Gravité | Mesures | Risque résiduel |
|---|---|---|---|
| Accès illégitime au contenu des rêves (fuite, employé, fournisseur) | Maximale | Chiffrement au repos et en transit, accès par compte uniquement, journaux sans contenu, ZDR demandée chez Mistral, prompt minimisé chez BFL | Limité |
| Réutilisation par un fournisseur (entraînement) | Importante | Opt-out d'entraînement activé et prouvé avant bêta (CS-04, ADR-002, ADR-004) ; fournisseurs UE | Limité, sous condition contractuelle BFL |
| Image choquante pour une personne fragile | Importante | Bouton « Ne pas générer d'image » (US-11), consigne de ton non graphique (ADR-003), aucune image affichée sans action | Négligeable |
| Lecture médicale abusive de l'humeur | Importante | Aucune interprétation (US-22 *Won't*), mention « indicateur personnel, sans valeur médicale » | Négligeable |
| Effacement incomplet | Importante | Suppression en cascade jusqu'au stockage objet, test automatisé (US-12, US-17) | Négligeable |

## 5.3 Sous-traitants : un DPA est nécessaire avec chaque fournisseur d'API

Chaque API reçoit des données personnelles pour notre compte : chacune est **sous-traitante** et l'art. 28.3 exige un contrat définissant objet, durée, nature et finalité du traitement.

| Sous-traitant | Données transmises | Lieu | DPA | Point ouvert |
|---|---|---|---|---|
| Mistral AI (STT, LLM, TTS R2) | Audio, transcription | UE par défaut | Publié (Addendum) | Activer l'opt-out ; demander la ZDR (accord discrétionnaire) |
| Black Forest Labs (image) | Prompt anglais reformulé, sans transcription | UE (`api.eu.bfl.ai`) | **Non trouvé** | Bloquant : DPA + opt-out écrit avant bêta (ADR-004) |
| Hébergeur (cloud UE, à choisir au Sprint 2) | Toutes | UE | Requis | Critère de choix |
| Service e-mail transactionnel (UE, à choisir) | E-mail, lien de connexion | UE | Requis | Critère de choix ; aucun contenu de rêve |
| Sentry (erreurs) | Traces techniques pseudonymisées, corps de requête supprimés | Région UE à retenir | Requis | Filtre ENF-10 testé ; Langfuse auto-hébergé n'est pas un sous-traitant |
| Repli : Google Gemini API payant | Prompt reformulé | Mondial (« any country ») | Publié | Transfert hors UE à documenter (garanties art. 46) |

## 5.4 AI Act

- **Hors du régime « reconnaissance des émotions »** : l'art. 3.39 vise un système qui identifie ou infère des émotions **à partir de données biométriques**, et l'art. 3.34 définit celles-ci comme issues d'un traitement technique spécifique de caractéristiques physiques, physiologiques ou comportementales. Nous classons le **texte** transcrit, jamais la voix (ADR-001).
- **Transparence des contenus générés (art. 50.2)**, applicable depuis le 2 août 2026 (art. 113) : les sorties doivent être marquées dans un format lisible par machine et détectables comme générées par IA. Mesures : mention visible « Image générée par IA » sur chaque image ; métadonnées XMP `DigitalSourceType = trainedAlgorithmicMedia` ajoutées à l'enregistrement ; signature C2PA (`c2pa-python`) en R2, aucun fournisseur retenu ne documentant de C2PA natif.

## 5.5 Éthique

- **Aucune prétention diagnostique ou thérapeutique** : ni interprétation, ni conseil, ni score de « santé » ; renvoi vers un professionnel dans l'aide.
- **Cauchemars** : image désactivable par rêve, ton visuel atténué par consigne (« évocateur et non explicite »), aucun affichage automatique en plein écran.
- **Refus du filtre de sécurité** : le rêve est conservé sans image, avec un message neutre (US-07) — jamais de message culpabilisant.
- **Biais des modèles d'image** : le prompt ne décrit pas l'apparence des personnes sauf si le récit le fait ; revue de 50 images en bêta (diversité, stéréotypes).
- **Droit à l'oubli effectif** : suppression d'un rêve ou du compte en cascade (base, stockage objet, cache CDN purgé) ; le journal d'audit ne garde que l'identifiant pseudonyme et l'action.

## 5.6 Mesures techniques et durées de conservation

| Donnée | Durée | Mécanisme |
|---|---|---|
| Audio brut | Supprimé dès la transcription validée ; **24 h maximum** si le traitement échoue | Tâche planifiée horaire |
| Transcription, émotion, image | Durée du compte ; compte inactif 24 mois → avertissement, effacement 30 jours après | Tâche planifiée quotidienne |
| Preuve du consentement | Durée du compte + 5 ans (hypothèse : prescription de droit commun, à valider par un juriste) | Table `consents`, sans contenu de rêve |
| Journaux techniques et coûts API | 6 mois (décision projet) | Logs JSON sans contenu de rêve, identifiant pseudonyme |

Autres mesures : TLS 1.2+ partout, chiffrement au repos (base et stockage objet), identifiant pseudonyme (HMAC) transmis aux API au lieu de l'identifiant interne, ZDR demandée là où elle existe, export JSON conforme à `dream.schema.json` (portabilité, US-15).
