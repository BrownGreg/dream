# Prompts Excalidraw — schémas du bloc 1

Trois prompts indépendants, à donner un par un à Claude dans le navigateur (extension Chrome), avec un onglet ouvert sur https://excalidraw.com. Chaque prompt contient le contenu exact du schéma, tiré des sources PlantUML de `docs/preprod/diagrams/` (architecture **cible** du bloc 1).

---

## Prompt 1 — C4 niveau 1 : contexte

```text
Tu travailles dans l'onglet ouvert sur https://excalidraw.com. Objectif : produire un diagramme C4 de niveau 1 (contexte) propre et lisible, puis l'exporter.

MÉTHODE (dans cet ordre)
1. Ouvre le menu des outils (icône « … » ou « More tools » dans la barre d'outils), choisis « Mermaid to Excalidraw » (parfois nommé « Text to diagram » → onglet Mermaid).
2. Colle EXACTEMENT le code Mermaid ci-dessous, clique « Insert ».
3. Mets en forme (voir RÈGLES DE STYLE), sans ajouter, retirer ni reformuler aucun élément ni libellé.
4. Exporte (voir EXPORT).

CODE MERMAID
flowchart TB
    user["<b>Rêveur</b><br/>[Personne]<br/>Raconte ses rêves au réveil,<br/>consulte son historique<br/>(Léa, Karim, Inès)"]
    ds["<b>Synthétiseur de rêves</b><br/>[Système]<br/>Journal de rêves vocal : transcription,<br/>image, ambiance, émotion, historique"]
    mistral["<b>Mistral AI (UE)</b><br/>[Système externe]<br/>STT Voxtral, LLM Mistral Small 4,<br/>TTS Voxtral (R2)"]
    bfl["<b>Black Forest Labs (UE)</b><br/>[Système externe]<br/>Génération d'image FLUX.2,<br/>endpoint api.eu.bfl.ai"]
    mail["<b>Service e-mail transactionnel (UE)</b><br/>[Système externe]<br/>Lien de connexion,<br/>alerte d'inactivité"]
    obs["<b>Observabilité</b><br/>[Système externe]<br/>Sentry / Langfuse auto-hébergé UE<br/>Erreurs, traces et coûts des appels IA"]
    user -->|"Enregistre ou importe un récit,<br/>consulte, corrige, supprime, exporte<br/>[HTTPS]"| ds
    ds -->|"Audio du récit, transcription →<br/>prompt visuel + émotion, résumé à lire<br/>[HTTPS/JSON, multipart]"| mistral
    ds -->|"Prompt visuel anglais reformulé<br/>(sans transcription)<br/>[HTTPS/JSON]"| bfl
    ds -->|"E-mail de l'utilisateur, lien magique<br/>[HTTPS]"| mail
    ds -->|"Événements techniques pseudonymisés,<br/>sans contenu de rêve<br/>[HTTPS]"| obs

RÈGLES DE STYLE
- Disposition : Rêveur en haut au centre, Synthétiseur de rêves au centre, les 4 systèmes externes alignés sur une rangée en bas, espacés régulièrement (au moins 80 px entre deux boîtes).
- Couleurs C4 : Rêveur fond #08427B ; Synthétiseur de rêves fond #1168BD ; systèmes externes fond #8C8496. Texte blanc dans ces boîtes. Bordures de la même couleur que le fond.
- Toutes les boîtes : rectangles à coins arrondis, largeur identique par rangée, texte centré. Nom en gras, taille de police « M » ; le reste en « S ».
- Flèches : droites ou coudées (pas de courbes qui se croisent), gris foncé #333333, libellé posé à côté de la flèche sans chevaucher les boîtes. Aucune flèche ne doit en croiser une autre.
- Police : choisis la police « Normal » (sans serif), PAS la police manuscrite. Style de trait : « Architect » (trait net, sans effet crayonné). Remplissage : « Solid ».
- Titre au-dessus du schéma, police L : « Synthétiseur de rêves — C4 niveau 1 : contexte ».
- Légende en bas à droite : 3 petits carrés colorés (Personne, Système, Système externe).

EXPORT
- Menu → « Export image » : fond blanc, échelle 2×, « Embed scene » coché. Exporte en PNG nommé c4_context.png ET en SVG nommé c4_context.svg.
- Menu → « Save to… » : enregistre aussi c4_context.excalidraw.
- Avant d'exporter, vérifie visuellement : aucun texte qui déborde de sa boîte, aucun libellé qui chevauche une flèche ou une boîte, tout est lisible au zoom 100 %.
```

