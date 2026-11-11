# 10 questions probables du jury

Réponses courtes, avec le fichier à ouvrir pour montrer la preuve.

**1. Pourquoi le traitement IA ne tourne-t-il pas dans la requête HTTP ?**
Il dure environ 30 s (objectif ADR-006) et dépend de quatre fournisseurs externes. Dans la requête, il bloquerait un processus gunicorn et échouerait au premier délai réseau. La vue crée le rêve et met la tâche en file après le commit (`on_commit`) ; elle répond en 50 à 60 ms au p50. Le navigateur suit l'avancement par polling HTMX. → `dreams/views.py`, `dreams/tasks.py`, `docs/diagrams/sequence_reve.svg`.

**2. Pourquoi une file de tâches en base plutôt que Celery et Redis ?**
Django 6 fournit l'API `django.tasks` ; le backend en base évite un broker à payer et à superviser, puisque PostgreSQL est déjà là. Le test de charge a vérifié que la base n'est pas le goulot : c'est le nombre de workers (ADR-008, `docs/tests/charge/`).

**3. Que se passe-t-il si le worker plante au milieu d'un rêve ?**
`process_dream` est idempotente. Chaque étape enregistre son résultat avant la suivante ; une reprise repart de l'étape manquante sans rejouer un appel déjà payé. Un verrou PostgreSQL par rêve empêche deux workers de traiter le même. Aucune exception ne laisse un rêve « en cours » indéfiniment : il passe `failed` avec un code. → `dreams/pipeline.py`, `dreams/locks.py`, `test_pipeline.py`.

**4. Comment le budget de 20 € est-il garanti par le code ?**
Avant chaque tentative d'appel, retries compris, la somme des coûts de `ApiCall` est comparée au coupe-circuit de 15 €. Au-delà, aucune requête ne part et le rêve se dégrade (lexique, pas d'image). → fiche 3, `dreams/services/http.py`, `budget.py`.

**5. Pourquoi ne pas rejouer les erreurs 4xx ?**
Une 4xx signale une requête invalide : clé, format, contenu refusé. La rejouer coûte du temps et parfois de l'argent pour le même résultat. Seuls 408, 429, 5xx et les délais dépassés sont passagers. → `errors.py`, `test_4xx_non_passagere_jamais_rejouee`.

**6. Comment garantissez-vous que le contenu des rêves n'apparaît pas dans les logs ?**
structlog masque les clés sensibles avant écriture. Sentry a les variables locales désactivées et un `before_send` qui masque les mêmes champs. Les textes sont chiffrés en base. Un test envoie un récit et vérifie qu'il n'apparaît ni dans les journaux ni dans l'événement Sentry. → `config/observability.py`, `test_observability.py`.

**7. Pourquoi l'émotion est-elle déduite du texte et non de la voix ?**
La reconnaissance d'émotions à partir de données biométriques, dont la voix, relève d'une catégorie encadrée par l'AI Act. Le texte évite cette requalification (risque R-04, ADR-001). Et l'audio est supprimé dès la transcription réussie.

**8. Votre couverture est de 99 % : est-ce que cela prouve que l'application marche ?**
Non. Le bug critique n° 9 (MediaRecorder) est passé à travers une couverture déjà très haute : les fixtures ne ressemblaient pas aux fichiers réels. C'est le test E2E dans un vrai navigateur qui l'a trouvé. La couverture mesure ce qui est exécuté, pas ce qui est vérifié face au réel. → fiche 1.

**9. Quel est le goulot de performance et comment le leveriez-vous ?**
L'attente en file. Un worker traite environ 14 rêves par minute en simulation. À 50 utilisateurs, le p95 de bout en bout passe de 72,4 s avec 1 worker à 24,2 s avec 3. En production, il faudrait ajouter des workers (offre Render payante). Autre point connu : la mesure de durée d'un webm sans durée (jusqu'à 0,75 s) est faite dans la requête. → `docs/tests/performance.md`, fiche 1.

**10. Si un fournisseur tombe en panne pendant la démonstration ?**
Émotion : Hugging Face, puis Mistral, puis le lexique local, qui ne peut pas échouer. Image : rêve `partial`, le reste est conservé et l'image peut être régénérée. Transcription : rêve `failed` avec un message clair ; l'audio n'est supprimé qu'après une transcription réussie. Démonstrable sans réseau avec `AI_MODE=fake` et `AI_FAKE_FAIL_STEPS=image`.
