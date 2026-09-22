from app.prompts.single_meal_swap import (
    RAG_QUERY_SYSTEM_PROMPT,
    RAG_QUERY_USER_TEMPLATE,
    SINGLE_MEAL_SYSTEM_TEMPLATE,
    SINGLE_MEAL_USER_TEMPLATE,
    PREFERENCE_CLAUSE,
    NO_PREFERENCE,
    SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT,
    SINGLE_MEAL_VALIDATOR_USER_TEMPLATE,
)


def test_rag_query_user_template_formats():
    result = RAG_QUERY_USER_TEMPLATE.format(
        preference_or_context="protein and vegetables",
        meal_slot="lunch",
        day="Monday",
        current_dish="dal rice",
    )
    assert "protein and vegetables" in result
    assert "lunch" in result
    assert "Monday" in result
    assert "dal rice" in result


def test_single_meal_system_template_formats_with_preference():
    result = SINGLE_MEAL_SYSTEM_TEMPLATE.format(
        day="Monday",
        meal_slot="lunch",
        other_dishes="dal rice, keema paratha",
        other_meal_for_day="dinner: chicken curry",
        preference_clause=PREFERENCE_CLAUSE.format(preference="high protein"),
    )
    assert "Monday" in result
    assert "lunch" in result
    assert "dal rice, keema paratha" in result
    assert "high protein" in result


def test_single_meal_system_template_formats_without_preference():
    result = SINGLE_MEAL_SYSTEM_TEMPLATE.format(
        day="Monday",
        meal_slot="lunch",
        other_dishes="dal rice",
        other_meal_for_day="dinner: chicken curry",
        preference_clause=NO_PREFERENCE,
    )
    assert "Monday" in result
    assert "dietary preference" not in result.lower() or NO_PREFERENCE == ""


def test_single_meal_user_template_formats():
    result = SINGLE_MEAL_USER_TEMPLATE.format(
        current_dish="dal rice",
        rag_results="- keema paratha - Saturday - indian,protein",
    )
    assert "dal rice" in result
    assert "keema paratha" in result


def test_validator_template_formats():
    result = SINGLE_MEAL_VALIDATOR_USER_TEMPLATE.format(
        meal_text="Monday lunch: chicken curry (30min) - from history",
        full_plan_text="Monday lunch: dal\nMonday dinner: chicken curry",
        verified_status="chicken curry: verified in history",
    )
    assert "chicken curry" in result
    assert "Monday" in result


def test_no_preference_is_empty():
    assert NO_PREFERENCE == ""


def test_rag_query_system_prompt_exists():
    assert len(RAG_QUERY_SYSTEM_PROMPT) > 0
    assert "search" in RAG_QUERY_SYSTEM_PROMPT.lower() or "query" in RAG_QUERY_SYSTEM_PROMPT.lower()


def test_validator_system_prompt_exists():
    assert len(SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT) > 0
