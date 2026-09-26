from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import routes_ingestion
from app.main import app
from app.services import retrieval_service
from app.services.ingestion_service import prepare_document

client = TestClient(app)


def test_health_readiness_and_request_id():
    health = client.get("/health")
    assert health.status_code == 200 and health.json()["status"] == "ok"
    assert health.headers["x-request-id"]
    assert client.get("/ready").json()["local_documents"] >= 3


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
