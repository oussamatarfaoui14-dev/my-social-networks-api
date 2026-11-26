import os
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from ..db import insert, one, page, update
from ..schemas import EventCreate, EventInput, EventRole, EventSettings
from ..security import DB, OptionalUser, Pagination, User, check_users, member, protect_last_manager, scope

router = APIRouter(tags=["Événements"])


def invite_group(db, event):
    if event["group_id"] is None:
        raise HTTPException(409, "Cet événement n'appartient pas à un groupe")
    before = db.total_changes
    db.execute(
        "INSERT OR IGNORE INTO event_members(event_id,user_id,role,status) "
        "SELECT ?,user_id,'participant','invited' FROM group_members WHERE group_id=?",
        (event["id"], event["group_id"]),
    )
    return {"invited_count": db.total_changes - before}


@router.post("/events", status_code=201, summary="Étape 1 : configurer un événement")
def create_event(body: EventCreate, db: DB, user: User):
    """Crée un brouillon avec au moins un organisateur. Les participants sont invités, sans acceptation automatique.
    Dans un groupe, respecte le droit de création et permet d'inviter tous ses membres en une opération.
    """
    if body.group_id:
        group, manager = scope(db, "group", body.group_id, user, "participate")
        if not manager and not group["members_can_create_events"]:
            raise HTTPException(403, "Création d'événements interdite aux membres")
        if group["visibility"] != "public" and body.visibility == "public":
            raise HTTPException(422, "Un groupe privé ou secret ne peut pas exposer un événement public")
    elif body.invite_all_group_members:
        raise HTTPException(422, "Un groupe est requis pour inviter ses membres")
    check_users(db, body.organizer_ids + body.participant_ids)
    event = insert(
        db,
        "events",
        body.model_dump(
            mode="json", exclude={"organizer_ids", "participant_ids", "invite_all_group_members"}
        ),
    )
    organizers = {*body.organizer_ids, user["id"]}
    for uid in organizers | set(body.participant_ids):
        insert(
            db,
            "event_members",
            {
                "event_id": event["id"],
                "user_id": uid,
                "role": "organizer" if uid in organizers else "participant",
                "status": "accepted" if uid in organizers else "invited",
            },
        )
    insert(db, "threads", {"event_id": event["id"], "title": "Général"})
    if body.invite_all_group_members:
        invite_group(db, event)
    return event


@router.get("/events", summary="Lister et rechercher les événements accessibles")
def list_events(db: DB, user: OptionalUser, params: Pagination, group_id: int | None = None):
    uid = user["id"] if user else 0
    where = "((status='published' AND (visibility='public' OR id IN (SELECT event_id FROM event_members WHERE user_id=?))) OR id IN (SELECT event_id FROM event_members WHERE user_id=? AND role='organizer'))"
    args = (uid, uid)
    if group_id is not None:
        scope(db, "group", group_id, user)
        where += " AND group_id=?"
        args += (group_id,)
    return page(db, "events", where, args, fields=("name", "description", "location"), **params)


@router.get("/events/{event_id}", summary="Lire un événement")
def read_event(event_id: int, db: DB, user: OptionalUser):
    return scope(db, "event", event_id, user)[0]


@router.put("/events/{event_id}", summary="Modifier les informations principales d'un événement")
def edit_event(event_id: int, body: EventInput, db: DB, user: User):
    event, _ = scope(db, "event", event_id, user, "manage")
    if event["group_id"] and body.visibility == "public":
        if one(db, "groups", event["group_id"])["visibility"] != "public":
            raise HTTPException(422, "Les événements de ce groupe doivent rester privés")
    if body.visibility == "private" and event["ticketing_enabled"]:
        raise HTTPException(409, "Désactivez la billetterie avant de rendre l'événement privé")
    # Existing arrival/departure data must remain consistent when dates change.
    values = body.model_dump(mode="json")
    if db.execute(
        "SELECT 1 FROM shopping_items WHERE event_id=? AND (arrival_at<? OR arrival_at>?)",
        (event_id, values["starts_at"], values["ends_at"]),
    ).fetchone():
        raise HTTPException(409, "Les horaires d'arrivée existants ne respecteraient plus les dates")
    if db.execute(
        "SELECT 1 FROM carpools WHERE event_id=? AND departure_at>?", (event_id, values["ends_at"])
    ).fetchone():
        raise HTTPException(409, "Un covoiturage partirait après la fin de l'événement")
    return update(db, "events", event_id, values)


@router.put("/events/{event_id}/settings", summary="Étape 2 : activer les options de l'événement")
def settings(event_id: int, body: EventSettings, db: DB, user: User):
    """Active la shopping list, le covoiturage et la billetterie. La billetterie exige un événement public."""
    event, _ = scope(db, "event", event_id, user, "manage")
    if body.ticketing_enabled and event["visibility"] != "public":
        raise HTTPException(422, "La billetterie est réservée aux événements publics")
    if (
        not body.ticketing_enabled
        and db.execute("SELECT 1 FROM tickets WHERE event_id=?", (event_id,)).fetchone()
    ):
        raise HTTPException(409, "Annulez les billets existants avant de désactiver la billetterie")
    return update(db, "events", event_id, body.model_dump())


