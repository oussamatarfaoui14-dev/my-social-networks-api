from fastapi import APIRouter, HTTPException, Response

from ..db import insert, one, page, update
from ..schemas import Login, PasswordChange, UserCreate, UserUpdate
from ..security import (
    DB,
    DUMMY_HASH,
    Pagination,
    User,
    hasher,
    new_session,
    protect_last_manager,
    public_user,
    verify_password,
)

router = APIRouter(tags=["Utilisateurs et authentification"])


@router.post("/users", status_code=201, summary="Créer un compte")
def register(body: UserCreate, db: DB):
    """Inscription publique. Email unique sans distinction de casse, mot de passe haché Argon2id.
    Retourne le profil privé et une session Bearer valable 24 heures.
    """
    values = body.model_dump(mode="json", exclude={"password"})
    values["email"] = values["email"].casefold()
    row = insert(db, "users", {**values, "password_hash": hasher.hash(body.password)})
    return {"user": public_user(row, True), **new_session(db, row["id"])}


@router.post("/auth/login", summary="Se connecter")
def login(body: Login, db: DB):
    """Vérifie les identifiants et crée une session révocable. Erreur 401 sans révéler l'existence de l'email."""
    row = db.execute("SELECT * FROM users WHERE email=?", (str(body.email).casefold(),)).fetchone()
    valid = verify_password(row["password_hash"] if row else DUMMY_HASH, body.password)
    if row is None or not valid:
        raise HTTPException(401, "Identifiants incorrects")
    return new_session(db, row["id"])


@router.post("/auth/logout", status_code=204, summary="Révoquer toutes mes sessions")
def logout(db: DB, user: User):
    db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
    return Response(status_code=204)


@router.put("/auth/password", status_code=204, summary="Changer mon mot de passe")
def change_password(body: PasswordChange, db: DB, user: User):
    """Exige le mot de passe actuel et révoque toutes les sessions après le changement."""
    if not verify_password(user["password_hash"], body.current_password):
        raise HTTPException(403, "Mot de passe actuel incorrect")
    update(db, "users", user["id"], {"password_hash": hasher.hash(body.new_password)})
    db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
    return Response(status_code=204)


@router.get("/users/me", summary="Lire mon profil privé")
def me(user: User):
    return public_user(user, True)


@router.get("/users", summary="Lister et rechercher les utilisateurs")
def users(db: DB, user: User, params: Pagination):
    """Recherche par nom/prénom ; pagination. Les emails et mots de passe ne sont jamais exposés."""
    result = page(db, "users", fields=("first_name", "last_name"), **params)
    result["items"] = [public_user(r) for r in result["items"]]
    return result


@router.get("/users/{user_id}", summary="Lire un profil")
def read_user(user_id: int, db: DB, user: User):
    return public_user(one(db, "users", user_id), user_id == user["id"])


@router.put("/users/{user_id}", summary="Mettre à jour mon profil")
def edit_user(user_id: int, body: UserUpdate, db: DB, user: User):
    if user_id != user["id"]:
        raise HTTPException(403, "Vous pouvez modifier uniquement votre profil")
    values = body.model_dump(mode="json")
    values["email"] = values["email"].casefold()
    return public_user(update(db, "users", user_id, values), True)


@router.delete("/users/{user_id}", status_code=204, summary="Supprimer mon compte")
def delete_user(user_id: int, db: DB, user: User):
    """Suppression en cascade du contenu personnel. Transférer auparavant les responsabilités exercées seul."""
    if user_id != user["id"]:
        raise HTTPException(403, "Vous pouvez supprimer uniquement votre compte")
    for kind in ("group", "event"):
        for row in db.execute(f"SELECT {kind}_id FROM {kind}_members WHERE user_id=?", (user_id,)):
            protect_last_manager(db, kind, row[0], user_id)
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    return Response(status_code=204)
