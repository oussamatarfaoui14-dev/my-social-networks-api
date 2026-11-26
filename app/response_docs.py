"""Explicit response contracts, shared by live OpenAPI and exported documentation."""

from copy import deepcopy

from fastapi.openapi.utils import get_openapi


def obj(fields, optional=()):
    return {"type": "object", "properties": fields, "required": [k for k in fields if k not in optional]}


def shape(text):
    fields = {}
    for token in text.split():
        name, kind = token.split(":")
        types = {"i": "integer", "s": "string", "b": "boolean", "n": "null"}
        fields[name] = {"type": [types[t] for t in kind]} if len(kind) > 1 else {"type": types[kind]}
    return fields


def array(item):
    return {"type": "array", "items": item}


def paginated(item):
    return obj({"items": array(item), **shape("total:i limit:i offset:i")})


ENTITIES = {
    "users": obj(shape("id:i first_name:s last_name:s bio:s avatar_url:sn created_at:s")),
    "groups": obj(
        shape(
            "id:i name:s description:s icon:s cover_url:s visibility:s members_can_post:b members_can_create_events:b created_at:s"
        )
    ),
    "events": obj(
        shape(
            "id:i name:s description:s starts_at:s ends_at:s location:s cover_url:s visibility:s group_id:in status:s shopping_enabled:b carpool_enabled:b ticketing_enabled:b"
        )
    ),
    "threads": obj(shape("id:i title:s group_id:in event_id:in")),
    "messages": obj(shape("id:i thread_id:i author_id:i content:s created_at:s")),
    "message-comments": obj(shape("id:i message_id:i author_id:i content:s created_at:s")),
    "albums": obj(shape("id:i event_id:i author_id:i name:s description:s")),
    "photos": obj(shape("id:i album_id:i author_id:i url:s caption:s")),
    "photo-comments": obj(shape("id:i photo_id:i author_id:i content:s created_at:s")),
    "shopping-items": obj(shape("id:i event_id:i author_id:i name:s quantity:i arrival_at:s")),
    "carpools": obj(
        shape(
            "id:i event_id:i author_id:i departure_location:s departure_at:s price_cents:i available_seats:i max_detour_minutes:i"
        )
    ),
    "ticket-types": obj(
        shape("id:i event_id:i name:s amount_cents:i quantity:i sold:i remaining:i currency:s")
    ),
    "tickets": obj(
        shape(
            "id:i event_id:i ticket_type_id:i email:s first_name:s last_name:s address_line:s postal_code:s city:s country:s amount_cents:i purchased_at:s currency:s"
        )
    ),
}
OPTION = obj(shape("id:i question_id:i text:s"))
QUESTION = obj({**shape("id:i poll_id:i text:s"), "options": array(OPTION)})
POLL_BASE = shape("id:i event_id:i title:s closed:b")
ENTITIES["polls"] = obj({**POLL_BASE, "questions": array(QUESTION)})
SESSION = obj(shape("access_token:s token_type:s expires_in:i"))
PRIVATE_USER = obj({**ENTITIES["users"]["properties"], "email": {"type": "string", "format": "email"}})


def response_for(path, method):
    parts = path.strip("/").split("/")
    if method == "delete" or path in {"/api/v1/auth/logout", "/api/v1/auth/password"}:
        return None
    if path == "/health":
        return obj(shape("status:s version:s"))
    if path == "/api/v1/auth/login":
        return SESSION
    if path == "/api/v1/users" and method == "post":
        return obj({"user": PRIVATE_USER, **SESSION["properties"]})
    if path == "/api/v1/users/me":
        return PRIVATE_USER
    if path == "/api/v1/users/{user_id}":
        if method == "put":
            return PRIVATE_USER
        return obj(PRIVATE_USER["properties"], optional=("email",))
    if path.endswith("/invitations"):
        return paginated(ENTITIES["events"])
    if path.endswith("/invite-group"):
        return obj(shape("invited_count:i"))
    if path.endswith("/share"):
        return obj(shape("url:s x:s linkedin:s"))
    if "/members" in path or path.endswith("/join"):
        kind = "group" if "/groups/" in path else "event"
        fields = shape(f"id:i {kind}_id:i user_id:i role:s")
        if kind == "event":
            fields.update(shape("status:s"))
        return paginated(obj(fields)) if path.endswith("/members") else obj(fields)
    if "/responses/me" in path:
        return obj(
            {"poll_id": {"type": "integer"}, "answers": array(obj(shape("question_id:i option_id:i")))}
        )
    if path.endswith("/results"):
        option = obj({**OPTION["properties"], "votes": {"type": "integer"}})
        question = obj(
            {**QUESTION["properties"], "options": array(option), "total_responses": {"type": "integer"}}
        )
        return obj({**POLL_BASE, "questions": array(question)})
    if path.endswith("/state"):
        return obj(POLL_BASE)
    if path.endswith("/settings") or path.endswith("/publish"):
        return ENTITIES["events"]
    resource = next(part for part in reversed(parts) if part in ENTITIES)
    entity = ENTITIES[resource]
    if resource == "tickets" and method == "post":
        return obj({**entity["properties"], "receipt_token": {"type": "string"}})
    return paginated(entity) if method == "get" and parts[-1] == resource else entity


def install(app):
    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes
        )
        schema["components"]["securitySchemes"]["TicketReceipt"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-Ticket-Token",
            "description": "Secret personnel remis une fois à l'achat du billet.",
        }
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                response = response_for(path, method)
                code = "201" if "201" in operation["responses"] else "200"
                if response:
                    operation["responses"][code]["content"] = {
                        "application/json": {"schema": deepcopy(response)}
                    }
                if (
                    path in {"/health", "/api/v1/auth/login"}
                    or (path == "/api/v1/users" and method == "post")
                    or (path.endswith("/tickets") and method == "post")
                ):
                    operation["security"] = []
                elif path.startswith("/api/v1/tickets/"):
                    operation["security"] = [{"HTTPBearer": []}, {"TicketReceipt": []}]
                elif method == "get" and (
                    path
                    in {
                        "/api/v1/events",
                        "/api/v1/groups",
                        "/api/v1/events/{event_id}",
                        "/api/v1/groups/{group_id}",
                    }
                    or "ticket-types" in path
                ):
                    operation["security"] = [{}, {"HTTPBearer": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
