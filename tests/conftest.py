import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PASSWORD = "Example-Password-2026!"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db", rate_limit=False)) as c:
        yield c


@pytest.fixture
def actors(client):
    result = []
    for name in ("Alice", "Bob", "Claire"):
        response = client.post(
            "/api/v1/users",
            json={
                "email": f"{name.lower()}@example.com",
                "password": PASSWORD,
                "first_name": name,
                "last_name": "Exemple",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        result.append(
            {"id": data["user"]["id"], "headers": {"Authorization": f"Bearer {data['access_token']}"}}
        )
    return result


def call(client, method, path, actor=None, expected=200, **kwargs):
    if actor:
        kwargs["headers"] = {**actor["headers"], **kwargs.get("headers", {})}
    response = client.request(method, "/api/v1" + path, **kwargs)
    assert response.status_code == expected, f"{method} {path}: {response.status_code} {response.text}"
    return response.json() if response.content else None


def group(client, actor, **overrides):
    body = {
        "name": "Communauté",
        "description": "Un groupe de démonstration",
        "icon": "calendar",
        "cover_url": "https://example.com/group.jpg",
        "visibility": "public",
        **overrides,
    }
    return call(client, "POST", "/groups", actor, 201, json=body)


def event(client, actor, publish=True, **overrides):
    body = {
        "name": "Rencontre annuelle",
        "description": "Programme et informations pratiques",
        "starts_at": "2030-06-15T10:00:00Z",
        "ends_at": "2030-06-15T20:00:00Z",
        "location": "10 rue Exemple, Paris",
        "cover_url": "https://example.com/cover.jpg",
        "visibility": "public",
        **overrides,
    }
    result = call(client, "POST", "/events", actor, 201, json=body)
    if publish:
        result = call(client, "POST", f"/events/{result['id']}/publish", actor)
    return result


def enable(client, actor, event_id, **overrides):
    return call(
        client,
        "PUT",
        f"/events/{event_id}/settings",
        actor,
        json={"shopping_enabled": True, "carpool_enabled": True, "ticketing_enabled": True, **overrides},
    )


def buyer(n=1, **overrides):
    return {
        "email": f"buyer{n}@example.com",
        "first_name": f"Visiteur{n}",
        "last_name": "Exemple",
        "address_line": f"{n} rue Démonstration",
        "postal_code": "75001",
        "city": "Paris",
        "country": "FR",
        **overrides,
    }
