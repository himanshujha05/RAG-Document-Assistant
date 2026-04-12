from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ask_returns_answer():
    fake_chunks = ["The capital of France is Paris."]
    fake_answer = "The capital of France is Paris."

    with (
        patch("app.main.query_chunks", return_value=fake_chunks),
        patch("app.main.ask_llm", return_value=fake_answer),
    ):
        response = client.post(
            "/ask",
            json={"question": "What is the capital of France?", "document_id": "abc123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == fake_answer
    assert data["source_chunks"] == fake_chunks
    assert data["document_id"] == "abc123"


def test_ask_returns_404_when_no_chunks():
    with patch("app.main.query_chunks", return_value=[]):
        response = client.post(
            "/ask",
            json={"question": "What is this about?", "document_id": "nonexistent"},
        )

    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]


def test_ask_rejects_empty_question():
    response = client.post(
        "/ask",
        json={"question": "", "document_id": "abc123"},
    )
    assert response.status_code == 422


def test_ask_rejects_missing_document_id():
    response = client.post(
        "/ask",
        json={"question": "What is this?"},
    )
    assert response.status_code == 422