---

## Prompt 2 — C4 niveau 2 : conteneurs

```text
Tu travailles dans l'onglet ouvert sur https://excalidraw.com. Objectif : produire un diagramme C4 de niveau 2 (conteneurs) propre et lisible, puis l'exporter. Commence par une scène vide (Menu → « Reset the canvas » si nécessaire).

MÉTHODE (dans cet ordre)
1. Menu des outils (« … » / « More tools ») → « Mermaid to Excalidraw » (onglet Mermaid de « Text to diagram »).
2. Colle EXACTEMENT le code Mermaid ci-dessous, clique « Insert ».
3. Réorganise et mets en forme (voir RÈGLES DE STYLE), sans ajouter, retirer ni reformuler aucun élément ni libellé.
4. Exporte (voir EXPORT).

CODE MERMAID
flowchart TB
    user["<b>Rêveur</b><br/>[Personne]<br/>Navigateur mobile ou bureau"]
    subgraph ds["Synthétiseur de rêves — hébergement UE"]
        web["<b>Front web</b><br/>[Streamlit (MVP, bêta) → Next.js (après R3)]<br/>Enregistrement micro, import,<br/>historique, consentements"]
        cdn["<b>CDN</b><br/>[Cache HTTP UE]<br/>Sert les images et ambiances<br/>via URL signées à durée courte"]
        api["<b>API</b><br/>[Python 3.12, FastAPI]<br/>Authentification, validation audio,<br/>quotas, endpoints REST /v1"]
        queue[("<b>File de tâches</b><br/>[Redis 7 + Arq]<br/>Jobs idempotents (clé = dream_id)")]
        worker["<b>Worker de génération</b><br/>[Python 3.12, Arq, httpx]<br/>Orchestre STT → LLM → image ∥ ambiance,<br/>retries, coupe-circuit budget"]
        sched["<b>Tâches planifiées</b><br/>[Arq cron]<br/>Purge audio (1 h), inactivité (24 h),<br/>agrégats de coûts"]
        db[("<b>Base relationnelle</b><br/>[PostgreSQL 16, chiffrée au repos]<br/>Utilisateurs, consentements, rêves,<br/>analyses, coûts, audit")]
        s3[("<b>Stockage objet</b><br/>[S3-compatible UE, chiffré (SSE)]<br/>Audio transitoire, images, ambiances")]
    end
    mistral["<b>Mistral AI (UE)</b><br/>[Système externe]<br/>STT, LLM, TTS"]
    bfl["<b>Black Forest Labs (UE)</b><br/>[Système externe]<br/>FLUX.2"]
    obs["<b>Observabilité</b><br/>[Système externe]<br/>Sentry, Langfuse, OpenTelemetry"]
    user -->|"Utilise [HTTPS]"| web
    user -->|"Télécharge images et sons<br/>[HTTPS, URL signée 15 min]"| cdn
    web -->|"Appels REST (JSON, audio en multipart)<br/>[HTTPS, jeton de session]"| api
    api -->|"Dépose l'audio reçu [S3 API, TLS]"| s3
    api -->|"Lit / écrit rêves, consentements, quotas [SQL/TLS]"| db
    api -->|"Enfile process_dream(dream_id) [RESP/TLS]"| queue
    worker -->|"Consomme les jobs [RESP/TLS]"| queue
    worker -->|"Lit l'audio, écrit image et ambiance,<br/>supprime l'audio [S3 API, TLS]"| s3
    worker -->|"Écrit transcription, émotion,<br/>assets, api_calls [SQL/TLS]"| db
    worker -->|"Audio → texte, texte → prompt + émotion (JSON)<br/>[HTTPS]"| mistral
    worker -->|"Prompt visuel → image<br/>(récupérée sous 10 min) [HTTPS]"| bfl
    sched -->|"Purge et agrégats [SQL/TLS]"| db
    sched -->|"Supprime audio > 24 h [S3 API]"| s3
    cdn -->|"Origine [HTTPS]"| s3
    api -->|"Traces, erreurs (sans contenu)<br/>[OTLP/HTTPS]"| obs
    worker -->|"Traces, latence et coût<br/>par appel IA [OTLP/HTTPS]"| obs

RÈGLES DE STYLE
- Disposition en 4 niveaux pour éviter les croisements :
  · Niveau 1 (haut) : Rêveur, centré.
  · Niveau 2 : Front web (sous le Rêveur) et CDN (à droite).
  · Niveau 3 : API au centre, File de tâches à sa droite, Worker de génération à droite de la file, Tâches planifiées à gauche de l'API.
  · Niveau 4 : Base relationnelle et Stockage objet, sous l'API et le Worker.
  · Systèmes externes (Mistral, BFL, Observabilité) en colonne à DROITE, à l'extérieur du cadre, face au Worker.
- Cadre « Synthétiseur de rêves — hébergement UE » : rectangle en pointillés gris #999999, sans remplissage, titre en haut à gauche ; il contient les 8 conteneurs et rien d'autre.
- Couleurs C4 : Rêveur #08427B ; conteneurs #438DD5 ; base, stockage et file de tâches (cylindres) #438DD5 ; systèmes externes #8C8496. Texte blanc dans toutes les boîtes colorées.
- Boîtes : rectangles arrondis de même largeur par niveau ; cylindres pour la base, le stockage et la file. Nom en gras (police M), techno entre crochets et description en police S.
- Flèches : coudées (« elbow ») de préférence, gris foncé #333333, aucune flèche ne traverse une boîte ; limite les croisements au strict minimum. Libellés en police S, posés près de la flèche, sans chevaucher les boîtes. Si un libellé est trop long, coupe-le sur deux lignes mais n'en change pas les mots.
- Police « Normal » (sans serif), PAS manuscrite. Trait « Architect ». Remplissage « Solid ».
- Titre au-dessus, police L : « Synthétiseur de rêves — C4 niveau 2 : conteneurs (architecture cible de production) ».
- Légende en bas à droite : Personne, Conteneur, Base / stockage / file, Système externe.

EXPORT
- « Export image » : fond blanc, échelle 2×, « Embed scene » coché → c4_container.png et c4_container.svg.
- « Save to… » → c4_container.excalidraw.
- Avant d'exporter : tout est lisible à 100 %, aucun texte ne déborde, aucune flèche ne passe sous une boîte.
```

