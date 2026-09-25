from unittest.mock import patch

import pytest

from app.agents.breakfast import (
    generate_breakfast_suggestion,
    add_breakfast,
    remove_breakfast,
)


@pytest.fixture
def current_plan():
    return [
        {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils", "rice"]},
        {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
         "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken", "onion"]},
        {"day": "Tuesday", "meal_slot": "lunch", "dish": "rajma chawal",
         "prep_time_min": 25, "reason": "from history", "ingredients": ["kidney beans", "rice"]},
    ]


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.breakfast.preference_service") as mock_pref,
        patch("app.agents.breakfast.chroma_service") as mock_chroma,
        patch("app.agents.breakfast.claude_service") as mock_claude,
    ):
        mock_pref.get.return_value = {"dietary_preference": "high protein"}
        mock_chroma.query_meals.return_value = [
            {"id": "meal_1", "document": "poha - Sunday - indian,light",
             "metadata": {"dish": "poha", "day": "Sunday"}, "distance": 0.3},
        ]
        mock_chroma.meal_exists.return_value = True
        mock_claude.call.return_value = "light indian breakfast protein"
        mock_claude.call_json.side_effect = [
            {"day": "Monday", "meal_slot": "breakfast", "dish": "poha",
             "prep_time_min": 15, "reason": "from history",
             "ingredients": ["flattened rice", "onion", "peanuts"]},
            {"is_valid": True, "errors": [], "warnings": []},
        ]
        yield mock_pref, mock_chroma, mock_claude


def test_returns_breakfast_suggestion(mock_services, current_plan):
    result = generate_breakfast_suggestion("Monday", current_plan)

    assert result["suggestion"]["dish"] == "poha"
    assert result["suggestion"]["day"] == "Monday"
    assert result["suggestion"]["meal_slot"] == "breakfast"
    assert result["validation_status"] == "passed"


def test_forces_breakfast_slot_even_if_llm_omits_it(mock_services, current_plan):
    _, _, mock_claude = mock_services
    mock_claude.call_json.side_effect = [
        {"day": "Monday", "dish": "poha", "prep_time_min": 15,
         "reason": "new", "ingredients": ["flattened rice"]},
        {"is_valid": True, "errors": [], "warnings": []},
    ]

    result = generate_breakfast_suggestion("Monday", current_plan)

    assert result["suggestion"]["meal_slot"] == "breakfast"


def test_uses_preference_in_rag_query(mock_services, current_plan):
    _, _, mock_claude = mock_services

    generate_breakfast_suggestion("Monday", current_plan)

    mock_claude.call.assert_called_once()
    assert "high protein" in mock_claude.call.call_args[0][1]


def test_queries_chromadb_with_llm_query(mock_services, current_plan):
    _, mock_chroma, _ = mock_services

    generate_breakfast_suggestion("Monday", current_plan)

    mock_chroma.query_meals.assert_called_once_with(
        "light indian breakfast protein", n_results=10
    )


def test_empty_history_is_not_an_error(mock_services, current_plan):
    _, mock_chroma, mock_claude = mock_services
    mock_chroma.query_meals.return_value = []
    mock_chroma.meal_exists.return_value = False
    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "breakfast", "dish": "masala oats",
         "prep_time_min": 10, "reason": "new", "ingredients": ["oats", "spices"]},
        {"is_valid": True, "errors": [], "warnings": []},
    ]

    result = generate_breakfast_suggestion("Monday", current_plan)

    assert result["suggestion"]["reason"] == "new"
    assert result["validation_status"] == "passed"
    user_msg = mock_claude.call_json.call_args_list[0][0][1]
    assert "No relevant meal history found." in user_msg


def test_excludes_existing_plan_dishes_from_generation(mock_services, current_plan):
    _, _, mock_claude = mock_services

    generate_breakfast_suggestion("Monday", current_plan)

    system_prompt = mock_claude.call_json.call_args_list[0][0][0]
    assert "dal rice" in system_prompt
    assert "chicken curry" in system_prompt
    assert "rajma chawal" in system_prompt


def test_retries_when_validator_reports_a_duplicate(mock_services, current_plan):
    """Review Focus 4: a breakfast duplicating an existing lunch must be rejected."""
    _, _, mock_claude = mock_services
    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "breakfast", "dish": "dal rice",
         "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
        {"is_valid": False, "errors": ["Duplicate dish: dal rice"], "warnings": []},
        {"day": "Monday", "meal_slot": "breakfast", "dish": "poha",
         "prep_time_min": 15, "reason": "from history", "ingredients": ["flattened rice"]},
        {"is_valid": True, "errors": [], "warnings": []},
    ]

    result = generate_breakfast_suggestion("Monday", current_plan)

    assert result["suggestion"]["dish"] == "poha"
    assert result["validation_status"] == "passed"


def test_gives_up_after_max_retries(mock_services, current_plan):
    _, _, mock_claude = mock_services
    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "breakfast", "dish": "bad1",
         "prep_time_min": 10, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue1"], "warnings": []},
        {"day": "Monday", "meal_slot": "breakfast", "dish": "bad2",
         "prep_time_min": 10, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue2"], "warnings": []},
        {"day": "Monday", "meal_slot": "breakfast", "dish": "bad3",
         "prep_time_min": 10, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue3"], "warnings": []},
    ]

    result = generate_breakfast_suggestion("Monday", current_plan)

    assert result["suggestion"]["dish"] == "bad3"
    assert result["validation_status"] == "failed"
    assert "issue3" in result["validation_warnings"]


def test_warnings_produce_passed_with_warnings(mock_services, current_plan):
    _, _, mock_claude = mock_services
    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "breakfast", "dish": "poha",
         "prep_time_min": 15, "reason": "new", "ingredients": ["flattened rice"]},
        {"is_valid": True, "errors": [], "warnings": ["light on protein"]},
    ]

    result = generate_breakfast_suggestion("Monday", current_plan)

    assert result["validation_status"] == "passed_with_warnings"
    assert result["validation_warnings"] == ["light on protein"]


