from fastapi import APIRouter, HTTPException, Response

from ..db import insert, one, page, update
from ..schemas import PollInput, PollState, Vote
from ..security import DB, Pagination, User, scope

router = APIRouter(tags=["Sondages"])


def full_poll(db, poll):
    poll["questions"] = []
    for question in db.execute("SELECT * FROM questions WHERE poll_id=? ORDER BY id", (poll["id"],)):
        q = dict(question)
        q["options"] = [
            dict(r) for r in db.execute("SELECT * FROM options WHERE question_id=? ORDER BY id", (q["id"],))
        ]
        poll["questions"].append(q)
    return poll


def add_questions(db, poll_id, questions):
    for question in questions:
        q = insert(db, "questions", {"poll_id": poll_id, "text": question.text})
        for text in question.options:
            insert(db, "options", {"question_id": q["id"], "text": text})


def access_poll(db, poll_id, user, permission="participate"):
    poll = one(db, "polls", poll_id)
    scope(db, "event", poll["event_id"], user, permission)
    return poll


@router.post(
    "/events/{event_id}/polls", status_code=201, summary="Créer un sondage avec ses questions et options"
)
def create_poll(event_id: int, body: PollInput, db: DB, user: User):
    """Organisateur uniquement. Au moins une question, au moins deux options distinctes par question."""
    scope(db, "event", event_id, user, "manage")
    poll = insert(db, "polls", {"event_id": event_id, "title": body.title})
    add_questions(db, poll["id"], body.questions)
    return full_poll(db, poll)


@router.get("/events/{event_id}/polls", summary="Lister et rechercher les sondages")
def list_polls(event_id: int, db: DB, user: User, params: Pagination):
    scope(db, "event", event_id, user, "participate")
    result = page(db, "polls", "event_id=?", (event_id,), fields=("title",), **params)
    result["items"] = [full_poll(db, row) for row in result["items"]]
    return result


@router.get("/polls/{poll_id}", summary="Lire un sondage et ses options")
def read_poll(poll_id: int, db: DB, user: User):
    return full_poll(db, access_poll(db, poll_id, user))


@router.put("/polls/{poll_id}", summary="Modifier un sondage sans réponses")
def edit_poll(poll_id: int, body: PollInput, db: DB, user: User):
    """Remplace le titre et les questions. Refus 409 dès qu'une réponse existe, pour préserver les votes."""
    access_poll(db, poll_id, user, "manage")
    if db.execute(
        "SELECT 1 FROM answers WHERE question_id IN (SELECT id FROM questions WHERE poll_id=?)", (poll_id,)
    ).fetchone():
        raise HTTPException(409, "Un sondage ayant des réponses ne peut plus être restructuré")
    db.execute("DELETE FROM questions WHERE poll_id=?", (poll_id,))
    add_questions(db, poll_id, body.questions)
    return full_poll(db, update(db, "polls", poll_id, {"title": body.title}))


@router.patch("/polls/{poll_id}/state", summary="Fermer ou rouvrir un sondage")
def state(poll_id: int, body: PollState, db: DB, user: User):
    access_poll(db, poll_id, user, "manage")
    return update(db, "polls", poll_id, body.model_dump())


@router.delete("/polls/{poll_id}", status_code=204, summary="Supprimer un sondage et ses réponses")
def delete_poll(poll_id: int, db: DB, user: User):
    access_poll(db, poll_id, user, "manage")
    db.execute("DELETE FROM polls WHERE id=?", (poll_id,))
    return Response(status_code=204)


@router.put("/polls/{poll_id}/responses/me", summary="Répondre ou remplacer mes réponses au sondage")
def vote(poll_id: int, body: Vote, db: DB, user: User):
    """Participant confirmé uniquement. Exactement une option valide pour chacune des questions, en une transaction."""
    poll = access_poll(db, poll_id, user)
    if poll["closed"]:
        raise HTTPException(409, "Le sondage est fermé")
    questions = {r[0] for r in db.execute("SELECT id FROM questions WHERE poll_id=?", (poll_id,))}
    submitted = [a.question_id for a in body.answers]
    if set(submitted) != questions or len(submitted) != len(questions):
        raise HTTPException(422, "Répondez exactement une fois à chaque question")
    for answer in body.answers:
        if not db.execute(
            "SELECT 1 FROM options WHERE id=? AND question_id=?", (answer.option_id, answer.question_id)
        ).fetchone():
            raise HTTPException(422, "Cette option n'appartient pas à cette question")
    for answer in body.answers:
        db.execute(
            "INSERT INTO answers(question_id,user_id,option_id) VALUES(?,?,?) "
            "ON CONFLICT(question_id,user_id) DO UPDATE SET option_id=excluded.option_id",
            (answer.question_id, user["id"], answer.option_id),
        )
    return {"poll_id": poll_id, "answers": [a.model_dump() for a in body.answers]}


@router.get("/polls/{poll_id}/responses/me", summary="Lire mes réponses au sondage")
def read_vote(poll_id: int, db: DB, user: User):
    access_poll(db, poll_id, user)
    return {
        "poll_id": poll_id,
        "answers": [
            dict(r)
            for r in db.execute(
                "SELECT question_id,option_id FROM answers WHERE user_id=? AND question_id IN (SELECT id FROM questions WHERE poll_id=?) ORDER BY question_id",
                (user["id"], poll_id),
            )
        ],
    }


@router.delete("/polls/{poll_id}/responses/me", status_code=204, summary="Retirer mes réponses au sondage")
def delete_vote(poll_id: int, db: DB, user: User):
    if access_poll(db, poll_id, user)["closed"]:
        raise HTTPException(409, "Le sondage est fermé")
    db.execute(
        "DELETE FROM answers WHERE user_id=? AND question_id IN (SELECT id FROM questions WHERE poll_id=?)",
        (user["id"], poll_id),
    )
    return Response(status_code=204)


@router.get("/polls/{poll_id}/results", summary="Consulter les résultats agrégés du sondage")
def results(poll_id: int, db: DB, user: User):
    """Retourne le nombre de réponses pour chaque option sans exposer l'identité des votants."""
    poll = full_poll(db, access_poll(db, poll_id, user))
    counts = {
        r[0]: r[1]
        for r in db.execute(
            "SELECT option_id,count(*) FROM answers WHERE question_id IN (SELECT id FROM questions WHERE poll_id=?) GROUP BY option_id",
            (poll_id,),
        )
    }
    for q in poll["questions"]:
        for option in q["options"]:
            option["votes"] = counts.get(option["id"], 0)
        q["total_responses"] = sum(o["votes"] for o in q["options"])
    return poll
