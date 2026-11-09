<!-- Généré par tools/backlog.py — ne pas éditer -->

| ID | Exigence | Stories |
|---|---|---|
| EXF-01 | Enregistrer un récit au micro depuis le navigateur (WAV). | US-01 |
| EXF-02 | Importer un fichier .wav ou .mp3 ; refuser tout autre format, > 20 Mo ou hors 3–300 s. | US-02 |
| EXF-03 | Bloquer tout envoi à un fournisseur sans consentement explicite pour la finalité concernée ; consentements révocables et horodatés. | US-03 |
| EXF-04 | Transcrire le récit en français et afficher la transcription. | US-04 |
| EXF-05 | Permettre la correction de la transcription avant génération. | US-05 |
| EXF-06 | Classer l'émotion dominante à partir du texte parmi 6 classes (heureux, serein, neutre, étrange, mélancolique, stressant), avec icône et couleur. | US-06 |
| EXF-07 | Permettre la correction de l'émotion ; conserver la source (modèle / utilisateur). | US-14 |
| EXF-08 | Générer une image à partir du seul prompt visuel reformulé (jamais de la transcription brute). | US-07 |
| EXF-09 | Marquer chaque contenu généré : mention visible « générée par IA » et métadonnées lisibles par machine. | US-07 |
| EXF-10 | Afficher la progression par étape et, en cas d'échec, un message clair avec une action possible. | US-08 |
| EXF-11 | Option « Ne pas générer d'image » par rêve : aucun appel au générateur d'image. | US-11 |
| EXF-12 | Associer une ambiance sonore à l'émotion du rêve. | US-13 |
| EXF-22 | Lire à voix haute le titre et le résumé du rêve (voix française de synthèse). | US-23 |
| EXF-13 | Appliquer un style visuel choisi au prompt. | US-19 |
| EXF-14 | Produire une micro-vidéo de 5 s maximum à la demande. | US-20 |
| EXF-15 | Lister les rêves de l'utilisateur du plus récent au plus ancien. | US-09 |
| EXF-16 | Filtrer l'historique par émotion et l'afficher sur une frise temporelle. | US-10 |
| EXF-17 | Afficher la répartition mensuelle des émotions avec la mention « sans valeur médicale ». | US-16 |
| EXF-18 | Rappel matinal optionnel, désactivé par défaut. | US-18 |
| EXF-19 | Supprimer un rêve et tous ses fichiers (base, stockage objet, cache CDN). | US-12 |
| EXF-20 | Exporter tous les rêves en JSON valide contre dream.schema.json. | US-15 |
| EXF-21 | Supprimer le compte et toutes les données rattachées ; seul subsiste un journal d'audit pseudonymisé. | US-17 |
| ENF-01 | Latence p95 de l'étape transcription ≤ 8 s pour un récit ≤ 90 s (ADR-006). | US-04 |
| ENF-02 | Latence p95 de l'étape image ≤ 15 s (ADR-006). | US-07 |
| ENF-03 | Taux de rêves en échec ≤ 2 % sur 30 jours glissants ; retries ×2 avec backoff exponentiel (ADR-006). | US-08 |
| ENF-04 | Accusé de réception d'un envoi audio (202) en p95 ≤ 1 s hors transfert réseau (ADR-006). | US-01 |
| ENF-05 | Disponibilité mensuelle de l'API ≥ 99,5 % (ADR-006). | — |
| ENF-06 | Budget API mensuel 25 $ en bêta, alerte à 80 %, coupe-circuit de l'image à 100 %, quota 5 rêves/jour/utilisateur (ADR-007). | — |
| ENF-07 | Effacement effectif sous 24 h, y compris stockage objet et purge CDN ; audio brut supprimé après transcription, 24 h maximum. | US-12, US-17 |
| ENF-08 | Sécurité OWASP ASVS niveau 1 : TLS 1.2+, chiffrement au repos, sessions sécurisées, secrets hors dépôt, limitation de débit. | US-03 |
| ENF-09 | L'émotion est inférée du texte uniquement ; aucun traitement acoustique de la voix (ADR-001). | US-06 |
| ENF-10 | Journaux et traces sans contenu de rêve ; identifiant utilisateur pseudonymisé (HMAC). | — |
| ENF-11 | Latence p95 bout-en-bout (fin d'envoi → image affichée) ≤ 30 s (CS-02, ADR-006). | — |
| ENF-12 | Montée en charge : 50 rêves simultanés traités sans erreur autre que les quotas fournisseurs, par ajout de workers (plan de charge). | — |
