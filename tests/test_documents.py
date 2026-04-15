from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── GET /documents ────────────────────────────────────────────────────────────

def test_list_documents_empty():
    with patch("app.main.list_documents", return_value=[]):
        response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["documents"] == []


def test_list_documents_returns_all():
    fake_docs = [
        {"document_id": "abc123", "chunk_count": 10},
        {"document_id": "def456", "chunk_count": 25},
    ]
    with patch("app.main.list_documents", return_value=fake_docs):
        response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["documents"][0]["document_id"] == "abc123"
    assert data["documents"][1]["chunk_count"] == 25


# ── DELETE /document/{id} ─────────────────────────────────────────────────────

def test_delete_document_success():
    with patch("app.main.delete_document", return_value=True):
        response = client.delete("/document/abc123")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True
    assert data["document_id"] == "abc123"


def test_delete_document_not_found():
    with patch("app.main.delete_document", return_value=False):
        response = client.delete("/document/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]


# ── POST /summarize ───────────────────────────────────────────────────────────

def test_summarize_success():
    fake_chunks = ["The company reported record profits.", "Revenue grew 30% year over year."]
    fake_summary = "The company had a strong financial year with record profits and 30% revenue growth."

    with (
        patch("app.main.get_all_chunks", return_value=fake_chunks),
        patch("app.main.summarize_document", return_value=fake_summary),
    ):
        response = client.post("/summarize", json={"document_id": "abc123"})

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == fake_summary
    assert data["chunks_used"] == 2
    assert data["document_id"] == "abc123"


def test_summarize_document_not_found():
    with patch("app.main.get_all_chunks", return_value=[]):
        response = client.post("/summarize", json={"document_id": "missing"})
    assert response.status_code == 404


def test_summarize_rejects_missing_document_id():
    response = client.post("/summarize", json={})
    assert response.status_code == 422


# ── POST /extract ─────────────────────────────────────────────────────────────

def test_extract_success():
    fake_chunks = ["Apple Inc. was founded by Steve Jobs in California."]
    fake_result = {
        "key_points": ["Apple was founded by Steve Jobs"],
        "entities": ["Apple Inc.", "Steve Jobs", "California"],
        "topics": ["Technology", "Business History"],
    }

    with (
        patch("app.main.get_all_chunks", return_value=fake_chunks),
        patch("app.main.extract_document_info", return_value=fake_result),
    ):
        response = client.post("/extract", json={"document_id": "abc123"})

    assert response.status_code == 200
    data = response.json()
    assert "Apple Inc." in data["entities"]
    assert "Technology" in data["topics"]
    assert len(data["key_points"]) == 1


def test_extract_document_not_found():
    with patch("app.main.get_all_chunks", return_value=[]):
        response = client.post("/extract", json={"document_id": "missing"})
    assert response.status_code == 404
