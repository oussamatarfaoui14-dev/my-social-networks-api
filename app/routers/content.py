"""Discussion, album and contribution routes with shared parent-scope enforcement."""

import unicodedata
from datetime import datetime

from fastapi import APIRouter, HTTPException, Response

from ..db import insert, one, page, update
from ..schemas import AlbumInput, CarpoolInput, Content, PhotoInput, ShoppingInput, ThreadInput, ThreadUpdate
from ..security import DB, Pagination, User, scope

router = APIRouter(tags=["Contenus et contributions"])


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def parent_scope(db, table, item_id):
    if table in {"events", "groups"}:
        return table[:-1], item_id
    row = one(db, table, item_id)
    if table == "threads":
        return ("group", row["group_id"]) if row["group_id"] else ("event", row["event_id"])
    links = {
        "messages": ("threads", "thread_id"),
        "message_comments": ("messages", "message_id"),
        "albums": ("events", "event_id"),
        "photos": ("albums", "album_id"),
        "photo_comments": ("photos", "photo_id"),
        "shopping_items": ("events", "event_id"),
        "carpools": ("events", "event_id"),
    }
    parent, key = links[table]
    return parent_scope(db, parent, row[key])


@router.post("/threads", status_code=201, summary="Créer un fil de discussion")
def create_thread(body: ThreadInput, db: DB, user: User):
    """Un seul parent obligatoire : groupe OU événement. Création réservée à ses responsables."""
    kind, parent_id = ("group", body.group_id) if body.group_id else ("event", body.event_id)
    scope(db, kind, parent_id, user, "manage")
    return insert(db, "threads", body.model_dump())


@router.get("/threads", summary="Lister et rechercher les fils d'un groupe ou événement")
def list_threads(
    db: DB, user: User, params: Pagination, group_id: int | None = None, event_id: int | None = None
):
    if (group_id is None) == (event_id is None):
        raise HTTPException(422, "Précisez exactement un group_id ou event_id")
    kind, parent_id = ("group", group_id) if group_id is not None else ("event", event_id)
    scope(db, kind, parent_id, user, "participate")
    return page(db, "threads", f"{kind}_id=?", (parent_id,), fields=("title",), **params)


@router.get("/threads/{thread_id}", summary="Lire un fil de discussion")
def read_thread(thread_id: int, db: DB, user: User):
    scope(db, *parent_scope(db, "threads", thread_id), user, "participate")
    return one(db, "threads", thread_id)


@router.put("/threads/{thread_id}", summary="Renommer un fil de discussion")
def edit_thread(thread_id: int, body: ThreadUpdate, db: DB, user: User):
    scope(db, *parent_scope(db, "threads", thread_id), user, "manage")
    return update(db, "threads", thread_id, body.model_dump())


@router.delete("/threads/{thread_id}", status_code=204, summary="Supprimer un fil de discussion")
def delete_thread(thread_id: int, db: DB, user: User):
    kind, parent_id = parent_scope(db, "threads", thread_id)
    scope(db, kind, parent_id, user, "manage")
    if (
        kind == "group"
        and db.execute("SELECT count(*) FROM threads WHERE group_id=?", (parent_id,)).fetchone()[0] == 1
    ):
        raise HTTPException(409, "Un groupe doit conserver au moins un fil de discussion")
    db.execute("DELETE FROM threads WHERE id=?", (thread_id,))
    return Response(status_code=204)


def contribution_values(table, body, entity):
    values = body.model_dump(mode="json")
    if table == "shopping_items":
        if not entity["shopping_enabled"]:
            raise HTTPException(409, "La shopping list est désactivée")
        if (
            not datetime.fromisoformat(entity["starts_at"])
            <= body.arrival_at
            <= datetime.fromisoformat(entity["ends_at"])
        ):
            raise HTTPException(422, "L'arrivée doit se situer pendant l'événement")
        values["name_key"] = normalized(body.name)
    if table == "carpools":
        if not entity["carpool_enabled"]:
            raise HTTPException(409, "Le covoiturage est désactivé")
        if body.departure_at > datetime.fromisoformat(entity["ends_at"]):
            raise HTTPException(422, "Le départ ne peut pas être postérieur à la fin de l'événement")
    return values


def serialize(row):
    return {k: v for k, v in row.items() if k != "name_key"}