---

## Prompt 3 — Séquence clé : traitement complet d'un rêve

```text
Tu travailles dans l'onglet ouvert sur https://excalidraw.com. Objectif : produire un diagramme de séquence UML clair, puis l'exporter. Commence par une scène vide.

MÉTHODE (dans cet ordre)
1. Menu des outils (« … » / « More tools ») → « Mermaid to Excalidraw ».
2. Colle EXACTEMENT le code Mermaid ci-dessous, clique « Insert ».
3. Mets en forme (voir RÈGLES DE STYLE) sans ajouter, retirer ni reformuler aucun message.
4. Exporte (voir EXPORT).

CODE MERMAID
sequenceDiagram
    autonumber
    actor U as Rêveur
    participant W as Front web
    participant A as API (FastAPI)
    participant DB as PostgreSQL
    participant S3 as Stockage objet
    participant Q as File (Redis/Arq)
    participant K as Worker
    participant STT as Mistral STT
    participant LLM as Mistral LLM
    participant T2I as BFL FLUX.2

    rect rgb(232, 240, 254)
    Note over U,Q: Phase 1 — Envoi (synchrone, dans la requête HTTP)
    U->>W: enregistre / importe un récit
    W->>A: POST /v1/dreams (multipart audio, image_disabled)
    A->>A: contrôles : session, consentement « transcription »,<br/>quota 5/jour, .wav/.mp3, ≤ 20 Mo, 3–300 s
    alt fichier invalide ou consentement absent
        A-->>W: 422 audio_invalid / 403 consent_required
        W-->>U: message clair + action (réenregistrer, consentir)
    else quota dépassé
        A-->>W: 429 quota_exceeded (reset_at)
    end
    A->>S3: PUT audio (chiffré)
    A->>DB: INSERT dreams(status=received), audio_assets
    A->>Q: enqueue process_dream(dream_id) [idempotence = dream_id]
    A-->>W: 202 Accepted {dream_id, status_url}
    W->>A: GET /v1/dreams/{id} (sondage 2 s, puis SSE en R2)
    end

    rect rgb(236, 248, 238)
    Note over Q,T2I: Phase 2 — Traitement (asynchrone, worker)
    Q->>K: process_dream(dream_id)
    K->>DB: verrou « dream_id » (déjà fait ? → fin)
    K->>S3: GET audio
    K->>STT: POST /v1/audio/transcriptions (language=fr)
    alt timeout (30 s) ou 5xx/429
        K->>STT: retry ×2, backoff exponentiel (0,5 s puis 1 s)
        opt échec définitif
            K->>DB: status=failed, error_code=stt_unavailable (audio conservé ≤ 24 h)
            W-->>U: « Transcription indisponible, réessayez » + bouton Relancer
        end
    end
    STT-->>K: {text, usage.prompt_audio_seconds}
    K->>DB: INSERT transcriptions, api_calls(cost)
    K->>S3: DELETE audio, audio_assets.purged_at = now()
    K->>LLM: POST /v1/chat/completions (schéma DreamAnalysis)
    LLM-->>K: {title, visual_prompt, emotion, confidence}
    K->>K: validation Pydantic (1 nouvel essai si non conforme)
    K->>DB: INSERT emotion_analyses(source=model), status=analyzed
    alt image_disabled, consentement image absent ou budget épuisé (ADR-007)
        K->>DB: generations(status=skipped)
    else génération
        par image
            K->>T2I: POST génération (prompt visuel)
            alt rejet du filtre de sécurité
                T2I-->>K: refus modération
                K->>DB: generations(status=rejected, reason=safety)
            else succès
                T2I-->>K: URL résultat (expire 10 min)
                K->>S3: copie immédiate de l'image + métadonnées « IA »
                K->>DB: generation_assets(ai_generated=true), api_calls(cost)
            end
        and ambiance
            K->>K: choix de la boucle d'ambiance selon l'émotion (ADR-005)
        end
    end
    K->>DB: status=done
    end

    rect rgb(254, 243, 230)
    Note over U,A: Phase 3 — Restitution
    W->>A: GET /v1/dreams/{id}
    A-->>W: 200 {transcription, émotion, URL signées 15 min}
    W-->>U: image + « Image générée par IA », icône d'émotion, ambiance
    end

RÈGLES DE STYLE
- Si l'import Mermaid ignore les bandes colorées (rect), recrée-les à la main : trois grands rectangles sans bordure, placés DERRIÈRE les messages (Menu contextuel → « Send to back »), couleurs bleu pâle #E8F0FE (Phase 1), vert pâle #ECF8EE (Phase 2), orange pâle #FEF3E6 (Phase 3), chacun avec son titre en gras en haut à gauche.
- Participants : boîtes de même largeur, espacées régulièrement, alignées en haut ; Rêveur en bonhomme. Lignes de vie en pointillés gris.
- Messages : police S, libellé au-dessus de la flèche, jamais coupé par une autre ligne. Flèches pleines pour les appels, pointillées pour les réponses. Numéros (autonumber) conservés.
- Cadres alt / opt / par : contour gris #666666, mot-clé (« alt », « opt », « par ») et condition en gras en haut à gauche ; séparation des branches en pointillés.
- Augmente l'espacement vertical entre les messages si des libellés se chevauchent : chaque message doit être lisible seul.
- Police « Normal » (sans serif), PAS manuscrite. Trait « Architect ».
- Titre au-dessus, police L : « Traitement complet d'un rêve (architecture cible) ».

EXPORT
- « Export image » : fond blanc, échelle 2×, « Embed scene » coché → sequence_reve.png et sequence_reve.svg.
- « Save to… » → sequence_reve.excalidraw.
- Avant d'exporter : zoome à 100 % et vérifie chaque message de haut en bas ; aucun texte tronqué ou superposé.
```

---

## Après les exports

Dépose les fichiers dans `docs/preprod/diagrams/excalidraw/`, puis dis-le à Claude Code : il remplacera les images dans les deux dossiers (Typst et Eisvogel) et vérifiera le nombre de pages.
