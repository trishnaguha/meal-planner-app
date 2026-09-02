from unittest.mock import MagicMock, patch

import pytest

from app.agents.meal_planner import meal_planner_node


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.meal_planner.claude_service") as mock_claude,
        patch("app.agents.meal_planner.chroma_service") as mock_chroma,
    ):
        mock_chroma.query_meals.return_value = [
            {
                "id": "meal_1",
                "document": "keema paratha - Saturday - indian,protein",
                "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian,protein"},
            },
            {
                "id": "meal_2",
                "document": "dal rice - Monday - indian,lentils",
                "metadata": {"day": "Monday", "dish": "dal rice", "tags": "indian,lentils"},
            },
        ]

        mock_claude.call_json.return_value = [
            {
                "day": "Monday",
                "meal_slot": "breakfast",
                "dish": "Oatmeal with fruit",
                "prep_time_min": 10,
                "reason": "new for variety",
                "ingredients": ["oats", "banana", "honey"],
            },
            {
                "day": "Monday",
                "meal_slot": "lunch",
                "dish": "keema paratha",
                "prep_time_min": 30,
                "reason": "past favorite",
                "ingredients": ["ground meat", "flour", "onion"],
            },
        ]
        yield mock_claude, mock_chroma


def test_meal_planner_generates_plan(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {"action": "generate", "excluded_dishes": []}

    result = meal_planner_node(state)

    assert len(result["meal_plan"]) == 2
    assert result["meal_plan"][0]["dish"] == "Oatmeal with fruit"
    assert result["meal_plan"][1]["reason"] == "past favorite"


def test_meal_planner_queries_chromadb(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {"action": "generate", "excluded_dishes": []}

    meal_planner_node(state)

    mock_chroma.query_meals.assert_called_once()


def test_meal_planner_passes_exclusions(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {"action": "swap", "excluded_dishes": ["Oatmeal with fruit"]}

    meal_planner_node(state)

    call_args = mock_claude.call_json.call_args
    system_prompt = call_args[0][0]
    assert "Oatmeal with fruit" in system_prompt
