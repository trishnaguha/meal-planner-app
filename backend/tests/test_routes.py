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


def test_get_preferences_empty(client):
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.get.return_value = None
        response = client.get("/api/preferences")
        assert response.status_code == 200
        assert response.json() == {}


def test_save_preferences(client):
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.save.return_value = {"dietary_preference": "high protein"}
        response = client.post(
            "/api/preferences",
            json={"dietary_preference": "high protein"},
        )
        assert response.status_code == 200
        assert response.json()["dietary_preference"] == "high protein"
        mock_pref.save.assert_called_once_with("high protein")


def test_get_preferences_returns_saved(client):
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.get.return_value = {"dietary_preference": "protein and vegetables"}
        response = client.get("/api/preferences")
        assert response.status_code == 200
        assert response.json()["dietary_preference"] == "protein and vegetables"


def test_swap_single_meal(client):
    with patch("app.api.routes.generate_swap_suggestion") as mock_swap:
        mock_swap.return_value = {
            "suggestion": {
                "day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history",
                "ingredients": ["meat", "flour"],
            },
            "validation_status": "passed",
            "validation_warnings": [],
        }
        # Set _current_plan so the route has a plan to reference
        from app.api import routes
        routes._current_plan = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
                 "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
            ],
        }

        response = client.post(
            "/api/swap-single-meal",
            json={"day": "Monday", "meal_slot": "lunch", "current_dish": "dal rice"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["suggestion"]["dish"] == "keema paratha"
        assert data["validation_status"] == "passed"


def test_swap_single_meal_no_plan(client):
    from app.api import routes
    routes._current_plan = {}

    response = client.post(
        "/api/swap-single-meal",
        json={"day": "Monday", "meal_slot": "lunch", "current_dish": "dal rice"},
    )
    assert response.status_code == 400


def test_accept_swap(client):
    with patch("app.api.routes.apply_swap") as mock_apply:
        from app.api import routes
        routes._current_plan = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
                 "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
            ],
        }
        mock_apply.return_value = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                 "prep_time_min": 30, "reason": "from history", "ingredients": ["meat"]},
            ],
            "grocery_list": [{"name": "meat", "quantity": "1kg", "category": "protein", "used_in": ["keema paratha"]}],
            "shopping_validation_status": "passed",
        }

        response = client.post(
            "/api/accept-swap",
            json={
                "day": "Monday",
                "meal_slot": "lunch",
                "new_meal": {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                             "prep_time_min": 30, "reason": "from history", "ingredients": ["meat"]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meal_plan"][0]["dish"] == "keema paratha"
        assert len(data["grocery_list"]) > 0
