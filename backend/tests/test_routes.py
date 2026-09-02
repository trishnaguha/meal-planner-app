from unittest.mock import patch, MagicMock, AsyncMock
import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_graph():
    with patch("app.api.routes.meal_graph") as mock:
        mock.invoke.return_value = {
            "parsed_meals": [
                {"day": "Saturday", "dishes": ["keema paratha"], "quantity": 5,
                 "prep_notes": "", "tags": ["indian"], "original_text": "Saturday 5 keema paratha"}
            ],
            "embedding_status": "complete",
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                 "prep_time_min": 30, "reason": "past favorite", "ingredients": ["meat", "flour"]}
            ],
            "grocery_list": [
                {"name": "ground meat", "quantity": "1 kg", "category": "protein",
                 "used_in": ["keema paratha"]}
            ],
            "validation_status": "passed",
            "validation_errors": [],
            "validation_warnings": [],
            "shopping_validation_status": "passed",
            "shopping_validation_errors": [],
        }
        yield mock


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_meals_text(client, mock_graph):
    response = client.post(
        "/api/upload-meals",
        data={"text": "Saturday 5 keema paratha"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["meals_indexed"] > 0


def test_upload_meals_file(client, mock_graph):
    file_content = b"Saturday 5 keema paratha. Make cabbage"
    response = client.post(
        "/api/upload-meals",
        files={"file": ("meals.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"


def test_generate_plan(client, mock_graph):
    response = client.post("/api/generate-plan")
    assert response.status_code == 200
    data = response.json()
    assert "meal_plan" in data
    assert "grocery_list" in data
    assert "validation_status" in data


def test_swap_meal(client, mock_graph):
    response = client.post(
        "/api/swap-meal",
        json={"excluded_dishes": ["keema paratha"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "meal_plan" in data


def test_get_meal_history(client):
    with patch("app.api.routes.chroma_service") as mock_chroma:
        mock_chroma.get_all_meals.return_value = [
            {"id": "meal_1", "document": "keema paratha", "metadata": {"dish": "keema paratha"}}
        ]
        response = client.get("/api/meal-history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["meals"]) == 1
