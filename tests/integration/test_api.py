from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.api import routes_health, routes_ingestion
from app.main import app
from app.services import account_service, qa_service, retrieval_service
from app.services.ingestion_service import prepare_document

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_local_sample_indexes(monkeypatch):
    monkeypatch.setattr(routes_health, "vector_store_ready", lambda: True)
    monkeypatch.setattr(routes_health, "keyword_index_ready", lambda: True)
    monkeypatch.setattr(
        qa_service,
        "search_detailed",
        lambda question, mode: retrieval_service.search_detailed(
            question, mode, retrieval_service.load_documents()
        ),
    )


def test_health_readiness_and_request_id():
    health = client.get("/health")
    assert health.status_code == 200 and health.json()["status"] == "ok"
    assert health.headers["x-request-id"]
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["vector_database"] == "qdrant"


def test_supported_and_unsupported_question_flow():
    supported = client.post("/api/v1/ask", json={"question": "What does hydration mean?"})
    assert supported.status_code == 200
    payload = supported.json()
    assert payload["citations"][0]["source_id"] == "hydration-001"
    assert payload["disclaimer"]
    unsupported = client.post(
        "/api/v1/ask", json={"question": "Explain quantum engine maintenance"}
    ).json()
    assert unsupported["safety"]["abstained"] is True


def test_common_sleep_typo_still_retrieves_sleep_evidence():
    response = client.post("/api/v1/ask", json={"question": "I am not getting slepp properly"})
    assert response.status_code == 200
    assert response.json()["citations"][0]["source_id"] == "sleep-001"


def test_input_validation_and_emergency_response():
    assert client.post("/api/v1/ask", json={"question": ""}).status_code == 422
    assert (
        client.post("/api/v1/ask", json={"question": "I have chest pain"}).json()["safety"][
            "emergency"
        ]
        is True
    )


def test_validation_response_does_not_echo_submitted_value():
    marker = "do-not-reflect-this-value"
    response = client.post("/api/v1/ask", json={"question": marker, "unexpected": marker})
    assert response.status_code == 422
    assert marker not in response.text


def test_account_api_opt_in_history_and_logout(monkeypatch):
    database_path = Path("data/local") / f"account-api-{uuid4().hex}.sqlite3"
    monkeypatch.setattr(
        account_service,
        "settings",
        replace(
            account_service.settings,
            database_path=str(database_path),
            database_url="",
            data_encryption_key=Fernet.generate_key().decode("ascii"),
        ),
    )
    try:
        account_service.initialize_account_store()
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": f"{uuid4().hex}@example.org", "password": "long test password 123"},
        )
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert client.get("/api/v1/auth/me").status_code == 200

        enabled = client.patch("/api/v1/auth/history", json={"enabled": True})
        assert enabled.status_code == 200 and enabled.json()["history_enabled"] is True
        assert client.get("/api/v1/auth/history").json()["conversations"] == []
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401
    finally:
        database_path.unlink(missing_ok=True)


def test_ingest_mock_without_key_is_dry_local_capability(monkeypatch):
    monkeypatch.setattr(
        routes_ingestion,
        "settings",
        replace(routes_ingestion.settings, ingestion_api_key=""),
    )
    path = Path("data/local") / f"test-{uuid4().hex}.jsonl"
    monkeypatch.setattr(routes_ingestion, "LOCAL_STORE_PATH", path)
    monkeypatch.setattr(retrieval_service, "LOCAL_STORE_PATH", path)
    document = {
        "document_id": "test-edu",
        "title": "Synthetic test",
        "source": "Synthetic educational fixture",
        "content": "A synthetic classroom example describes hand hygiene after outdoor gardening.",
    }
    expected_id = prepare_document(document)[0]["chunk_id"]
    try:
        response = client.post(
            "/api/v1/documents/ingest",
            json=document,
        )
        assert response.status_code == 200
        assert response.json()["chunks_added"] >= 1
        answer = client.post(
            "/api/v1/ask",
            json={
                "question": "What does the gardening hygiene example mention?",
                "retrieval_mode": "bm25",
            },
        )
        assert answer.status_code == 200
        assert answer.json()["citations"][0]["source_id"] == expected_id
    finally:
        path.unlink(missing_ok=True)


def test_ingestion_requires_configured_key_and_persists_for_retrieval(monkeypatch):
    configured_key = uuid4().hex
    incorrect_key = uuid4().hex
    monkeypatch.setattr(
        routes_ingestion,
        "settings",
        replace(routes_ingestion.settings, ingestion_api_key=configured_key),
    )
    path = Path("data/local") / f"test-{uuid4().hex}.jsonl"
    monkeypatch.setattr(routes_ingestion, "LOCAL_STORE_PATH", path)
    payload = {
        "document_id": "fixture-ingested",
        "title": "Synthetic sleep note",
        "content": "Synthetic educational information about sleep routines.",
    }
    try:
        assert client.post("/api/v1/documents/ingest", json=payload).status_code == 401
        assert (
            client.post(
                "/api/v1/documents/ingest",
                json=payload,
                headers={"X-API-Key": incorrect_key},
            ).status_code
            == 401
        )
        written = client.post(
            "/api/v1/documents/ingest", json=payload, headers={"X-API-Key": configured_key}
        )
        assert written.status_code == 200
        assert written.json()["chunks_added"] == 1
        assert path.exists()
    finally:
        path.unlink(missing_ok=True)
