from fastapi.testclient import TestClient

from app.main import create_app
from scripts.export_docs import run_journey


def test_all_operations_match_their_response_contracts():
    schema, recordings = run_journey()
    assert len(recordings) == sum(len(methods) for methods in schema["paths"].values())


def test_rate_limit_and_payload_limits(tmp_path):
    with TestClient(create_app(tmp_path / "rate.db", rate_limit=True)) as client:
        for _ in range(30):
            assert client.post("/api/v1/auth/login", json={}).status_code == 422
        limited = client.post("/api/v1/auth/login", json={})
        assert limited.status_code == 429
        assert limited.headers["Retry-After"] == "60"
        assert (
            client.post("/api/v1/users", content="{}", headers={"Content-Length": "2000000"}).status_code
            == 413
        )
        assert (
            client.post("/api/v1/users", content="{}", headers={"Content-Length": "invalid"}).status_code
            == 400
        )
