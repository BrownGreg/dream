# Journal des incidents et difficultés

Tenu au fil de l'eau. Format : symptôme → diagnostic → correctif → test de non-régression → PR.
Matière première de la section « difficultés » du rapport et du dossier de code review.

| # | Date | Ticket | Symptôme | Diagnostic | Correctif | Test de non-régression | PR |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-09 | DREAM-1 | `Lea@Example.org` à l'inscription est enregistré `Lea@example.org` ; une connexion en `lea@…` échoue et un second compte `lea@…` peut être créé. | `BaseUserManager.normalize_email` ne met en minuscules que le domaine (RFC 5321 : la partie locale est sensible à la casse), alors que la connexion normalise tout. | `SignupForm.clean_email` : minuscules + refus d'un doublon `iexact`. | `test_inscription_refuse_un_doublon_a_la_casse_pres`, `test_inscription_enregistre_les_consentements_horodates_et_connecte` | à venir |
| 2 | 2026-11-09 | DREAM-1 | Les journaux Axes affichent `username: "None"` ; le blocage portait sur l'IP seule, si bien que l'échec d'un tiers derrière la même IP bloquait tout le monde. | Axes lit par défaut le champ `USERNAME_FIELD` du modèle (`email`), alors que `AuthenticationForm` poste `username`. | `AXES_USERNAME_FORM_FIELD = "username"`. | `test_axes_journalise_l_email_saisi_et_pas_none`, `test_un_autre_compte_n_est_pas_bloque_par_les_echecs_d_un_tiers` | à venir |
| 3 | 2026-11-09 | DREAM-5 | Budget cumulé exactement égal au coupe-circuit (15,00 €) : un appel Hugging Face (prix NON PUBLIÉ, coût estimé 0) passait encore. | Comparaison stricte `dépensé + estimé > plafond` : avec un estimé nul, l'égalité ne bloque pas. | `ensure_budget` bloque d'abord si `exceeded` (dépensé ≥ plafond), puis si l'appel ferait dépasser. | `test_depassement_atteint`, `test_adapter_fake_gratuit_meme_budget_epuise` | DREAM-5 |
