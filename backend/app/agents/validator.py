from app.agents.state import MealPlannerState
from app.prompts.validator import (
    MEAL_PLAN_SYSTEM_PROMPT,
    MEAL_PLAN_USER_TEMPLATE,
    SHOPPING_LIST_SYSTEM_PROMPT,
    SHOPPING_LIST_USER_TEMPLATE,
)
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service


def meal_validator_node(state: MealPlannerState) -> dict:
    meal_plan = state.get("meal_plan", [])
    retry_count = state.get("retry_count", 0)

    verified = []
    unverified = []
    for meal in meal_plan:
        if meal.get("reason") == "past favorite":
            if chroma_service.meal_exists(meal["dish"]):
                verified.append(meal["dish"])
            else:
                unverified.append(meal["dish"])

    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} ({m['prep_time_min']}min) - {m['reason']}"
        for m in meal_plan
    )

    result = claude_service.call_json(
        MEAL_PLAN_SYSTEM_PROMPT,
        MEAL_PLAN_USER_TEMPLATE.format(
            meal_plan_text=meal_plan_text,
            verified_dishes=", ".join(verified) if verified else "none",
            unverified_dishes=", ".join(unverified) if unverified else "none",
        ),
    )

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if unverified:
        warnings.append(f"Dishes claimed as favorites but not in history: {', '.join(unverified)}")

    if errors:
        status = "failed"
        retry_count += 1
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"

    return {
        "validation_status": status,
        "validation_errors": errors,
        "validation_warnings": warnings,
        "retry_count": retry_count,
    }


def shopping_validator_node(state: MealPlannerState) -> dict:
    meal_plan = state.get("meal_plan", [])
    grocery_list = state.get("grocery_list", [])
    shopping_retry_count = state.get("shopping_retry_count", 0)

    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} - ingredients: {', '.join(m.get('ingredients', []))}"
        for m in meal_plan
    )
    shopping_list_text = "\n".join(
        f"{item['name']} ({item['quantity']}) [{item['category']}] - used in: {', '.join(item['used_in'])}"
        for item in grocery_list
    )

    result = claude_service.call_json(
        SHOPPING_LIST_SYSTEM_PROMPT,
        SHOPPING_LIST_USER_TEMPLATE.format(
            meal_plan_text=meal_plan_text,
            shopping_list_text=shopping_list_text,
        ),
    )

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if errors:
        status = "failed"
        shopping_retry_count += 1
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"

    return {
        "shopping_validation_status": status,
        "shopping_validation_errors": errors,
        "shopping_retry_count": shopping_retry_count,
    }
