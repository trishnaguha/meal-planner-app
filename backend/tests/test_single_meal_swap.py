from unittest.mock import patch, MagicMock

import pytest

from app.agents.single_meal_swap import generate_swap_suggestion, apply_swap


@pytest.fixture
def current_plan():
    return [
        {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils", "rice"]},
        {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
         "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken", "onion", "spices"]},
        {"day": "Tuesday", "meal_slot": "lunch", "dish": "rajma chawal",
         "prep_time_min": 25, "reason": "from history", "ingredients": ["kidney beans", "rice"]},
        {"day": "Tuesday", "meal_slot": "dinner", "dish": "paneer tikka",
         "prep_time_min": 30, "reason": "from history", "ingredients": ["paneer", "bell pepper"]},
    ]


@pytest.fixture
def mock_all_services():
    with (
        patch("app.agents.single_meal_swap.preference_service") as mock_pref,
        patch("app.agents.single_meal_swap.chroma_service") as mock_chroma,
        patch("app.agents.single_meal_swap.claude_service") as mock_claude,
    ):
        mock_pref.get.return_value = {"dietary_preference": "protein and vegetables with carbohydrate"}

        mock_chroma.query_meals.return_value = [
            {"id": "meal_1", "document": "keema paratha - Saturday - indian,protein",
             "metadata": {"dish": "keema paratha", "day": "Saturday", "tags": "indian,protein"}, "distance": 0.3},
            {"id": "meal_2", "document": "egg bhurji - Sunday - protein,indian",
             "metadata": {"dish": "egg bhurji", "day": "Sunday", "tags": "protein,indian"}, "distance": 0.4},
        ]
        mock_chroma.meal_exists.return_value = True

        mock_claude.call.return_value = "protein vegetable indian lunch"

        mock_claude.call_json.side_effect = [
            {
                "day": "Monday",
                "meal_slot": "lunch",
                "dish": "keema paratha",
                "prep_time_min": 30,
                "reason": "from history",
                "ingredients": ["ground meat", "flour", "onion"],
            },
            {
                "is_valid": True,
                "errors": [],
                "warnings": [],
            },
        ]

        yield mock_pref, mock_chroma, mock_claude


def test_generate_swap_returns_suggestion(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    result = generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    assert result["suggestion"]["dish"] == "keema paratha"
    assert result["suggestion"]["day"] == "Monday"
    assert result["suggestion"]["meal_slot"] == "lunch"
    assert result["validation_status"] == "passed"


def test_generate_swap_uses_preference_for_rag(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    mock_claude.call.assert_called_once()
    rag_call_args = mock_claude.call.call_args
    assert "protein and vegetables with carbohydrate" in rag_call_args[0][1]


def test_generate_swap_queries_chromadb_with_llm_output(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    mock_chroma.query_meals.assert_called_once_with("protein vegetable indian lunch", n_results=10)


def test_generate_swap_without_preference(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services
    mock_pref.get.return_value = None

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    rag_call_args = mock_claude.call.call_args
    assert "lunch" in rag_call_args[0][1]
    assert "Monday" in rag_call_args[0][1]


def test_generate_swap_retries_on_validation_failure(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
        {"is_valid": False, "errors": ["Duplicate dish: dal rice"], "warnings": []},
        {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
         "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]},
        {"is_valid": True, "errors": [], "warnings": []},
    ]

    result = generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)
    assert result["suggestion"]["dish"] == "keema paratha"
    assert result["validation_status"] == "passed"


def test_generate_swap_gives_up_after_max_retries(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "lunch", "dish": "bad1",
         "prep_time_min": 20, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue1"], "warnings": []},
        {"day": "Monday", "meal_slot": "lunch", "dish": "bad2",
         "prep_time_min": 20, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue2"], "warnings": []},
        {"day": "Monday", "meal_slot": "lunch", "dish": "bad3",
         "prep_time_min": 20, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue3"], "warnings": []},
    ]

    result = generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)
    assert result["suggestion"]["dish"] == "bad3"
    assert result["validation_status"] == "failed"


def test_generate_swap_excludes_current_plan_dishes(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    meal_gen_call = mock_claude.call_json.call_args_list[0]
    system_prompt = meal_gen_call[0][0]
    assert "chicken curry" in system_prompt
    assert "rajma chawal" in system_prompt


@pytest.fixture
def mock_apply_services():
    with (
        patch("app.agents.single_meal_swap.claude_service") as mock_claude,
    ):
        mock_claude.call_json.side_effect = [
            [{"name": "lentils", "quantity": "500g", "category": "grains_pantry", "used_in": ["dal"]}],
            {"is_valid": True, "errors": [], "warnings": []},
        ]
        yield mock_claude


def test_apply_swap_replaces_meal(mock_apply_services, current_plan):
    new_meal = {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]}

    result = apply_swap(current_plan, "Monday", "lunch", new_meal)

    updated_plan = result["meal_plan"]
    monday_lunch = [m for m in updated_plan if m["day"] == "Monday" and m["meal_slot"] == "lunch"]
    assert len(monday_lunch) == 1
    assert monday_lunch[0]["dish"] == "keema paratha"


def test_apply_swap_preserves_other_meals(mock_apply_services, current_plan):
    new_meal = {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]}

    result = apply_swap(current_plan, "Monday", "lunch", new_meal)

    updated_plan = result["meal_plan"]
    assert len(updated_plan) == len(current_plan)
    tuesday_meals = [m for m in updated_plan if m["day"] == "Tuesday"]
    assert len(tuesday_meals) == 2


def test_apply_swap_regenerates_shopping_list(mock_apply_services, current_plan):
    new_meal = {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]}

    result = apply_swap(current_plan, "Monday", "lunch", new_meal)

    assert "grocery_list" in result
    assert len(result["grocery_list"]) > 0
