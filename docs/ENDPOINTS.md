# Référence des endpoints

93 opérations HTTP vérifiées par le parcours complet.

Base : http://localhost:8000. Les identifiants des parents sont immuables.

| Méthode | URL | Fonction | Succès |
|---|---|---|---|
| GET | /health | Vérifier le service et la base | 200 |
| POST | /api/v1/users | Créer un compte | 201 |
| POST | /api/v1/auth/login | Se connecter | 200 |
| GET | /api/v1/users/me | Lire mon profil privé | 200 |
| GET | /api/v1/users | Lister et rechercher les utilisateurs | 200 |
| GET | /api/v1/users/{user_id} | Lire un profil | 200 |
| PUT | /api/v1/users/{user_id} | Mettre à jour mon profil | 200 |
| POST | /api/v1/groups | Créer un groupe | 201 |
| GET | /api/v1/groups | Lister et rechercher les groupes accessibles | 200 |
| GET | /api/v1/groups/{group_id} | Lire un groupe | 200 |
| PUT | /api/v1/groups/{group_id} | Modifier les paramètres du groupe | 200 |
| POST | /api/v1/groups/{group_id}/join | Rejoindre un groupe public | 200 |
| PUT | /api/v1/groups/{group_id}/members/{user_id} | Ajouter un membre ou modifier son rôle | 200 |
| GET | /api/v1/groups/{group_id}/members | Lister les membres du groupe | 200 |
| POST | /api/v1/events | Étape 1 : configurer un événement | 201 |
| PUT | /api/v1/events/{event_id}/settings | Étape 2 : activer les options de l'événement | 200 |
| POST | /api/v1/events/{event_id}/publish | Étape 3 : publier l'événement | 200 |
| GET | /api/v1/events | Lister et rechercher les événements accessibles | 200 |
| GET | /api/v1/events/{event_id} | Lire un événement | 200 |
| PUT | /api/v1/events/{event_id} | Modifier les informations principales d'un événement | 200 |
| PUT | /api/v1/events/{event_id}/members/{user_id} | Inviter un participant ou désigner un organisateur | 200 |
| POST | /api/v1/events/{event_id}/invite-group | Inviter tous les membres du groupe en un clic | 200 |
| GET | /api/v1/me/invitations | Lister mes invitations à des événements publiés | 200 |
| POST | /api/v1/events/{event_id}/join | Accepter une invitation ou rejoindre un événement public | 200 |
| GET | /api/v1/events/{event_id}/members | Lister participants, organisateurs et invitations | 200 |
| GET | /api/v1/events/{event_id}/share | Obtenir les liens de partage social | 200 |
| POST | /api/v1/threads | Créer un fil de discussion | 201 |
| GET | /api/v1/threads | Lister et rechercher les fils d'un groupe ou événement | 200 |
| GET | /api/v1/threads/{thread_id} | Lire un fil de discussion | 200 |
| PUT | /api/v1/threads/{thread_id} | Renommer un fil de discussion | 200 |
| POST | /api/v1/threads/{parent_id}/messages | Créer un message | 201 |
| GET | /api/v1/threads/{parent_id}/messages | Lister et rechercher un message | 200 |
| GET | /api/v1/messages/{item_id} | Lire un message | 200 |
| PUT | /api/v1/messages/{item_id} | Modifier un message | 200 |
| POST | /api/v1/messages/{parent_id}/message-comments | Créer un commentaire de message | 201 |
| GET | /api/v1/messages/{parent_id}/message-comments | Lister et rechercher un commentaire de message | 200 |
| GET | /api/v1/message-comments/{item_id} | Lire un commentaire de message | 200 |
| PUT | /api/v1/message-comments/{item_id} | Modifier un commentaire de message | 200 |
| POST | /api/v1/events/{parent_id}/albums | Créer un album photo | 201 |
| GET | /api/v1/events/{parent_id}/albums | Lister et rechercher un album photo | 200 |
| GET | /api/v1/albums/{item_id} | Lire un album photo | 200 |
| PUT | /api/v1/albums/{item_id} | Modifier un album photo | 200 |
| POST | /api/v1/albums/{parent_id}/photos | Créer une photo | 201 |
| GET | /api/v1/albums/{parent_id}/photos | Lister et rechercher une photo | 200 |
| GET | /api/v1/photos/{item_id} | Lire une photo | 200 |
| PUT | /api/v1/photos/{item_id} | Modifier une photo | 200 |
| POST | /api/v1/photos/{parent_id}/photo-comments | Créer un commentaire de photo | 201 |
| GET | /api/v1/photos/{parent_id}/photo-comments | Lister et rechercher un commentaire de photo | 200 |
| GET | /api/v1/photo-comments/{item_id} | Lire un commentaire de photo | 200 |
| PUT | /api/v1/photo-comments/{item_id} | Modifier un commentaire de photo | 200 |
| POST | /api/v1/events/{parent_id}/shopping-items | Créer une contribution à la shopping list | 201 |
| GET | /api/v1/events/{parent_id}/shopping-items | Lister et rechercher une contribution à la shopping list | 200 |
| GET | /api/v1/shopping-items/{item_id} | Lire une contribution à la shopping list | 200 |
| PUT | /api/v1/shopping-items/{item_id} | Modifier une contribution à la shopping list | 200 |
| POST | /api/v1/events/{parent_id}/carpools | Créer un trajet de covoiturage | 201 |
| GET | /api/v1/events/{parent_id}/carpools | Lister et rechercher un trajet de covoiturage | 200 |
| GET | /api/v1/carpools/{item_id} | Lire un trajet de covoiturage | 200 |
| PUT | /api/v1/carpools/{item_id} | Modifier un trajet de covoiturage | 200 |
| POST | /api/v1/events/{event_id}/polls | Créer un sondage avec ses questions et options | 201 |
| GET | /api/v1/events/{event_id}/polls | Lister et rechercher les sondages | 200 |
| GET | /api/v1/polls/{poll_id} | Lire un sondage et ses options | 200 |
| PUT | /api/v1/polls/{poll_id} | Modifier un sondage sans réponses | 200 |
| PUT | /api/v1/polls/{poll_id}/responses/me | Répondre ou remplacer mes réponses au sondage | 200 |
| GET | /api/v1/polls/{poll_id}/responses/me | Lire mes réponses au sondage | 200 |
| GET | /api/v1/polls/{poll_id}/results | Consulter les résultats agrégés du sondage | 200 |
| PATCH | /api/v1/polls/{poll_id}/state | Fermer ou rouvrir un sondage | 200 |
| POST | /api/v1/events/{event_id}/ticket-types | Créer un type de billet | 201 |
| GET | /api/v1/events/{event_id}/ticket-types | Lister et rechercher les types de billets et stocks | 200 |
| GET | /api/v1/ticket-types/{type_id} | Lire un type de billet et son stock | 200 |
| PUT | /api/v1/ticket-types/{type_id} | Modifier un type de billet | 200 |
| POST | /api/v1/events/{event_id}/tickets | Obtenir un billet sans compte utilisateur | 201 |
| GET | /api/v1/events/{event_id}/tickets | Lister et rechercher les billets vendus | 200 |
| GET | /api/v1/tickets/{ticket_id} | Lire un billet avec son secret ou comme organisateur | 200 |
| PUT | /api/v1/tickets/{ticket_id} | Corriger les coordonnées d'un billet | 200 |
| DELETE | /api/v1/tickets/{ticket_id} | Annuler un billet et libérer sa place | 204 |
| DELETE | /api/v1/ticket-types/{type_id} | Supprimer un type de billet sans ventes | 204 |
| DELETE | /api/v1/polls/{poll_id}/responses/me | Retirer mes réponses au sondage | 204 |
| DELETE | /api/v1/polls/{poll_id} | Supprimer un sondage et ses réponses | 204 |
| DELETE | /api/v1/carpools/{item_id} | Supprimer un trajet de covoiturage | 204 |
| DELETE | /api/v1/shopping-items/{item_id} | Supprimer une contribution à la shopping list | 204 |
| DELETE | /api/v1/photo-comments/{item_id} | Supprimer un commentaire de photo | 204 |
| DELETE | /api/v1/photos/{item_id} | Supprimer une photo | 204 |
| DELETE | /api/v1/albums/{item_id} | Supprimer un album photo | 204 |
| DELETE | /api/v1/message-comments/{item_id} | Supprimer un commentaire de message | 204 |
| DELETE | /api/v1/messages/{item_id} | Supprimer un message | 204 |
| DELETE | /api/v1/threads/{thread_id} | Supprimer un fil de discussion | 204 |
| DELETE | /api/v1/events/{event_id}/members/{user_id} | Retirer un participant ou quitter l'événement | 204 |
| DELETE | /api/v1/events/{event_id} | Supprimer un événement et son contenu | 204 |
| DELETE | /api/v1/groups/{group_id}/members/{user_id} | Retirer un membre ou quitter le groupe | 204 |
| DELETE | /api/v1/groups/{group_id} | Supprimer un groupe et son contenu | 204 |
| DELETE | /api/v1/users/{user_id} | Supprimer mon compte | 204 |
| PUT | /api/v1/auth/password | Changer mon mot de passe | 204 |
| POST | /api/v1/auth/logout | Révoquer toutes mes sessions | 204 |

Les descriptions détaillées, corps attendus et réponses JSON sont inclus dans la collection Postman et dans openapi.json.
Les listes acceptent q, limit et offset ; certains services proposent aussi group_id ou event_id.
Les paramètres parent_id et item_id désignent la ressource nommée dans le chemin (fil, album, photo, etc.).
