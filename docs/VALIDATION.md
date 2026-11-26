# Résultats de validation

Contrôles locaux effectués le 26 novembre 2026 avec Python 3.12.14.

| Contrôle | Résultat |
|---|---|
| Tests pytest | **42 réussis**, aucun échec |
| Couverture des instructions applicatives | **98,95 %** |
| Ruff, analyse statique | Conforme |
| Ruff, formatage | Conforme |
| Documentation synchronisée | 93 opérations, exports reproductibles |
| Parcours d'intégration des contrats de sortie | 100 étapes, toutes les réponses validées contre JSON Schema |
| Newman 6.2.3 sur un serveur Uvicorn réel | **100 requêtes, 100 assertions, 0 échec** |
| Dernier billet sous concurrence | 8 tentatives simultanées : 1 succès, 7 conflits, aucun dépassement de stock |
| Configuration Docker Compose | Syntaxe validée |
| Démarrage du conteneur Docker local | Non exécuté : daemon Docker non démarré sur la machine |
| Publication Postman | En attente de connexion au compte ; aucune URL publique inventée |

## Périmètre des tests

- Inscription, email unique, connexion, session expirée, déconnexion, changement
  de mot de passe, profils publics/privés, suppression de compte.
- Trois visibilités de groupe, membres, rôles, protection du dernier responsable.
- Brouillon, options, publication, invitations, acceptation et partage.
- Droits de création d'événements et de publication dans un groupe.
- CRUDS et autorisations sur messages, commentaires, albums, photos,
  shopping list et covoiturage.
- Sondages : options distinctes, vote complet, mauvaise question, doublons,
  remplacement, fermeture, suppression et résultats agrégés.
- Billets : confidentialité, secret du billet, unicité sur plusieurs tarifs,
  conservation du prix à l'achat, stock, annulation et concurrence.
- Validation des dates/fuseaux, quantités, URL, pagination et champs inconnus.
- Paramètres SQL, hachage Argon2id et absence de mots de passe dans les erreurs.
- Limitation des tentatives et refus des Content-Length invalides/trop grands.

## Reproduire

~~~bash
python -m pytest --cov=app --cov-report=term-missing
python -m ruff check app tests scripts
python -m ruff format --check app tests scripts
python scripts/export_docs.py --check
~~~

Après démarrage du serveur, avec Node.js installé :

~~~bash
npx --yes newman@6.2.3 run postman/Parcours-complet.postman_collection.json -e postman/Local.postman_environment.json
~~~

Les tests Python utilisent des bases temporaires. Le scénario Newman crée puis
supprime ses propres données sur la base cible ; utiliser une base de démonstration.
Les contrôles de concurrence ne constituent pas un benchmark de charge à grande échelle.

Le workflow GitHub Actions vérifie Python 3.12, 3.13 et 3.14 et exécute aussi Newman.
Sur Python 3.12, il construit aussi l'image Docker, démarre le conteneur, appelle
/health et vérifie l'utilisateur non privilégié (UID 10001).
Les résultats distants sont consultables dans l'onglet Actions du dépôt.