def test_works_without_a_stored_preference(mock_services, current_plan):
    mock_pref, _, mock_claude = mock_services
    mock_pref.get.return_value = None

    generate_breakfast_suggestion("Monday", current_plan)

    assert "Monday" in mock_claude.call.call_args[0][1]


@pytest.fixture
def mock_rebuild():
    with patch("app.agents.shopping_organiser.claude_service") as mock_claude:
        mock_claude.call_json.side_effect = [
            [{"name": "flattened rice", "quantity": "500g",
              "category": "grains_pantry", "used_in": ["poha"]}],
            {"is_valid": True, "errors": [], "warnings": []},
        ]
        yield mock_claude


BREAKFAST_MEAL = {
    "day": "Monday", "meal_slot": "breakfast", "dish": "poha",
    "prep_time_min": 15, "reason": "new", "ingredients": ["flattened rice", "onion"],
}


def test_add_breakfast_inserts_the_slot(mock_rebuild, current_plan):
    result = add_breakfast(current_plan, "Monday", BREAKFAST_MEAL)

    monday_breakfast = [
        m for m in result["meal_plan"]
        if m["day"] == "Monday" and m["meal_slot"] == "breakfast"
    ]
    assert len(monday_breakfast) == 1
    assert monday_breakfast[0]["dish"] == "poha"
    assert len(result["meal_plan"]) == len(current_plan) + 1


def test_add_breakfast_orders_the_day_breakfast_lunch_dinner(mock_rebuild, current_plan):
    result = add_breakfast(current_plan, "Monday", BREAKFAST_MEAL)

    monday = [m["meal_slot"] for m in result["meal_plan"] if m["day"] == "Monday"]
    assert monday == ["breakfast", "lunch", "dinner"]


def test_add_breakfast_preserves_day_order(mock_rebuild, current_plan):
    result = add_breakfast(current_plan, "Monday", BREAKFAST_MEAL)

    seen = []
    for m in result["meal_plan"]:
        if m["day"] not in seen:
            seen.append(m["day"])
    assert seen == ["Monday", "Tuesday"]


def test_add_breakfast_leaves_other_days_untouched(mock_rebuild, current_plan):
    result = add_breakfast(current_plan, "Monday", BREAKFAST_MEAL)

    tuesday = [m for m in result["meal_plan"] if m["day"] == "Tuesday"]
    assert len(tuesday) == 1
    assert tuesday[0]["dish"] == "rajma chawal"


def test_add_breakfast_replaces_an_existing_breakfast(mock_rebuild, current_plan):
    plan = [BREAKFAST_MEAL] + current_plan
    replacement = {**BREAKFAST_MEAL, "dish": "masala oats"}

    result = add_breakfast(plan, "Monday", replacement)

    monday_breakfast = [
        m for m in result["meal_plan"]
        if m["day"] == "Monday" and m["meal_slot"] == "breakfast"
    ]
    assert len(monday_breakfast) == 1
    assert monday_breakfast[0]["dish"] == "masala oats"


def test_add_breakfast_rebuilds_the_shopping_list(mock_rebuild, current_plan):
    result = add_breakfast(current_plan, "Monday", BREAKFAST_MEAL)

    assert result["grocery_list"][0]["name"] == "flattened rice"
    assert result["shopping_validation_status"] == "passed"


def test_remove_breakfast_drops_the_slot(mock_rebuild, current_plan):
    plan = [BREAKFAST_MEAL] + current_plan

    result = remove_breakfast(plan, "Monday")

    assert all(
        not (m["day"] == "Monday" and m["meal_slot"] == "breakfast")
        for m in result["meal_plan"]
    )
    assert len(result["meal_plan"]) == len(current_plan)


def test_remove_breakfast_on_a_day_without_one_is_a_noop(mock_rebuild, current_plan):
    result = remove_breakfast(current_plan, "Monday")

    assert result["meal_plan"] == current_plan


def test_remove_breakfast_only_affects_the_named_day(mock_rebuild, current_plan):
    plan = [BREAKFAST_MEAL, {**BREAKFAST_MEAL, "day": "Tuesday", "dish": "idli"}] + current_plan

    result = remove_breakfast(plan, "Monday")

    tuesday_breakfast = [
        m for m in result["meal_plan"]
        if m["day"] == "Tuesday" and m["meal_slot"] == "breakfast"
    ]
    assert len(tuesday_breakfast) == 1
    assert tuesday_breakfast[0]["dish"] == "idli"


def test_remove_last_meal_of_a_day_empties_that_day(mock_rebuild):
    """Review Focus 3: removing a breakfast that is the day's only meal."""
    plan = [
        {"day": "Monday", "meal_slot": "breakfast", "dish": "poha",
         "prep_time_min": 15, "reason": "new", "ingredients": ["flattened rice"]},
        {"day": "Tuesday", "meal_slot": "lunch", "dish": "rajma chawal",
         "prep_time_min": 25, "reason": "from history", "ingredients": ["kidney beans"]},
    ]

    result = remove_breakfast(plan, "Monday")

    assert all(m["day"] != "Monday" for m in result["meal_plan"])
    assert len(result["meal_plan"]) == 1


def test_remove_breakfast_rebuilds_the_shopping_list(mock_rebuild, current_plan):
    plan = [BREAKFAST_MEAL] + current_plan

    result = remove_breakfast(plan, "Monday")

    assert result["grocery_list"][0]["name"] == "flattened rice"
    assert result["shopping_validation_status"] == "passed"
