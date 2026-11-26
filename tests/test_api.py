from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from conftest import PASSWORD, buyer, call, enable, event, group

from app.db import connect


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok", "version": "2.0.0"}
    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == "2.0.0"
    assert len(schema["paths"]) >= 45
    assert client.get("/docs").status_code == 200


def test_user_cruds_authentication_privacy(client, actors):
    a, b, _ = actors
    call(client, "GET", "/users", expected=401)
    rows = call(client, "GET", "/users?q=Alice&limit=1", a)
    assert rows["total"] == 1 and "email" not in rows["items"][0]
    assert "email" not in call(client, "GET", f"/users/{b['id']}", a)
    assert call(client, "GET", "/users/me", a)["email"] == "alice@example.com"
    body = {"email": "ALICE@example.com", "first_name": "Alice", "last_name": "Exemple", "password": PASSWORD}
    call(client, "POST", "/users", expected=409, json=body)
    call(
        client,
        "POST",
        "/auth/login",
        expected=401,
        json={"email": "alice@example.com", "password": "incorrect"},
    )
    call(
        client,
        "POST",
        "/auth/login",
        expected=401,
        json={"email": "missing@example.com", "password": "incorrect"},
    )
    call(client, "POST", "/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    body.pop("password")
    body["first_name"] = "Alicia"
    call(client, "PUT", f"/users/{a['id']}", b, 403, json=body)
    call(client, "PUT", f"/users/{a['id']}", a, json=body)
    call(client, "DELETE", f"/users/{a['id']}", b, 403)
    call(
        client,
        "PUT",
        "/auth/password",
        a,
        403,
        json={"current_password": "incorrect", "new_password": PASSWORD},
    )
    call(
        client,
        "PUT",
        "/auth/password",
        a,
        204,
        json={"current_password": PASSWORD, "new_password": "New-Password-2026!"},
    )
    call(client, "GET", "/users/me", a, 401)
    call(client, "POST", "/auth/logout", b, 204)
    call(client, "GET", "/users/me", b, 401)


def test_delete_account_and_expired_session(client, actors):
    a, b, _ = actors
    call(client, "DELETE", f"/users/{a['id']}", a, 204)
    call(client, "GET", "/users/me", a, 401)
    with connect(client.app.state.database_path) as db:
        db.execute("UPDATE sessions SET expires_at=0 WHERE user_id=?", (b["id"],))
    call(client, "GET", "/users/me", b, 401)
    call(client, "GET", "/users/me", expected=401, headers={"Authorization": "Bearer forged-token"})


@pytest.mark.parametrize("visibility", ["public", "private", "secret"])
def test_group_visibility_and_membership(client, actors, visibility):
    a, b, c = actors
    g = group(client, a, visibility=visibility, member_ids=[b["id"]])
    gid = g["id"]
    call(client, "GET", f"/groups/{gid}", c, 200 if visibility == "public" else 404)
    assert call(client, "GET", "/groups", c)["total"] == (visibility == "public")
    call(client, "GET", f"/groups/{gid}", b)
    call(client, "GET", f"/groups/{gid}/members", b)
    call(client, "PUT", f"/groups/{gid}/members/{c['id']}", b, 403, json={"role": "admin"})
    call(client, "POST", f"/groups/{gid}/join", c, 200 if visibility == "public" else 404)
    call(client, "POST", f"/groups/{gid}/join", b)
    call(client, "PUT", f"/groups/{gid}/members/{c['id']}", a, json={"role": "admin"})
    call(client, "PUT", f"/groups/{gid}/members/{a['id']}", c, json={"role": "member"})
    call(client, "DELETE", f"/groups/{gid}/members/{a['id']}", a, 204)
    call(client, "DELETE", f"/groups/{gid}/members/{c['id']}", c, 409)
    call(client, "DELETE", f"/groups/{gid}/members/9999", c, 404)
    body = {k: g[k] for k in ["name", "description", "icon", "cover_url", "visibility"]}
    call(client, "PUT", f"/groups/{gid}", c, json={**body, "name": "Nouveau nom"})
    call(client, "DELETE", f"/groups/{gid}", b, 403)
    call(client, "DELETE", f"/groups/{gid}", c, 204)


@pytest.mark.parametrize("kind", ["group", "event"])
def test_last_manager_invariant(client, actors, kind):
    a, b, _ = actors
    resource = group(client, a) if kind == "group" else event(client, a)
    path = f"/{kind}s/{resource['id']}/members/{a['id']}"
    call(client, "DELETE", path, a, 409)
    call(client, "PUT", path, a, 409, json={"role": "member" if kind == "group" else "participant"})
    call(client, "DELETE", f"/users/{a['id']}", a, 409)
    call(
        client,
        "PUT",
        f"/{kind}s/{resource['id']}/members/{b['id']}",
        a,
        json={"role": "admin" if kind == "group" else "organizer"},
    )
    call(client, "DELETE", f"/users/{a['id']}", a, 204)


def test_three_steps_private_invitation_and_search(client, actors):
    a, b, c = actors
    e = event(client, a, publish=False, visibility="private", participant_ids=[b["id"]])
    eid = e["id"]
    call(client, "GET", f"/events/{eid}", b, 404)
    assert call(client, "GET", "/events", b)["total"] == 0
    assert call(client, "GET", "/events?q=annuelle", a)["total"] == 1
    call(client, "POST", f"/events/{eid}/join", a, 409)
    enable(client, a, eid, ticketing_enabled=False)
    call(client, "POST", f"/events/{eid}/publish", a)
    call(client, "GET", f"/events/{eid}", b)
    call(client, "GET", f"/events/{eid}", c, 404)
    assert call(client, "GET", "/me/invitations", b)["total"] == 1
    call(client, "GET", f"/events/{eid}/members", b, 403)
    call(client, "POST", f"/events/{eid}/join", b)
    call(client, "GET", f"/events/{eid}/members", b)
    assert call(client, "GET", "/me/invitations", b)["total"] == 0
    body = {
        k: e[k]
        for k in ["name", "description", "starts_at", "ends_at", "location", "cover_url", "visibility"]
    }
    call(client, "PUT", f"/events/{eid}", b, 403, json=body)
    call(client, "PUT", f"/events/{eid}", a, json={**body, "name": "Événement modifié"})
    call(client, "PUT", f"/events/{eid}/members/{c['id']}", a, json={"role": "participant"})
    call(client, "DELETE", f"/events/{eid}/members/{c['id']}", c, 204)
    call(client, "DELETE", f"/events/{eid}/members/9999", a, 404)
    call(client, "DELETE", f"/events/{eid}/members/{b['id']}", b, 204)
    call(client, "DELETE", f"/events/{eid}", a, 204)


def test_group_events_permissions_bulk_invite_and_share(client, actors):
    a, b, c = actors
    g = group(client, a, member_ids=[b["id"]], members_can_create_events=False)
    gid = g["id"]
    base = {
        "name": "E",
        "description": "Desc",
        "starts_at": "2030-01-01T10:00:00Z",
        "ends_at": "2030-01-01T11:00:00Z",
        "location": "Paris",
        "cover_url": "https://example.com/a.jpg",
        "visibility": "public",
        "group_id": gid,
    }
    call(client, "POST", "/events", b, 403, json=base)
    e = event(client, a, group_id=gid, invite_all_group_members=True)
    assert call(client, "POST", f"/events/{e['id']}/invite-group", a)["invited_count"] == 0
    call(client, "PUT", f"/groups/{gid}/members/{c['id']}", a, json={"role": "member"})
    assert call(client, "POST", f"/events/{e['id']}/invite-group", a)["invited_count"] == 1
    assert "linkedin" in call(client, "GET", f"/events/{e['id']}/share", a)
    assert call(client, "GET", f"/events?group_id={gid}", a)["total"] == 1
    gbody = {k: g[k] for k in ["name", "description", "icon", "cover_url", "visibility"]}
    call(client, "PUT", f"/groups/{gid}", a, 409, json={**gbody, "visibility": "secret"})
    call(client, "DELETE", f"/events/{e['id']}", a, 204)
    call(client, "PUT", f"/groups/{gid}", a, json={**gbody, "visibility": "secret"})
    call(client, "POST", "/events", a, 422, json=base)
    private = event(client, a, group_id=gid, visibility="private")
    call(client, "GET", f"/events/{private['id']}/share", a, 409)
    call(client, "DELETE", f"/groups/{gid}", a, 204)
    call(client, "GET", f"/events/{private['id']}", a, 404)


@pytest.mark.parametrize(
    "override",
    [
        {"ends_at": "2020-01-01T00:00:00Z"},
        {"starts_at": "2030-06-15T10:00:00"},
        {"visibility": "secret"},
        {"cover_url": "javascript:alert(1)"},
        {"name": " "},
        {"organizer_ids": [9999]},
        {"invite_all_group_members": True},
        {"unknown": True},
    ],
)
def test_event_validation(client, actors, override):
    body = {
        "name": "E",
        "description": "D",
        "starts_at": "2030-06-15T10:00:00Z",
        "ends_at": "2030-06-15T20:00:00Z",
        "location": "Paris",
        "cover_url": "https://example.com/a.jpg",
        "visibility": "public",
        **override,
    }
    call(client, "POST", "/events", actors[0], 404 if "organizer_ids" in override else 422, json=body)
    assert call(client, "GET", "/events", actors[0])["total"] == 0


def test_thread_exclusivity_and_group_publication_rights(client, actors):
    a, b, c = actors
    g = group(client, a, member_ids=[b["id"]], members_can_post=False)
    eid = event(client, a)["id"]
    for body in [{"title": "X"}, {"title": "X", "group_id": g["id"], "event_id": eid}]:
        call(client, "POST", "/threads", a, 422, json=body)
    call(client, "GET", "/threads", a, 422)
    thread = call(client, "GET", f"/threads?group_id={g['id']}", a)["items"][0]
    tid = thread["id"]
    call(client, "GET", f"/threads/{tid}", c, 403)
    call(client, "POST", f"/threads/{tid}/messages", b, 403, json={"content": "Bonjour"})
    call(client, "DELETE", f"/threads/{tid}", a, 409)
    extra = call(client, "POST", "/threads", a, 201, json={"title": "Autre", "group_id": g["id"]})
    call(client, "PUT", f"/threads/{extra['id']}", a, json={"title": "Renommé"})
    call(client, "GET", f"/threads/{extra['id']}", a)
    call(client, "DELETE", f"/threads/{extra['id']}", a, 204)


@pytest.mark.parametrize(
    "resource",
    ["messages", "message-comments", "albums", "photos", "photo-comments", "shopping-items", "carpools"],
)
def test_content_cruds_and_ownership(client, actors, resource):
    a, b, c = actors
    eid = event(client, a)["id"]
    enable(client, a, eid)
    call(client, "POST", f"/events/{eid}/join", b)
    tid = call(client, "GET", f"/threads?event_id={eid}", a)["items"][0]["id"]
    mid = call(client, "POST", f"/threads/{tid}/messages", a, 201, json={"content": "Message initial"})["id"]
    aid = call(client, "POST", f"/events/{eid}/albums", a, 201, json={"name": "Souvenirs"})["id"]
    pid = call(
        client, "POST", f"/albums/{aid}/photos", a, 201, json={"url": "https://example.com/photo.jpg"}
    )["id"]
    configs = {
        "messages": (f"/threads/{tid}/messages", {"content": "Bonjour tout le monde"}),
        "message-comments": (f"/messages/{mid}/message-comments", {"content": "Commentaire"}),
        "albums": (f"/events/{eid}/albums", {"name": "Album test", "description": "Souvenirs"}),
        "photos": (f"/albums/{aid}/photos", {"url": "https://example.com/image.jpg", "caption": "Portrait"}),
        "photo-comments": (f"/photos/{pid}/photo-comments", {"content": "Belle photo"}),
        "shopping-items": (
            f"/events/{eid}/shopping-items",
            {"name": "Jus de fruits", "quantity": 3, "arrival_at": "2030-06-15T11:00:00Z"},
        ),
        "carpools": (
            f"/events/{eid}/carpools",
            {
                "departure_location": "Lyon",
                "departure_at": "2030-06-15T07:00:00Z",
                "price_cents": 1200,
                "available_seats": 3,
                "max_detour_minutes": 30,
            },
        ),
    }
    url, body = configs[resource]
    call(client, "POST", url, c, 403, json=body)
    row = call(client, "POST", url, b, 201, json=body)
    assert row["author_id"] == b["id"]
    detail = f"/{resource}/{row['id']}"
    call(client, "GET", url, b)
    call(client, "GET", detail, b)
    call(client, "GET", detail, c, 403)
    call(client, "POST", f"/events/{eid}/join", c)
    call(client, "PUT", detail, c, 403, json=body)
    call(client, "DELETE", detail, c, 403)
    call(client, "PUT", detail, b, json=body)
    call(client, "PUT", detail, a, json=body)
    assert call(client, "GET", url + "?q=nonexistent", b)["total"] == 0
    call(client, "DELETE", detail, a, 204)
    call(client, "GET", detail, b, 404)


def test_shopping_and_carpool_settings_uniqueness_and_dates(client, actors):
    a, b, _ = actors
    e = event(client, a)
    eid = e["id"]
    shopping = {"name": "Eau minérale", "quantity": 3, "arrival_at": "2030-06-15T11:00:00Z"}
    carpool = {
        "departure_location": "Lyon",
        "departure_at": "2030-06-15T07:00:00Z",
        "price_cents": 0,
        "available_seats": 1,
        "max_detour_minutes": 30,
    }
    call(client, "POST", f"/events/{eid}/shopping-items", a, 409, json=shopping)
    call(client, "POST", f"/events/{eid}/carpools", a, 409, json=carpool)
    enable(client, a, eid)
    item = call(client, "POST", f"/events/{eid}/shopping-items", a, 201, json=shopping)
    call(
        client,
        "POST",
        f"/events/{eid}/shopping-items",
        a,
        409,
        json={**shopping, "name": "  EAU   MINÉRALE  "},
    )
    call(
        client,
        "POST",
        f"/events/{eid}/shopping-items",
        a,
        422,
        json={**shopping, "name": "Autre", "quantity": 0},
    )
    call(
        client,
        "POST",
        f"/events/{eid}/shopping-items",
        a,
        422,
        json={**shopping, "arrival_at": "2031-06-15T11:00:00Z"},
    )
    call(
        client,
        "POST",
        f"/events/{eid}/carpools",
        a,
        422,
        json={**carpool, "departure_at": "2031-06-15T11:00:00Z"},
    )
    call(client, "POST", f"/events/{eid}/carpools", a, 422, json={**carpool, "price_cents": -1})
    call(client, "POST", f"/events/{eid}/carpools", a, 201, json=carpool)
    body = {
        k: e[k]
        for k in ["name", "description", "starts_at", "ends_at", "location", "cover_url", "visibility"]
    }
    call(client, "PUT", f"/events/{eid}", a, 409, json={**body, "starts_at": "2030-06-15T12:00:00Z"})
    call(client, "DELETE", f"/shopping-items/{item['id']}", a, 204)
    call(
        client,
        "PUT",
        f"/events/{eid}",
        a,
        409,
        json={**body, "starts_at": "2030-06-14T00:00:00Z", "ends_at": "2030-06-14T20:00:00Z"},
    )


def test_poll_complete_lifecycle_and_invalid_votes(client, actors):
    a, b, c = actors
    eid = event(client, a, participant_ids=[b["id"]])["id"]
    body = {
        "title": "Organisation",
        "questions": [
            {"text": "Menu ?", "options": ["Végétarien", "Classique"]},
            {"text": "Horaire ?", "options": ["10h", "11h"]},
        ],
    }
    call(client, "POST", f"/events/{eid}/polls", b, 403, json=body)
    poll = call(client, "POST", f"/events/{eid}/polls", a, 201, json=body)
    pid = poll["id"]
    call(client, "GET", f"/events/{eid}/polls", b, 403)
    call(client, "POST", f"/events/{eid}/join", b)
    assert call(client, "GET", f"/events/{eid}/polls?q=Organisation", b)["total"] == 1
    call(client, "GET", f"/polls/{pid}", b)
    poll = call(client, "PUT", f"/polls/{pid}", a, json=body)
    q1, q2 = poll["questions"]
    answers = [{"question_id": q["id"], "option_id": q["options"][0]["id"]} for q in poll["questions"]]
    for invalid in [
        answers[:1],
        [answers[0], answers[0]],
        [{**answers[0], "option_id": q2["options"][0]["id"]}, answers[1]],
    ]:
        call(client, "PUT", f"/polls/{pid}/responses/me", b, 422, json={"answers": invalid})
    call(client, "PUT", f"/polls/{pid}/responses/me", c, 403, json={"answers": answers})
    call(client, "PUT", f"/polls/{pid}/responses/me", b, json={"answers": answers})
    call(client, "PUT", f"/polls/{pid}/responses/me", b, json={"answers": answers})
    assert len(call(client, "GET", f"/polls/{pid}/responses/me", b)["answers"]) == 2
    assert call(client, "GET", f"/polls/{pid}/results", b)["questions"][0]["total_responses"] == 1
    call(client, "PUT", f"/polls/{pid}", a, 409, json=body)
    call(client, "PATCH", f"/polls/{pid}/state", a, json={"closed": True})
    call(client, "PUT", f"/polls/{pid}/responses/me", b, 409, json={"answers": answers})
    call(client, "DELETE", f"/polls/{pid}/responses/me", b, 409)
    call(client, "PATCH", f"/polls/{pid}/state", a, json={"closed": False})
    call(client, "DELETE", f"/polls/{pid}/responses/me", b, 204)
    call(client, "DELETE", f"/polls/{pid}", b, 403)
    call(client, "DELETE", f"/polls/{pid}", a, 204)


@pytest.mark.parametrize(
    "questions", [[], [{"text": "Q", "options": ["A"]}], [{"text": "Q", "options": ["A", "a"]}]]
)
def test_invalid_poll_questions(client, actors, questions):
    eid = event(client, actors[0])["id"]
    call(
        client,
        "POST",
        f"/events/{eid}/polls",
        actors[0],
        422,
        json={"title": "Sondage", "questions": questions},
    )


def setup_tickets(client, actor, quantity=5):
    eid = event(client, actor)["id"]
    enable(client, actor, eid)
    ticket_type = call(
        client,
        "POST",
        f"/events/{eid}/ticket-types",
        actor,
        201,
        json={"name": "Standard", "amount_cents": 1500, "quantity": quantity},
    )
    return eid, ticket_type


def test_ticket_full_lifecycle_price_snapshot_and_personal_data(client, actors):
    a, b, _ = actors
    eid, t = setup_tickets(client, a)
    tid = t["id"]
    assert call(client, "GET", f"/events/{eid}/ticket-types")["items"][0]["remaining"] == 5
    call(client, "GET", f"/ticket-types/{tid}")
    ticket = call(
        client, "POST", f"/events/{eid}/tickets", expected=201, json={**buyer(), "ticket_type_id": tid}
    )
    url = f"/tickets/{ticket['id']}"
    secret = {"X-Ticket-Token": ticket["receipt_token"]}
    call(client, "GET", url, expected=404)
    call(client, "GET", url, b, 404)
    call(client, "GET", url, expected=404, headers={"X-Ticket-Token": "wrong"})
    assert "receipt_hash" not in call(client, "GET", url, headers=secret)
    assert "receipt_token" not in call(client, "GET", url, a)
    call(client, "GET", f"/events/{eid}/tickets", b, 403)
    assert call(client, "GET", f"/events/{eid}/tickets?q=buyer1", a)["total"] == 1
    call(
        client,
        "PUT",
        f"/ticket-types/{tid}",
        a,
        json={"name": "Standard", "amount_cents": 2500, "quantity": 5},
    )
    assert call(client, "GET", url, a)["amount_cents"] == 1500
    call(client, "PUT", url, json={**buyer(), "city": "Lyon"}, headers=secret)
    call(client, "DELETE", f"/ticket-types/{tid}", a, 409)
    call(client, "PUT", f"/events/{eid}/settings", a, 409, json={"ticketing_enabled": False})
    call(client, "DELETE", url, expected=204, headers=secret)
    assert call(client, "GET", f"/ticket-types/{tid}")["remaining"] == 5
    call(client, "DELETE", f"/ticket-types/{tid}", a, 204)


def test_one_ticket_per_person_per_event_across_types(client, actors):
    a = actors[0]
    eid, t = setup_tickets(client, a)
    t2 = call(
        client,
        "POST",
        f"/events/{eid}/ticket-types",
        a,
        201,
        json={"name": "VIP", "amount_cents": 3000, "quantity": 5},
    )
    call(client, "POST", f"/events/{eid}/tickets", expected=201, json={**buyer(), "ticket_type_id": t["id"]})
    call(
        client,
        "POST",
        f"/events/{eid}/tickets",
        expected=409,
        json={**buyer(email="BUYER1@example.com"), "ticket_type_id": t2["id"]},
    )
    call(
        client,
        "POST",
        f"/events/{eid}/tickets",
        expected=409,
        json={**buyer(email="different@example.com"), "ticket_type_id": t2["id"]},
    )
    other, _ = setup_tickets(client, a)
    call(
        client, "POST", f"/events/{other}/tickets", expected=422, json={**buyer(), "ticket_type_id": t["id"]}
    )
    assert call(client, "GET", f"/ticket-types/{t2['id']}")["sold"] == 0


def test_concurrent_last_ticket_never_oversells(client, actors):
    eid, ticket_type = setup_tickets(client, actors[0], quantity=1)

    def buy(n):
        return client.post(
            f"/api/v1/events/{eid}/tickets", json={**buyer(n), "ticket_type_id": ticket_type["id"]}
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(buy, range(10, 18)))
    assert statuses.count(201) == 1
    assert statuses.count(409) == 7
    assert call(client, "GET", f"/ticket-types/{ticket_type['id']}")["remaining"] == 0


def test_ticket_visibility_and_inventory_guards(client, actors):
    a, b, _ = actors
    private = event(client, a, visibility="private")
    call(client, "PUT", f"/events/{private['id']}/settings", a, 422, json={"ticketing_enabled": True})
    call(client, "GET", f"/events/{private['id']}/ticket-types", a, 409)
    eid, t = setup_tickets(client, a, 2)
    for n in (1, 2):
        call(
            client,
            "POST",
            f"/events/{eid}/tickets",
            expected=201,
            json={**buyer(n), "ticket_type_id": t["id"]},
        )
    call(
        client,
        "PUT",
        f"/ticket-types/{t['id']}",
        a,
        409,
        json={"name": "Standard", "amount_cents": 1500, "quantity": 1},
    )
    e = call(client, "GET", f"/events/{eid}")
    body = {
        k: e[k]
        for k in ["name", "description", "starts_at", "ends_at", "location", "cover_url", "visibility"]
    }
    call(client, "PUT", f"/events/{eid}", a, 409, json={**body, "visibility": "private"})
    call(client, "DELETE", f"/events/{eid}", a, 204)
    with connect(client.app.state.database_path) as db:
        assert db.execute("SELECT count(*) FROM tickets").fetchone()[0] == 0


def test_normalizes_timezone_and_subsecond_dates(client, actors):
    e = event(client, actors[0], starts_at="2030-06-15T12:00:00+02:00", ends_at="2030-06-15T10:00:00.100Z")
    assert e["starts_at"] == "2030-06-15T10:00:00.000000Z"
    assert datetime.fromisoformat(e["ends_at"]) > datetime.fromisoformat(e["starts_at"])


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_pagination_validation(client, actors, query):
    call(client, "GET", "/users?" + query, actors[0], 422)


def test_sql_injection_is_data_and_validation_does_not_echo_password(client, actors):
    assert call(client, "GET", "/users?q=' OR 1=1 --", actors[0])["total"] == 0
    response = client.post(
        "/api/v1/users", json={"email": "bad", "password": "secret", "first_name": "A", "last_name": "B"}
    )
    assert response.status_code == 422 and "secret" not in response.text
    with connect(client.app.state.database_path) as db:
        rows = db.execute("SELECT password_hash FROM users").fetchall()
        assert all(row[0].startswith("$argon2id$") for row in rows)
        assert all(PASSWORD not in row[0] for row in rows)
