"""Deterministic executable journey, also exported as a Postman collection."""


def steps():
    result = []

    def add(name, method, path, body=None, save=None, auth="token", status=200, headers=None):
        result.append(
            dict(
                name=name,
                method=method,
                path=path,
                body=body,
                save=save or {},
                auth=auth,
                status=status,
                headers=headers or {},
            )
        )

    def user(label):
        return {
            "email": label + ".{{run_id}}@example.com",
            "first_name": label.title(),
            "last_name": "Démonstration",
            "password": "Demo-Password-2030!",
        }

    g = {
        "name": "Communauté de démonstration",
        "description": "Préparation de la rencontre annuelle",
        "icon": "calendar",
        "cover_url": "https://example.com/group.jpg",
        "visibility": "public",
        "members_can_post": True,
        "members_can_create_events": True,
    }
    e = {
        "name": "Rencontre annuelle",
        "description": "Accueil, repas et échanges entre membres",
        "starts_at": "2030-06-15T10:00:00Z",
        "ends_at": "2030-06-15T20:00:00Z",
        "location": "10 rue Exemple, Paris",
        "cover_url": "https://example.com/event.jpg",
        "visibility": "public",
    }
    buyer = {
        "email": "visiteur.{{run_id}}@example.com",
        "first_name": "Visiteur",
        "last_name": "Démonstration",
        "address_line": "1 rue Exemple",
        "postal_code": "75001",
        "city": "Paris",
        "country": "FR",
    }
    poll = {
        "title": "Préférences repas",
        "questions": [{"text": "Quel menu préférez-vous ?", "options": ["Végétarien", "Classique"]}],
    }
    add("Vérifier le service", "GET", "/health", auth=None)
    add(
        "Créer l'organisateur",
        "POST",
        "/api/v1/users",
        user("organisateur"),
        {"token": "access_token", "user_id": "user.id"},
        auth=None,
        status=201,
    )
    add(
        "Créer le participant",
        "POST",
        "/api/v1/users",
        user("participant"),
        {"participant_token": "access_token", "participant_id": "user.id"},
        auth=None,
        status=201,
    )
    add(
        "Se connecter",
        "POST",
        "/api/v1/auth/login",
        {"email": user("organisateur")["email"], "password": "Demo-Password-2030!"},
        {"token": "access_token"},
        auth=None,
    )
    add("Lire mon profil", "GET", "/api/v1/users/me")
    add("Rechercher les utilisateurs", "GET", "/api/v1/users?q=Organisateur&limit=20&offset=0")
    add("Lire un utilisateur", "GET", "/api/v1/users/{{user_id}}")
    profile = {k: v for k, v in user("organisateur").items() if k != "password"}
    add(
        "Modifier mon profil",
        "PUT",
        "/api/v1/users/{{user_id}}",
        {**profile, "bio": "Organisateur de rencontres"},
    )
    add("Créer un groupe", "POST", "/api/v1/groups", g, {"group_id": "id"}, status=201)
    add("Lister les groupes", "GET", "/api/v1/groups?q=démonstration")
    add("Lire le groupe", "GET", "/api/v1/groups/{{group_id}}")
    add("Modifier le groupe", "PUT", "/api/v1/groups/{{group_id}}", g)
    add("Rejoindre le groupe", "POST", "/api/v1/groups/{{group_id}}/join", auth="participant_token")
    add(
        "Gérer le rôle d'un membre",
        "PUT",
        "/api/v1/groups/{{group_id}}/members/{{participant_id}}",
        {"role": "member"},
    )
    add("Lister les membres", "GET", "/api/v1/groups/{{group_id}}/members")
    add(
        "Étape 1 - créer l'événement",
        "POST",
        "/api/v1/events",
        {**e, "group_id": "{{group_id}}", "invite_all_group_members": True},
        {"event_id": "id"},
        status=201,
    )
    add(
        "Étape 2 - options",
        "PUT",
        "/api/v1/events/{{event_id}}/settings",
        {"shopping_enabled": True, "carpool_enabled": True, "ticketing_enabled": True},
    )
    add("Étape 3 - publication", "POST", "/api/v1/events/{{event_id}}/publish")
    add("Lister les événements", "GET", "/api/v1/events?q=annuelle")
    add("Lire l'événement", "GET", "/api/v1/events/{{event_id}}")
    add("Modifier l'événement", "PUT", "/api/v1/events/{{event_id}}", e)
    add(
        "Inviter un participant",
        "PUT",
        "/api/v1/events/{{event_id}}/members/{{participant_id}}",
        {"role": "participant"},
    )
    add("Inviter tous les membres du groupe", "POST", "/api/v1/events/{{event_id}}/invite-group")
    add("Lister mes invitations", "GET", "/api/v1/me/invitations", auth="participant_token")
    add("Accepter l'invitation", "POST", "/api/v1/events/{{event_id}}/join", auth="participant_token")
    add("Lister les participants", "GET", "/api/v1/events/{{event_id}}/members")
    add("Obtenir les liens de partage", "GET", "/api/v1/events/{{event_id}}/share")
    add(
        "Créer un fil",
        "POST",
        "/api/v1/threads",
        {"title": "Organisation", "event_id": "{{event_id}}"},
        {"thread_id": "id"},
        status=201,
    )
    add("Lister les fils", "GET", "/api/v1/threads?event_id={{event_id}}")
    add("Lire le fil", "GET", "/api/v1/threads/{{thread_id}}")
    add("Renommer le fil", "PUT", "/api/v1/threads/{{thread_id}}", {"title": "Questions pratiques"})
    resources = [
        ("messages", "/threads/{{thread_id}}", "message_id", {"content": "Bienvenue à toutes et à tous !"}),
        (
            "message-comments",
            "/messages/{{message_id}}",
            "message_comment_id",
            {"content": "Merci pour l'organisation"},
        ),
        (
            "albums",
            "/events/{{event_id}}",
            "album_id",
            {"name": "Souvenirs", "description": "Photos de la rencontre"},
        ),
        (
            "photos",
            "/albums/{{album_id}}",
            "photo_id",
            {"url": "https://example.com/photo.jpg", "caption": "Le lieu de la rencontre"},
        ),
        ("photo-comments", "/photos/{{photo_id}}", "photo_comment_id", {"content": "Un beau souvenir"}),
        (
            "shopping-items",
            "/events/{{event_id}}",
            "shopping_item_id",
            {"name": "Jus de fruits", "quantity": 3, "arrival_at": "2030-06-15T11:00:00Z"},
        ),
        (
            "carpools",
            "/events/{{event_id}}",
            "carpool_id",
            {
                "departure_location": "Lyon",
                "departure_at": "2030-06-15T07:00:00Z",
                "price_cents": 1500,
                "available_seats": 3,
                "max_detour_minutes": 30,
            },
        ),
    ]
    for name, parent, variable, body in resources:
        add(
            f"Créer : {name}",
            "POST",
            f"/api/v1{parent}/{name}",
            body,
            {variable: "id"},
            auth="participant_token",
            status=201,
        )
        add(f"Lister et rechercher : {name}", "GET", f"/api/v1{parent}/{name}?limit=20&offset=0")
        add(f"Lire : {name}", "GET", f"/api/v1/{name}/{{{{{variable}}}}}")
        add(f"Modifier : {name}", "PUT", f"/api/v1/{name}/{{{{{variable}}}}}", body, auth="participant_token")
    add("Créer un sondage", "POST", "/api/v1/events/{{event_id}}/polls", poll, {"poll_id": "id"}, status=201)
    add("Lister les sondages", "GET", "/api/v1/events/{{event_id}}/polls")
    add("Lire le sondage", "GET", "/api/v1/polls/{{poll_id}}")
    add(
        "Modifier le sondage",
        "PUT",
        "/api/v1/polls/{{poll_id}}",
        poll,
        {"question_id": "questions.0.id", "option_id": "questions.0.options.0.id"},
    )
    add(
        "Répondre au sondage",
        "PUT",
        "/api/v1/polls/{{poll_id}}/responses/me",
        {"answers": [{"question_id": "{{question_id}}", "option_id": "{{option_id}}"}]},
        auth="participant_token",
    )
    add("Lire mes réponses", "GET", "/api/v1/polls/{{poll_id}}/responses/me", auth="participant_token")
    add("Consulter les résultats", "GET", "/api/v1/polls/{{poll_id}}/results")
    add("Fermer le sondage", "PATCH", "/api/v1/polls/{{poll_id}}/state", {"closed": True})
    add("Rouvrir le sondage", "PATCH", "/api/v1/polls/{{poll_id}}/state", {"closed": False})
    tariff = {"name": "Standard", "amount_cents": 1500, "quantity": 50}
    add(
        "Créer un tarif",
        "POST",
        "/api/v1/events/{{event_id}}/ticket-types",
        tariff,
        {"ticket_type_id": "id"},
        status=201,
    )
    add("Lister les tarifs", "GET", "/api/v1/events/{{event_id}}/ticket-types", auth=None)
    add("Lire le tarif", "GET", "/api/v1/ticket-types/{{ticket_type_id}}", auth=None)
    add("Modifier le tarif", "PUT", "/api/v1/ticket-types/{{ticket_type_id}}", tariff)
    add(
        "Obtenir un billet sans compte",
        "POST",
        "/api/v1/events/{{event_id}}/tickets",
        {**buyer, "ticket_type_id": "{{ticket_type_id}}"},
        {"ticket_id": "id", "receipt_token": "receipt_token"},
        auth=None,
        status=201,
    )
    add("Lister les billets vendus", "GET", "/api/v1/events/{{event_id}}/tickets")
    receipt = {"X-Ticket-Token": "{{receipt_token}}"}
    add("Lire mon billet", "GET", "/api/v1/tickets/{{ticket_id}}", auth=None, headers=receipt)
    add("Corriger mon billet", "PUT", "/api/v1/tickets/{{ticket_id}}", buyer, auth=None, headers=receipt)
    add(
        "Annuler mon billet",
        "DELETE",
        "/api/v1/tickets/{{ticket_id}}",
        auth=None,
        status=204,
        headers=receipt,
    )
    add("Supprimer le tarif", "DELETE", "/api/v1/ticket-types/{{ticket_type_id}}", status=204)
    add(
        "Retirer mes réponses",
        "DELETE",
        "/api/v1/polls/{{poll_id}}/responses/me",
        auth="participant_token",
        status=204,
    )
    add("Supprimer le sondage", "DELETE", "/api/v1/polls/{{poll_id}}", status=204)
    for name, _parent, variable, _body in reversed(resources):
        add(f"Supprimer : {name}", "DELETE", f"/api/v1/{name}/{{{{{variable}}}}}", status=204)
    add("Supprimer le fil", "DELETE", "/api/v1/threads/{{thread_id}}", status=204)
    add(
        "Quitter l'événement",
        "DELETE",
        "/api/v1/events/{{event_id}}/members/{{participant_id}}",
        auth="participant_token",
        status=204,
    )
    add("Supprimer l'événement", "DELETE", "/api/v1/events/{{event_id}}", status=204)
    add(
        "Quitter le groupe",
        "DELETE",
        "/api/v1/groups/{{group_id}}/members/{{participant_id}}",
        auth="participant_token",
        status=204,
    )
    add("Supprimer le groupe", "DELETE", "/api/v1/groups/{{group_id}}", status=204)
    add(
        "Supprimer le compte participant",
        "DELETE",
        "/api/v1/users/{{participant_id}}",
        auth="participant_token",
        status=204,
    )
    add(
        "Changer mon mot de passe",
        "PUT",
        "/api/v1/auth/password",
        {"current_password": "Demo-Password-2030!", "new_password": "Updated-Demo-Password!"},
        status=204,
    )
    add(
        "Se reconnecter",
        "POST",
        "/api/v1/auth/login",
        {"email": user("organisateur")["email"], "password": "Updated-Demo-Password!"},
        {"token": "access_token"},
        auth=None,
    )
    add("Supprimer le compte organisateur", "DELETE", "/api/v1/users/{{user_id}}", status=204)
    add(
        "Créer un compte pour tester la déconnexion",
        "POST",
        "/api/v1/users",
        user("session"),
        {"token": "access_token", "user_id": "user.id"},
        auth=None,
        status=201,
    )
    add("Se déconnecter", "POST", "/api/v1/auth/logout", status=204)
    add(
        "Se reconnecter pour nettoyer",
        "POST",
        "/api/v1/auth/login",
        {"email": user("session")["email"], "password": "Demo-Password-2030!"},
        {"token": "access_token"},
        auth=None,
    )
    add("Nettoyer le dernier compte", "DELETE", "/api/v1/users/{{user_id}}", status=204)
    return result
