from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_all_llm_calls():
    with patch("app.agents.history_analyser.claude_service") as mock_hist, \
         patch("app.agents.meal_planner.claude_service") as mock_plan, \
         patch("app.agents.validator.claude_service") as mock_val, \
         patch("app.agents.shopping_organiser.claude_service") as mock_shop, \
         patch("app.agents.history_analyser.chroma_service") as mock_chroma_hist, \
         patch("app.agents.meal_planner.chroma_service") as mock_chroma_plan, \
         patch("app.agents.validator.chroma_service") as mock_chroma_val:

        mock_hist.call_json.return_value = [
            {"day": "Saturday", "dishes": ["keema paratha"], "quantity": 5,
             "prep_notes": "", "tags": ["indian", "protein"]}
        ]

        mock_chroma_plan.get_all_meals.return_value = [
            {"id": "m1", "document": "keema paratha", "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian"}}
        ]

        mock_plan.call_json.return_value = [
            {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha", "prep_time_min": 30,
             "reason": "from history", "ingredients": ["meat", "flour"]},
            {"day": "Monday", "meal_slot": "dinner", "dish": "Grilled chicken", "prep_time_min": 25,
             "reason": "new", "ingredients": ["chicken", "rice"]},
        ]

        mock_val.call_json.return_value = {"is_valid": True, "errors": [], "warnings": []}
        mock_chroma_val.meal_exists.return_value = True

        mock_shop.call_json.return_value = [
            {"name": "oats", "quantity": "500g", "category": "grains_pantry", "used_in": ["Oatmeal"]},
            {"name": "chicken", "quantity": "1 kg", "category": "protein", "used_in": ["Grilled chicken"]},
        ]

        yield


def test_full_flow_upload_then_generate(client, mock_all_llm_calls):
    upload_resp = client.post("/api/upload-meals", data={"text": "Saturday 5 keema paratha"})
    assert upload_resp.status_code == 200
    assert upload_resp.json()["status"] == "complete"

    gen_resp = client.post("/api/generate-plan")
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert len(data["meal_plan"]) == 2
    assert len(data["grocery_list"]) == 2
    assert data["validation_status"] == "passed"


def test_single_meal_swap_flow(client):
    """Integration test: preference save -> swap single meal -> accept swap."""
    # Save preference
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.save.return_value = {"dietary_preference": "protein and vegetables"}
        response = client.post(
            "/api/preferences",
            json={"dietary_preference": "protein and vegetables"},
        )
        assert response.status_code == 200

    # Set up a current plan
    from app.api import routes
    routes._current_plan = {
        "meal_plan": [
            {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
             "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils", "rice"]},
            {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
             "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken"]},
        ],
        "grocery_list": [],
        "validation_status": "passed",
    }

    # Swap single meal
    with patch("app.api.routes.generate_swap_suggestion") as mock_gen:
        mock_gen.return_value = {
            "suggestion": {
                "day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history",
                "ingredients": ["ground meat", "flour"],
            },
            "validation_status": "passed",
            "validation_warnings": [],
        }
        response = client.post(
            "/api/swap-single-meal",
            json={"day": "Monday", "meal_slot": "lunch", "current_dish": "dal rice"},
        )
        assert response.status_code == 200
        assert response.json()["suggestion"]["dish"] == "keema paratha"

    # Accept swap
    with patch("app.api.routes.apply_swap") as mock_apply:
        mock_apply.return_value = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                 "prep_time_min": 30, "reason": "from history", "ingredients": ["ground meat", "flour"]},
                {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
                 "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken"]},
            ],
            "grocery_list": [{"name": "ground meat", "quantity": "500g", "category": "protein", "used_in": ["keema paratha"]}],
            "shopping_validation_status": "passed",
        }
        response = client.post(
            "/api/accept-swap",
            json={
                "day": "Monday",
                "meal_slot": "lunch",
                "new_meal": {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                             "prep_time_min": 30, "reason": "from history", "ingredients": ["ground meat", "flour"]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meal_plan"][0]["dish"] == "keema paratha"
        assert data["meal_plan"][1]["dish"] == "chicken curry"