@router.post("/events/{event_id}/publish", summary="Étape 3 : publier l'événement")
def publish(event_id: int, db: DB, user: User):
    """Publie le brouillon. Les champs essentiels ont déjà été validés à l'étape 1. Opération idempotente."""
    scope(db, "event", event_id, user, "manage")
    return update(db, "events", event_id, {"status": "published"})


@router.delete("/events/{event_id}", status_code=204, summary="Supprimer un événement et son contenu")
def delete_event(event_id: int, db: DB, user: User):
    scope(db, "event", event_id, user, "manage")
    db.execute("DELETE FROM events WHERE id=?", (event_id,))
    return Response(status_code=204)


@router.get("/events/{event_id}/members", summary="Lister participants, organisateurs et invitations")
def members(event_id: int, db: DB, user: User, params: Pagination):
    scope(db, "event", event_id, user, "participate")
    return page(db, "event_members", "event_id=?", (event_id,), fields=("role", "status"), **params)


@router.put(
    "/events/{event_id}/members/{user_id}", summary="Inviter un participant ou désigner un organisateur"
)
def set_member(event_id: int, user_id: int, body: EventRole, db: DB, user: User):
    scope(db, "event", event_id, user, "manage")
    one(db, "users", user_id)
    existing = member(db, "event", event_id, {"id": user_id})
    if body.role != "organizer":
        protect_last_manager(db, "event", event_id, user_id)
    status = "accepted" if body.role == "organizer" else (existing["status"] if existing else "invited")
    db.execute(
        "INSERT INTO event_members(event_id,user_id,role,status) VALUES(?,?,?,?) "
        "ON CONFLICT(event_id,user_id) DO UPDATE SET role=excluded.role,status=excluded.status",
        (event_id, user_id, body.role, status),
    )
    return member(db, "event", event_id, {"id": user_id})


@router.post("/events/{event_id}/invite-group", summary="Inviter tous les membres du groupe en un clic")
def invite_all(event_id: int, db: DB, user: User):
    event, _ = scope(db, "event", event_id, user, "manage")
    if event["group_id"]:
        scope(db, "group", event["group_id"], user, "participate")
    return invite_group(db, event)


@router.post("/events/{event_id}/join", summary="Accepter une invitation ou rejoindre un événement public")
def join(event_id: int, db: DB, user: User):
    event, _ = scope(db, "event", event_id, user)
    if event["status"] != "published":
        raise HTTPException(409, "L'événement n'est pas encore publié")
    existing = member(db, "event", event_id, user)
    if existing:
        return update(db, "event_members", existing["id"], {"status": "accepted"})
    return insert(
        db,
        "event_members",
        {"event_id": event_id, "user_id": user["id"], "role": "participant", "status": "accepted"},
    )


@router.delete(
    "/events/{event_id}/members/{user_id}",
    status_code=204,
    summary="Retirer un participant ou quitter l'événement",
)
def remove_member(event_id: int, user_id: int, db: DB, user: User):
    scope(db, "event", event_id, user, "view" if user_id == user["id"] else "manage")
    if not member(db, "event", event_id, {"id": user_id}):
        raise HTTPException(404, "Participant introuvable")
    protect_last_manager(db, "event", event_id, user_id)
    db.execute("DELETE FROM event_members WHERE event_id=? AND user_id=?", (event_id, user_id))
    return Response(status_code=204)


@router.get("/events/{event_id}/share", summary="Obtenir les liens de partage social")
def share(event_id: int, db: DB, user: User):
    """Organisateurs uniquement ; événement publié/public appartenant à un groupe public. Aucun message n'est envoyé."""
    event, _ = scope(db, "event", event_id, user, "manage")
    if event["status"] != "published" or event["visibility"] != "public" or not event["group_id"]:
        raise HTTPException(409, "Le partage nécessite un événement public publié dans un groupe public")
    if one(db, "groups", event["group_id"])["visibility"] != "public":
        raise HTTPException(409, "Le groupe doit être public")
    url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/") + f"/api/v1/events/{event_id}"
    return {
        "url": url,
        "x": f"https://twitter.com/intent/tweet?url={quote(url, safe='')}&text={quote(event['name'])}",
        "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={quote(url, safe='')}",
    }


@router.get("/me/invitations", summary="Lister mes invitations à des événements publiés")
def invitations(db: DB, user: User, params: Pagination):
    return page(
        db,
        "events",
        "status='published' AND id IN (SELECT event_id FROM event_members WHERE user_id=? AND status='invited')",
        (user["id"],),
        fields=("name", "description"),
        **params,
    )
