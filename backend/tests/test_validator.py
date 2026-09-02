from unittest.mock import MagicMock, patch

import pytest

from app.agents.validator import meal_validator_node, shopping_validator_node


@pytest.fixture
def valid_meal_plan():
    return [
        {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
         "prep_time_min": 30, "reason": "past favorite", "ingredients": ["meat", "flour"]},
        {"day": "Tuesday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "past favorite", "ingredients": ["lentils", "rice"]},
    ]


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.validator.claude_service") as mock_claude,
        patch("app.agents.validator.chroma_service") as mock_chroma,
    ):
        mock_chroma.meal_exists.return_value = True
        yield mock_claude, mock_chroma


def test_meal_validator_passes_valid_plan(mock_services, valid_meal_plan):
    mock_claude, mock_chroma = mock_services
    mock_claude.call_json.return_value = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    state = {"meal_plan": valid_meal_plan, "retry_count": 0}

    result = meal_validator_node(state)

    assert result["validation_status"] == "passed"
    assert result["validation_errors"] == []


def test_meal_validator_fails_with_errors(mock_services, valid_meal_plan):
    mock_claude, mock_chroma = mock_services
    mock_claude.call_json.return_value = {
        "is_valid": False,
        "errors": ["Duplicate dish: keema paratha appears on Monday and Wednesday"],
        "warnings": [],
    }
    state = {"meal_plan": valid_meal_plan, "retry_count": 0}

    result = meal_validator_node(state)

    assert result["validation_status"] == "failed"
    assert len(result["validation_errors"]) == 1
    assert result["retry_count"] == 1


def test_meal_validator_flags_unverified_favorites(mock_services, valid_meal_plan):
    mock_claude, mock_chroma = mock_services
    mock_chroma.meal_exists.side_effect = lambda dish: dish == "keema paratha"
    mock_claude.call_json.return_value = {
        "is_valid": True,
        "errors": [],
        "warnings": ["dal rice claimed as favorite but not in history"],
    }
    state = {"meal_plan": valid_meal_plan, "retry_count": 0}

    result = meal_validator_node(state)

    assert result["validation_status"] == "passed_with_warnings"


def test_shopping_validator_passes(mock_services):
    mock_claude, _ = mock_services
    mock_claude.call_json.return_value = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    state = {
        "meal_plan": [{"day": "Monday", "meal_slot": "lunch", "dish": "dal",
                        "prep_time_min": 20, "reason": "past favorite", "ingredients": ["lentils"]}],
        "grocery_list": [{"name": "lentils", "quantity": "500g", "category": "grains_pantry",
                          "used_in": ["dal"]}],
        "shopping_retry_count": 0,
    }

    result = shopping_validator_node(state)

    assert result["shopping_validation_status"] == "passed"
