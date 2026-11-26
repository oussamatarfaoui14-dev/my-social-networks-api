# Publication Postman

## Documentation publique

[Consulter la documentation My Social Networks API](https://my-social-networks-api.docs.buildwithfern.com/).

Publication effectuée le 26 novembre 2026 depuis la collection Postman, via
**Publish docs site**, qui utilise désormais Fern dans ce compte. Le tableau de
bord indique **Live** et **Successful**. La page publique a été vérifiée dans le
navigateur et répond HTTP 200 sans authentification. Il s'agit de la documentation ;
le serveur API reste à lancer localement avec les instructions du README.

## Collections importées dans Postman

- [Référence — 93 opérations](https://oussamatarfaoui14-2789685.postman.co/workspace/a00e34b2-a514-4f7e-88e0-f47e9e3b5b9b/collection/60283666-8c28afbe-5724-4b6e-affb-c14c28dfc5ad).
- [Parcours complet — 100 requêtes](https://oussamatarfaoui14-2789685.postman.co/workspace/a00e34b2-a514-4f7e-88e0-f47e9e3b5b9b/collection/60283666-30b94339-8e78-4cc7-9720-8d74d1fb36cb).
- Environnement **My Social Networks — Local** importé ; aucun jeton réel inclus.

Les liens du workspace nécessitent les droits du compte Postman. Pour le rendu,
utiliser le lien public de documentation ci-dessus et le dépôt GitHub. Les exports
JSON sont également fournis dans le dossier postman/ pour une importation autonome.
Aucun abonnement payant n'a été souscrit.

## Mise à jour

Après modification de l'API :

~~~bash
python scripts/export_docs.py
~~~

Importer/remplacer la collection existante dans Postman, actualiser la documentation
via le flux Fern, puis vérifier les pages publiques avant de remettre leur URL.

Procédure officielle :
[Documenter une collection avec Fern](https://learning.postman.com/docs/fern/document-a-collection).
