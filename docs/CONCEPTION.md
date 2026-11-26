# Conception et décisions

## Périmètre

Le projet livre un web service, ses tests et sa documentation. Le sujet ne demande
pas d'interface utilisateur, de paiement bancaire, d'envoi d'email, de stockage
de fichiers ni de publication automatique sur des réseaux sociaux.
FastAPI fournit validation et OpenAPI ; SQLite une persistance sans service externe.
Les bibliothèques sont épinglées dans les fichiers requirements.

## Hypothèses explicites

1. **Trois étapes.** Seule la première figure dans le sujet. L'étape 2 configure les
   options et l'étape 3 publie le brouillon. L'étape 2 peut être omise si toutes les
   options restent désactivées.
2. **CRUDS.** S désigne la recherche. Les listes ont q, limit, offset et total.
   La recherche SQLite via lower est insensible à la casse ASCII ; les variantes
   Unicode accentuées doivent garder leur casse pour cette recherche textuelle.
   L'unicité des contributions utilise une normalisation Unicode casefold.
3. **Rôles.** Administrateurs et organisateurs sont aussi membres/participants.
   Le créateur conserve son rôle jusqu'à transfert ou suppression.
   Une désignation explicite comme organisateur vaut participation acceptée.
4. **Invitations.** Les participants ordinaires acceptent leur invitation.
   Les invitations sont visibles via /me/invitations après publication.
   Ajouter un membre à un groupe est une action d'administrateur, sans workflow
   d'acceptation distinct demandé par le sujet.
5. **Visibilité.** Les groupes privés et secrets sont tous deux invisibles aux tiers.
   La distinction est conservée dans les données. Leurs événements restent privés.
   Les événements publics publiés et groupes publics sont lisibles sans compte ;
   leur contenu collaboratif exige une participation confirmée.
6. **Participations séparées.** Quitter un groupe ne supprime pas les participations
   déjà acceptées à ses événements : elles se gèrent séparément.
7. **Photos.** Le service enregistre une URL HTTP(S), sans télécharger le média.
8. **Billetterie.** « Acheter » enregistre l'obtention d'un billet avec son montant.
   Aucun débit, remboursement ou prestataire de paiement. Devise EUR, en centimes.
   Le prix à l'achat est conservé même si le tarif change.
9. **Acheteur extérieur.** Email ajouté au nom/prénom/adresse pour identifier un
   acheteur sans compte. Deux contraintes empêchent les doublons : même email OU
   même identité déclarée normalisée dans un événement, tous tarifs confondus.
   Aucune vérification d'identité ou d'email : des coordonnées entièrement
   différentes peuvent contourner cette règle.
10. **Billet personnel.** Un secret aléatoire permet de lire, corriger et annuler
    son billet sans compte. Seule son empreinte SHA-256 est stockée.
    Les organisateurs gèrent aussi les billets ; les participants ne voient pas les coordonnées.
11. **Shopping list.** Quantité entière positive ; arrivée pendant l'événement.
    L'unicité porte sur le nom normalisé, pas sur des synonymes.
12. **Covoiturage.** Prix en centimes ; détour maximal en minutes.
    Places disponibles déclarées par l'auteur. Réservation et calcul d'itinéraire
    ne sont pas demandés.
13. **Suppression.** Contenus dépendants supprimés en cascade. Un groupe supprime
    ses événements ; un événement supprime ses billets. Aucun paiement réel n'étant
    traité, aucune opération bancaire n'en résulte.
14. **Sondages.** Répondre à toutes les questions à la fois. Réponse remplaçable tant
    que le sondage reste ouvert. Structure immuable dès qu'une réponse existe.
    Les résultats ne révèlent pas les votants.
15. **Options désactivées.** Données existantes conservées lisibles et supprimables ;
    création/modification bloquées. Une billetterie ayant des billets doit d'abord
    être vidée par annulation.

## Autorisations

| Action | Acteur autorisé |
|---|---|
| Inscription, connexion, présentation publique | Visiteur |
| Profil privé, modification/suppression du compte | Utilisateur lui-même |
| Recherche de profils publics | Utilisateur connecté |
| Paramètres et membres de groupe | Administrateur |
| Publication dans un groupe | Membre si autorisé, ou administrateur |
| Création d'événement de groupe | Membre si autorisé, ou administrateur |
| Paramètres, invitations, publication d'événement | Organisateur |
| Discussions, photos, contributions | Membre/participant confirmé |
| Modification/suppression d'un contenu | Auteur ou responsable du parent |
| Gestion du sondage | Organisateur |
| Réponses et résultats du sondage | Participant confirmé |
| Tarifs et liste des acheteurs | Organisateur |
| Achat de billet public | Visiteur sans compte |
| Lecture/correction/annulation de billet | Porteur du secret ou organisateur |

## Transactions et sécurité

Chaque écriture utilise une transaction BEGIN IMMEDIATE. Contrôle du stock,
insertion du billet et contraintes d'unicité restent atomiques ; une erreur
annule l'ensemble. Lectures en transaction de lecture, journal WAL activé.

Clés étrangères activées à chaque connexion. Paramètres SQL liés séparément du
texte SQL ; noms de tables provenant de constantes du code. Index sur les parents,
appartenances et champs d'accès.

Mots de passe Argon2id. Jetons aléatoires de 256 bits, empreinte seule stockée.
Champs sensibles filtrés dans les réponses et erreurs de validation.
Limitation des endpoints sensibles par IP et processus.

Références :
[tests FastAPI](https://fastapi.tiangolo.com/tutorial/testing/) ;
[transactions SQLite Python](https://docs.python.org/3.12/library/sqlite3.html#transaction-control).
