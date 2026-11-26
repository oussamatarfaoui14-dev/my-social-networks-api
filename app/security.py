import hashlib
import secrets
import time
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import database, one

DB = Annotated[object, Depends(database, scope="function")]
bearer = HTTPBearer(auto_error=False)
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("unused-comparison-password")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(encoded, plain):
    try:
        return hasher.verify(encoded, plain)
    except VerificationError:
        return False


def optional_user(db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if credentials is None:
        return None
    row = db.execute(
        "SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?",
        (digest(credentials.credentials), int(time.time())),
    ).fetchone()
    if row is None:
        raise HTTPException(401, "Session invalide ou expirée", headers={"WWW-Authenticate": "Bearer"})
    return dict(row)


OptionalUser = Annotated[dict | None, Depends(optional_user)]


def required_user(user: OptionalUser):
    if user is None:
        raise HTTPException(401, "Authentification requise", headers={"WWW-Authenticate": "Bearer"})
    return user


User = Annotated[dict, Depends(required_user)]


def pagination(
    q: str = Query("", max_length=160), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)
):
    return {"q": q, "limit": limit, "offset": offset}


Pagination = Annotated[dict, Depends(pagination)]


def new_session(db, user_id):
    raw = secrets.token_urlsafe(32)
    expires_in = 86400
    db.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
    db.execute(
        "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
        (digest(raw), user_id, int(time.time()) + expires_in),
    )
    return {"access_token": raw, "token_type": "bearer", "expires_in": expires_in}


def member(db, kind, parent_id, user):
    if user is None:
        return None
    row = db.execute(
        f"SELECT * FROM {kind}_members WHERE {kind}_id=? AND user_id=?", (parent_id, user["id"])
    ).fetchone()
    return dict(row) if row else None


def scope(db, kind, parent_id, user, permission="view"):
    entity = one(db, kind + "s", parent_id)
    membership = member(db, kind, parent_id, user)
    manager = membership and membership["role"] == ("admin" if kind == "group" else "organizer")
    accepted = membership and (kind == "group" or membership["status"] == "accepted")
    if kind == "event":
        visible = bool(membership) or (entity["visibility"] == "public" and entity["status"] == "published")
        if entity["status"] == "draft" and not manager:
            visible = False
    else:
        visible = bool(membership) or entity["visibility"] == "public"
    if not visible:
        raise HTTPException(404, "Ressource introuvable")
    if permission == "manage" and not manager:
        raise HTTPException(403, "Droits de responsable requis")
    if permission in {"participate", "post"} and not accepted:
        raise HTTPException(403, "Adhésion ou participation confirmée requise")
    if permission == "post" and kind == "group" and not manager and not entity["members_can_post"]:
        raise HTTPException(403, "Les publications des membres sont désactivées")
    return entity, bool(manager)


def public_user(row, private=False):
    return {k: v for k, v in row.items() if k != "password_hash" and (private or k != "email")}


def check_users(db, ids):
    for user_id in set(ids):
        one(db, "users", user_id)


def protect_last_manager(db, kind, parent_id, user_id):
    role = "admin" if kind == "group" else "organizer"
    current = db.execute(
        f"SELECT role FROM {kind}_members WHERE {kind}_id=? AND user_id=?", (parent_id, user_id)
    ).fetchone()
    if current and current["role"] == role:
        count = db.execute(
            f"SELECT count(*) FROM {kind}_members WHERE {kind}_id=? AND role=?", (parent_id, role)
        ).fetchone()[0]
        if count <= 1:
            raise HTTPException(409, "Il faut conserver au moins un responsable")
