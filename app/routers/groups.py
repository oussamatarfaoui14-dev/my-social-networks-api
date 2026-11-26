from fastapi import APIRouter, HTTPException, Response

from ..db import insert, one, page, update
from ..schemas import GroupCreate, GroupInput, GroupRole
from ..security import DB, OptionalUser, Pagination, User, check_users, member, protect_last_manager, scope

router = APIRouter(prefix="/groups", tags=["Groupes"])


@router.post("", status_code=201, summary="Créer un groupe")
def create_group(body: GroupCreate, db: DB, user: User):
    """Le créateur devient administrateur et membre. Un fil Général est créé automatiquement."""
    check_users(db, body.member_ids + body.admin_ids)
    group = insert(db, "groups", body.model_dump(mode="json", exclude={"member_ids", "admin_ids"}))
    admins = {*body.admin_ids, user["id"]}
    for uid in admins | set(body.member_ids):
        insert(
            db,
            "group_members",
            {"group_id": group["id"], "user_id": uid, "role": "admin" if uid in admins else "member"},
        )
    insert(db, "threads", {"group_id": group["id"], "title": "Général"})
    return group


@router.get("", summary="Lister et rechercher les groupes accessibles")
def list_groups(db: DB, user: OptionalUser, params: Pagination):
    """Les groupes privés et secrets sont visibles uniquement par leurs membres."""
    return page(
        db,
        "groups",
        "(visibility='public' OR id IN (SELECT group_id FROM group_members WHERE user_id=?))",
        (user["id"] if user else 0,),
        fields=("name", "description"),
        **params,
    )


@router.get("/{group_id}", summary="Lire un groupe")
def read_group(group_id: int, db: DB, user: OptionalUser):
    return scope(db, "group", group_id, user)[0]


@router.put("/{group_id}", summary="Modifier les paramètres du groupe")
def edit_group(group_id: int, body: GroupInput, db: DB, user: User):
    """Administrateurs uniquement. Rendre un groupe privé/secret impose d'abord de rendre ses événements privés."""
    scope(db, "group", group_id, user, "manage")
    if (
        body.visibility != "public"
        and db.execute(
            "SELECT 1 FROM events WHERE group_id=? AND visibility='public'", (group_id,)
        ).fetchone()
    ):
        raise HTTPException(409, "Rendez les événements du groupe privés avant ce changement")
    return update(db, "groups", group_id, body.model_dump(mode="json"))


@router.delete("/{group_id}", status_code=204, summary="Supprimer un groupe et son contenu")
def delete_group(group_id: int, db: DB, user: User):
    scope(db, "group", group_id, user, "manage")
    db.execute("DELETE FROM groups WHERE id=?", (group_id,))
    return Response(status_code=204)


@router.post("/{group_id}/join", summary="Rejoindre un groupe public")
def join_group(group_id: int, db: DB, user: User):
    group = one(db, "groups", group_id)
    existing = member(db, "group", group_id, user)
    if existing:
        return existing
    if group["visibility"] != "public":
        raise HTTPException(404, "Ressource introuvable")
    return insert(db, "group_members", {"group_id": group_id, "user_id": user["id"], "role": "member"})


@router.get("/{group_id}/members", summary="Lister les membres du groupe")
def members(group_id: int, db: DB, user: User, params: Pagination):
    scope(db, "group", group_id, user, "participate")
    return page(db, "group_members", "group_id=?", (group_id,), fields=("role",), **params)


@router.put("/{group_id}/members/{user_id}", summary="Ajouter un membre ou modifier son rôle")
def set_member(group_id: int, user_id: int, body: GroupRole, db: DB, user: User):
    scope(db, "group", group_id, user, "manage")
    one(db, "users", user_id)
    if body.role != "admin":
        protect_last_manager(db, "group", group_id, user_id)
    db.execute(
        "INSERT INTO group_members(group_id,user_id,role) VALUES(?,?,?) "
        "ON CONFLICT(group_id,user_id) DO UPDATE SET role=excluded.role",
        (group_id, user_id, body.role),
    )
    return member(db, "group", group_id, {"id": user_id})


@router.delete(
    "/{group_id}/members/{user_id}", status_code=204, summary="Retirer un membre ou quitter le groupe"
)
def remove_member(group_id: int, user_id: int, db: DB, user: User):
    scope(db, "group", group_id, user, "participate" if user_id == user["id"] else "manage")
    if not member(db, "group", group_id, {"id": user_id}):
        raise HTTPException(404, "Membre introuvable")
    protect_last_manager(db, "group", group_id, user_id)
    db.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    return Response(status_code=204)
