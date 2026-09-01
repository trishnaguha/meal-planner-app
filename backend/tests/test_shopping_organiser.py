from unittest.mock import patch

import pytest

from app.agents.shopping_organiser import shopping_organiser_node


@pytest.fixture
def sample_state():
    return {
        "meal_plan": [
            {
                "day": "Monday",
                "meal_slot": "lunch",
                "dish": "keema paratha",
                "prep_time_min": 30,
                "reason": "past favorite",
                "ingredients": ["ground meat", "flour", "onion"],
            },
            {
                "day": "Tuesday",
                "meal_slot": "dinner",
                "dish": "dal rice",
                "prep_time_min": 25,
                "reason": "past favorite",
                "ingredients": ["lentils", "rice", "onion"],
            },
        ],
    }


@pytest.fixture
def mock_claude():
    with patch("app.agents.shopping_organiser.claude_service") as mock:
        mock.call_json.return_value = [
            {"name": "ground meat", "quantity": "1 kg", "category": "protein",
             "used_in": ["keema paratha"]},
            {"name": "onions", "quantity": "1 kg", "category": "produce",
             "used_in": ["keema paratha", "dal rice"]},
            {"name": "flour", "quantity": "500g", "category": "grains_pantry",
             "used_in": ["keema paratha"]},
            {"name": "lentils", "quantity": "500g", "category": "grains_pantry",
             "used_in": ["dal rice"]},
            {"name": "rice", "quantity": "1 kg", "category": "grains_pantry",
             "used_in": ["dal rice"]},
        ]
        yield mock


def test_shopping_organiser_extracts_ingredients(mock_claude, sample_state):
    result = shopping_organiser_node(sample_state)

    assert len(result["grocery_list"]) == 5
    assert result["shopping_retry_count"] == 0


def test_shopping_organiser_groups_by_category(mock_claude, sample_state):
    result = shopping_organiser_node(sample_state)

    categories = {item["category"] for item in result["grocery_list"]}
    assert "protein" in categories
    assert "produce" in categories
    assert "grains_pantry" in categories


def test_shopping_organiser_tracks_used_in(mock_claude, sample_state):
    result = shopping_organiser_node(sample_state)

    onions = next(item for item in result["grocery_list"] if item["name"] == "onions")
    assert "keema paratha" in onions["used_in"]
    assert "dal rice" in onions["used_in"]
