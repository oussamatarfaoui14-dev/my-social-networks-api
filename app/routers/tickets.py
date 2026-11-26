import secrets
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response

from ..db import insert, one, page, update
from ..schemas import Buyer, TicketPurchase, TicketTypeInput
from ..security import DB, OptionalUser, Pagination, User, digest, scope
from .content import normalized

router = APIRouter(tags=["Billetterie"])
Receipt = Annotated[str | None, Header(alias="X-Ticket-Token", max_length=200)]


def inventory(db, row):
    row["sold"] = db.execute("SELECT count(*) FROM tickets WHERE ticket_type_id=?", (row["id"],)).fetchone()[
        0
    ]
    row["remaining"] = row["quantity"] - row["sold"]
    row["currency"] = "EUR"
    return row


def ticketing(db, event_id, user, permission="view", selling=False):
    event, _ = scope(db, "event", event_id, user, permission)
    if not event["ticketing_enabled"] or event["visibility"] != "public":
        raise HTTPException(409, "La billetterie n'est pas activée pour cet événement public")
    if selling and event["status"] != "published":
        raise HTTPException(409, "L'événement doit être publié avant l'achat de billets")
    return event


def buyer_values(body):
    values = body.model_dump(exclude={"ticket_type_id"})
    values["email"] = str(values["email"]).casefold()
    values["identity_key"] = "|".join(
        normalized(values[k])
        for k in ("first_name", "last_name", "address_line", "postal_code", "city", "country")
    )
    return values


def public_ticket(row):
    return {**{k: v for k, v in row.items() if k not in {"receipt_hash", "identity_key"}}, "currency": "EUR"}


def ticket_access(db, ticket_id, user, receipt):
    ticket = one(db, "tickets", ticket_id)
    if receipt and secrets.compare_digest(digest(receipt), ticket["receipt_hash"]):
        return ticket
    if user:
        try:
            scope(db, "event", ticket["event_id"], user, "manage")
            return ticket
        except HTTPException:
            pass
    raise HTTPException(404, "Billet introuvable")


@router.post("/events/{event_id}/ticket-types", status_code=201, summary="Créer un type de billet")
def create_type(event_id: int, body: TicketTypeInput, db: DB, user: User):
    """Organisateur uniquement. Montant entier en centimes EUR et quantité strictement positive."""
    ticketing(db, event_id, user, "manage")
    return inventory(db, insert(db, "ticket_types", {**body.model_dump(), "event_id": event_id}))


@router.get("/events/{event_id}/ticket-types", summary="Lister et rechercher les types de billets et stocks")
def list_types(event_id: int, db: DB, user: OptionalUser, params: Pagination):
    ticketing(db, event_id, user)
    result = page(db, "ticket_types", "event_id=?", (event_id,), **params)
    result["items"] = [inventory(db, row) for row in result["items"]]
    return result


@router.get("/ticket-types/{type_id}", summary="Lire un type de billet et son stock")
def read_type(type_id: int, db: DB, user: OptionalUser):
    row = one(db, "ticket_types", type_id)
    ticketing(db, row["event_id"], user)
    return inventory(db, row)


@router.put("/ticket-types/{type_id}", summary="Modifier un type de billet")
def edit_type(type_id: int, body: TicketTypeInput, db: DB, user: User):
    row = inventory(db, one(db, "ticket_types", type_id))
    ticketing(db, row["event_id"], user, "manage")
    if body.quantity < row["sold"]:
        raise HTTPException(409, "La quantité ne peut pas être inférieure au nombre de billets vendus")
    return inventory(db, update(db, "ticket_types", type_id, body.model_dump()))


@router.delete("/ticket-types/{type_id}", status_code=204, summary="Supprimer un type de billet sans ventes")
def delete_type(type_id: int, db: DB, user: User):
    row = inventory(db, one(db, "ticket_types", type_id))
    scope(db, "event", row["event_id"], user, "manage")
    if row["sold"]:
        raise HTTPException(409, "Annulez d'abord les billets associés")
    db.execute("DELETE FROM ticket_types WHERE id=?", (type_id,))
    return Response(status_code=204)


@router.post(
    "/events/{event_id}/tickets", status_code=201, summary="Obtenir un billet sans compte utilisateur"
)
def purchase(event_id: int, body: TicketPurchase, db: DB):
    """Billetterie publique. Un billet par email et par identité déclarée, par événement, tous tarifs confondus.
    Vérifie et réserve le stock atomiquement. Le prix à l'achat est conservé. Aucun paiement bancaire n'est exécuté.
    Conservez receipt_token : ce secret, retourné une seule fois, permet de lire, corriger ou annuler ce billet.
    """
    ticketing(db, event_id, None, selling=True)
    row = inventory(db, one(db, "ticket_types", body.ticket_type_id))
    if row["event_id"] != event_id:
        raise HTTPException(422, "Ce type de billet n'appartient pas à cet événement")
    if row["remaining"] <= 0:
        raise HTTPException(409, "Stock de billets épuisé")
    receipt = secrets.token_urlsafe(32)
    ticket = insert(
        db,
        "tickets",
        {
            **buyer_values(body),
            "event_id": event_id,
            "ticket_type_id": body.ticket_type_id,
            "receipt_hash": digest(receipt),
            "amount_cents": row["amount_cents"],
        },
    )
    return {**public_ticket(ticket), "receipt_token": receipt}


@router.get("/events/{event_id}/tickets", summary="Lister et rechercher les billets vendus")
def list_tickets(event_id: int, db: DB, user: User, params: Pagination):
    """Organisateurs uniquement : contient les coordonnées des acheteurs. Recherche par nom, prénom ou email."""
    scope(db, "event", event_id, user, "manage")
    result = page(
        db, "tickets", "event_id=?", (event_id,), fields=("first_name", "last_name", "email"), **params
    )
    result["items"] = [public_ticket(row) for row in result["items"]]
    return result


@router.get("/tickets/{ticket_id}", summary="Lire un billet avec son secret ou comme organisateur")
def read_ticket(ticket_id: int, db: DB, user: OptionalUser, x_ticket_token: Receipt = None):
    return public_ticket(ticket_access(db, ticket_id, user, x_ticket_token))


@router.put("/tickets/{ticket_id}", summary="Corriger les coordonnées d'un billet")
def edit_ticket(ticket_id: int, body: Buyer, db: DB, user: OptionalUser, x_ticket_token: Receipt = None):
    """Exige X-Ticket-Token ou le rôle organisateur. Le type, le montant et la date d'achat restent immuables."""
    ticket_access(db, ticket_id, user, x_ticket_token)
    return public_ticket(update(db, "tickets", ticket_id, buyer_values(body)))


@router.delete("/tickets/{ticket_id}", status_code=204, summary="Annuler un billet et libérer sa place")
def delete_ticket(ticket_id: int, db: DB, user: OptionalUser, x_ticket_token: Receipt = None):
    """Exige X-Ticket-Token ou le rôle organisateur. Supprime l'inscription et restitue immédiatement le stock."""
    ticket_access(db, ticket_id, user, x_ticket_token)
    db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
    return Response(status_code=204)
