# Publication Postman

## État du rendu

Collections et environnement prêts, exemples réellement exécutés.
**Aucune URL Postman publique n'est encore vérifiée** : la connexion au compte
Postman est nécessaire. Ce point est distinct de Swagger local et du dépôt GitHub.

## Publier depuis l'interface

1. Se connecter à Postman.
2. Importer postman/My-Social-Networks.postman_collection.json dans un workspace.
3. Ouvrir la collection et choisir **View complete documentation**.
4. Choisir **Publish docs**, puis **Postman**.
5. Publier sans environnement contenant de vrais jetons ou coordonnées.
   Les valeurs de jetons du fichier fourni sont vides.
6. Copier l'URL générée et remplacer la mention « en attente » dans README.md.
7. Ajouter l'URL dans ce document et pousser la modification au dépôt.

Procédure officielle :
[Publier une documentation Postman](https://learning.postman.com/docs/publishing-your-api/publishing-your-docs).
Certains comptes d'entreprise nécessitent l'approbation de leur Community Manager.

Après modification de l'API :

~~~bash
python scripts/export_docs.py
~~~

Importer/remplacer ensuite la collection existante. Vérifier la documentation
publiée avant de remettre son URL.