def register_resource(*, table, path, parent_table, parent_path, parent_key, model, fields, label):
    """Build explicit OpenAPI CRUDS operations, all using the same authorization invariant."""
    collection_path = f"/{parent_path}/{{parent_id}}/{path}"
    detail_path = f"/{path}/{{item_id}}"
    permission = "post" if table in {"messages", "message_comments"} else "participate"

    def create(parent_id: int, body, db: DB, user: User):
        kind, scope_id = parent_scope(db, parent_table, parent_id)
        entity, _ = scope(db, kind, scope_id, user, permission)
        values = contribution_values(table, body, entity)
        return serialize(insert(db, table, {**values, parent_key: parent_id, "author_id": user["id"]}))

    create.__annotations__["body"] = model
    create.__doc__ = f"Crée {label} dans le parent indiqué. Participation confirmée requise. Retourne la ressource créée avec son identifiant et son auteur."

    def listing(parent_id: int, db: DB, user: User, params: Pagination):
        scope(db, *parent_scope(db, parent_table, parent_id), user, "participate")
        result = page(db, table, f"{parent_key}=?", (parent_id,), fields=fields, **params)
        result["items"] = [serialize(row) for row in result["items"]]
        return result

    listing.__doc__ = (
        f"Liste et recherche {label} dans ce parent uniquement. Retourne items, total, limit et offset."
    )

    def read(item_id: int, db: DB, user: User):
        scope(db, *parent_scope(db, table, item_id), user, "participate")
        return serialize(one(db, table, item_id))

    def edit(item_id: int, body, db: DB, user: User):
        entity, manager = scope(db, *parent_scope(db, table, item_id), user, permission)
        row = one(db, table, item_id)
        if row["author_id"] != user["id"] and not manager:
            raise HTTPException(403, "Modification réservée à l'auteur ou au responsable")
        return serialize(update(db, table, item_id, contribution_values(table, body, entity)))

    edit.__annotations__["body"] = model
    edit.__doc__ = "Remplace les champs modifiables. Auteur ou responsable uniquement ; parent et auteur restent immuables."

    def delete(item_id: int, db: DB, user: User):
        _, manager = scope(db, *parent_scope(db, table, item_id), user, "participate")
        row = one(db, table, item_id)
        if row["author_id"] != user["id"] and not manager:
            raise HTTPException(403, "Suppression réservée à l'auteur ou au responsable")
        db.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
        return Response(status_code=204)

    for endpoint, url, method, status, summary in [
        (create, collection_path, "POST", 201, f"Créer {label}"),
        (listing, collection_path, "GET", 200, f"Lister et rechercher {label}"),
        (read, detail_path, "GET", 200, f"Lire {label}"),
        (edit, detail_path, "PUT", 200, f"Modifier {label}"),
        (delete, detail_path, "DELETE", 204, f"Supprimer {label}"),
    ]:
        router.add_api_route(
            url,
            endpoint,
            methods=[method],
            status_code=status,
            summary=summary,
            name=f"{table}_{method.lower()}",
            operation_id=f"{table}_{endpoint.__name__}",
        )


for config in [
    ("messages", "messages", "threads", "threads", "thread_id", Content, ("content",), "un message"),
    (
        "message_comments",
        "message-comments",
        "messages",
        "messages",
        "message_id",
        Content,
        ("content",),
        "un commentaire de message",
    ),
    (
        "albums",
        "albums",
        "events",
        "events",
        "event_id",
        AlbumInput,
        ("name", "description"),
        "un album photo",
    ),
    ("photos", "photos", "albums", "albums", "album_id", PhotoInput, ("caption",), "une photo"),
    (
        "photo_comments",
        "photo-comments",
        "photos",
        "photos",
        "photo_id",
        Content,
        ("content",),
        "un commentaire de photo",
    ),
    (
        "shopping_items",
        "shopping-items",
        "events",
        "events",
        "event_id",
        ShoppingInput,
        ("name",),
        "une contribution à la shopping list",
    ),
    (
        "carpools",
        "carpools",
        "events",
        "events",
        "event_id",
        CarpoolInput,
        ("departure_location",),
        "un trajet de covoiturage",
    ),
]:
    register_resource(
        **dict(
            zip(
                ("table", "path", "parent_table", "parent_path", "parent_key", "model", "fields", "label"),
                config,
                strict=True,
            )
        )
    )
