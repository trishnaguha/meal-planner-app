from app.prompts.breakfast import (
    RAG_QUERY_USER_TEMPLATE,
    BREAKFAST_SYSTEM_TEMPLATE,
    BREAKFAST_USER_TEMPLATE,
    PREFERENCE_CLAUSE,
    NO_PREFERENCE,
    BREAKFAST_VALIDATOR_SYSTEM_PROMPT,
    BREAKFAST_VALIDATOR_USER_TEMPLATE,
)


def test_rag_query_user_template_formats():
    result = RAG_QUERY_USER_TEMPLATE.format(
        preference_or_context="high protein",
        day="Monday",
    )
    assert "high protein" in result
    assert "Monday" in result
    assert "breakfast" in result.lower()


def test_breakfast_system_template_formats_with_preference():
    result = BREAKFAST_SYSTEM_TEMPLATE.format(
        day="Monday",
        other_dishes="dal rice, chicken curry",
        other_meals_for_day="lunch: dal rice",
        preference_clause=PREFERENCE_CLAUSE.format(preference="high protein"),
    )
    assert "Monday" in result
    assert "dal rice, chicken curry" in result
    assert "high protein" in result
    assert '"meal_slot": "breakfast"' in result


def test_breakfast_system_template_formats_without_preference():
    result = BREAKFAST_SYSTEM_TEMPLATE.format(
        day="Monday",
        other_dishes="dal rice",
        other_meals_for_day="lunch: dal rice",
        preference_clause=NO_PREFERENCE,
    )
    assert "Monday" in result
    assert "dietary preference" not in result.lower()


def test_breakfast_system_template_permits_inventing_a_breakfast():
    """Empty breakfast history is the expected case, not a failure."""
    result = BREAKFAST_SYSTEM_TEMPLATE.format(
        day="Monday",
        other_dishes="dal rice",
        other_meals_for_day="lunch: dal rice",
        preference_clause=NO_PREFERENCE,
    )
    assert "invent" in result.lower()
    assert '"new"' in result


def test_breakfast_user_template_formats():
    result = BREAKFAST_USER_TEMPLATE.format(
        rag_results="- poha - Sunday - indian,light",
    )
    assert "poha" in result


def test_validator_template_formats():
    result = BREAKFAST_VALIDATOR_USER_TEMPLATE.format(
        meal_text="Monday breakfast: poha (15min) - from history",
        full_plan_text="Monday lunch: dal rice",
        verified_status="poha: verified in history",
    )
    assert "poha" in result
    assert "dal rice" in result


def test_no_preference_is_empty():
    assert NO_PREFERENCE == ""


def test_validator_system_prompt_exists():
    assert len(BREAKFAST_VALIDATOR_SYSTEM_PROMPT) > 0
    assert "breakfast" in BREAKFAST_VALIDATOR_SYSTEM_PROMPT.lower()
