# My Social Networks API — v2.0.0

API REST réalisée à partir du cahier des charges **My Social Networks API v2.0.0** :
utilisateurs, événements, groupes, discussions, albums, sondages, billetterie,
shopping list et **covoiturage bonus**.

**93 opérations HTTP**, authentification, droits d'accès, base persistante, collection
Postman documentée et parcours de démonstration de **100 requêtes**.

## Démarrage rapide

Prérequis : Python 3.12, 3.13 ou 3.14.

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Sous Windows, remplacer l'activation par .venv\Scripts\activate.
Pour exécuter seulement l'API, installer requirements.txt.
La base data/social.db est créée automatiquement au premier démarrage.

- API : http://localhost:8000/api/v1
- Swagger interactif : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc
- OpenAPI : http://localhost:8000/openapi.json
- Santé : http://localhost:8000/health

Alternative Docker, lorsque Docker Desktop est démarré :

~~~bash
docker compose up --build -d
~~~

Le volume social-data conserve les données. Le port est lié uniquement à
127.0.0.1. Le conteneur s'exécute avec un utilisateur non privilégié.

## Essayer avec Postman

1. Importer [la référence de l'API](postman/My-Social-Networks.postman_collection.json),
   [le parcours complet](postman/Parcours-complet.postman_collection.json)
   et [l'environnement local](postman/Local.postman_environment.json).
2. Démarrer l'API et sélectionner l'environnement local.
3. Exécuter **Parcours complet** dans le Collection Runner, dans l'ordre.
   Les identifiants et jetons sont récupérés automatiquement.
4. Les 100 requêtes créent des données fictives, parcourent les 93 opérations,
   vérifient les codes HTTP et suppriment toutes leurs données à la fin.
5. Pour des essais manuels, utiliser **Référence**, s'inscrire ou se connecter,
   puis renseigner token et les identifiants correspondants dans les variables
   de cette collection.

La référence contient les URL, explications fonctionnelles, corps de requêtes,
contrats et exemples de réponses. Elle ne contient aucun véritable secret.
La référence s'utilise par requête ; le parcours complet respecte l'ordre des dépendances.

**URL de documentation Postman publiée : en attente de connexion au compte Postman.**
Le fichier [PUBLICATION.md](docs/PUBLICATION.md) indique comment terminer cette
exigence du rendu ; aucune URL de publication fictive n'est fournie.

## Authentification et conventions

POST /api/v1/users inscrit un utilisateur et retourne son profil, access_token,
token_type et expires_in. POST /api/v1/auth/login ouvre une nouvelle session.
Envoyer ensuite l'en-tête Authorization: Bearer suivi du jeton.
Les sessions durent 24 heures ; déconnexion et changement de mot de passe les révoquent.

- Mots de passe : 10 à 128 caractères, stockage Argon2id.
- Profils des autres utilisateurs : aucun email ni mot de passe exposé.
- Dates : ISO 8601 avec fuseau obligatoire ; stockage et réponses en UTC.
- Montants : entiers en **centimes EUR**, jamais des nombres décimaux flottants.
- Listes : items, total, limit, offset ; q pour rechercher, limit entre 1 et 100.
- PUT remplace les champs modifiables ; parents et auteurs restent immuables.
- 201 à la création, 200 à la lecture/modification, 204 à la suppression.
- Erreurs : 401, 403, 404, 409, 422, 429, et 503 si la base reste occupée.
- Les ressources privées inaccessibles retournent 404 pour ne pas divulguer leur existence.

## Parcours de création d'événement

1. POST /events : informations principales, organisateurs, invitations ; état draft.
2. PUT /events/{id}/settings : options shopping list, covoiturage et billetterie.
3. POST /events/{id}/publish : passage à l'état published.

Ces URL sont relatives à /api/v1. Le sujet annonce trois étapes mais décrit
uniquement la première. Les deux suivantes constituent un choix d'implémentation,
explicité dans [les décisions de conception](docs/CONCEPTION.md).

Le créateur est toujours responsable et participant. Les autres participants
reçoivent une invitation ; POST /events/{id}/join l'accepte.
Un événement public peut aussi être rejoint directement.

## Vérification

~~~bash
python -m pytest --cov=app --cov-report=term-missing
python -m ruff check app tests scripts
python -m ruff format --check app tests scripts
python scripts/export_docs.py --check
~~~

L'exporteur exécute le parcours sur une base temporaire, vérifie **toutes les
réponses contre leurs schémas JSON**, contrôle que chaque opération est couverte
et que les données de démonstration sont supprimées.
Sans --check, il régénère les collections, l'environnement, OpenAPI et la liste des endpoints.
Un workflow GitHub Actions répète ces contrôles sur Python 3.12, 3.13 et 3.14.

Les résultats réellement observés figurent dans [VALIDATION.md](docs/VALIDATION.md).

## Organisation du code

~~~text
app/
  main.py              application, erreurs et protections HTTP
  db.py                transactions et accès SQL paramétré
  schema.sql           tables, clés étrangères, contraintes et index
  schemas.py           validation des entrées
  response_docs.py     contrats de sortie OpenAPI
  security.py          sessions et autorisations par groupe/événement
  routers/             utilisateurs, groupes, événements, contenus, sondages, billets
tests/                 scénarios fonctionnels, droits, conflits et concurrence
scripts/               parcours de démonstration et export de la documentation
postman/               collections et environnement importables
docs/                  conception, modèle relationnel, conformité et exploitation
~~~

## Choix et limites explicites

Le sujet ne précise pas les outils vus en cours. **Python/FastAPI et SQLite** sont
donc le choix retenu en l'absence de précision sur la pile imposée.
Les photos sont référencées par URL HTTP(S), sans stockage de fichiers.
La billetterie gère les billets, les coordonnées, le montant à l'achat et le stock ;
elle n'exécute aucun paiement bancaire, non demandé dans le sujet.

L'unicité d'un acheteur est contrôlée par email et identité déclarée normalisée
(nom, prénom, adresse) pour chaque événement. Elle ne constitue pas une
vérification d'identité réelle. Les liens de partage sont retournés sans publier
sur un réseau social. Aucun envoi d'email n'est nécessaire au fonctionnement.

SQLite convient à ce rendu et à une instance de taille modérée. Une mise en
production à l'échelle de Facebook nécessite notamment une base adaptée, un
stockage média, une architecture distribuée et des essais de charge dédiés.
Voir [EXPLOITATION.md](docs/EXPLOITATION.md).

## Documents du rendu

- [Matrice de conformité au sujet](docs/CONFORMITE.md)
- [Conception et hypothèses](docs/CONCEPTION.md)
- [Modèle relationnel](docs/MODELE.md)
- [Référence des 93 opérations](docs/ENDPOINTS.md)
- [Contrat OpenAPI](docs/openapi.json)
- [Exploitation et configuration](docs/EXPLOITATION.md)
- [Publication de la documentation Postman](docs/PUBLICATION.md)
- [Résultats de validation](docs/VALIDATION.md)
