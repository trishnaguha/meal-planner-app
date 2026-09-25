from app.agents.state import PlannedMeal
from app.prompts.single_meal_swap import RAG_QUERY_SYSTEM_PROMPT
from app.prompts.breakfast import (
    RAG_QUERY_USER_TEMPLATE,
    BREAKFAST_SYSTEM_TEMPLATE,
    BREAKFAST_USER_TEMPLATE,
    PREFERENCE_CLAUSE,
    NO_PREFERENCE,
    BREAKFAST_VALIDATOR_SYSTEM_PROMPT,
    BREAKFAST_VALIDATOR_USER_TEMPLATE,
)
from app.agents.shopping_organiser import rebuild_grocery_list
from app.services.preference_service import preference_service
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service

MAX_RETRIES = 3
SLOT_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2}


def generate_breakfast_suggestion(day: str, current_plan: list[dict]) -> dict:
    prefs = preference_service.get()
    preference_text = prefs["dietary_preference"] if prefs else None

    # Step 1: LLM generates an optimized RAG query
    context = preference_text or f"light breakfast for {day}"
    rag_query = claude_service.call(
        RAG_QUERY_SYSTEM_PROMPT,
        RAG_QUERY_USER_TEMPLATE.format(
            preference_or_context=context,
            day=day,
        ),
    ).strip()

    # Step 2: Query ChromaDB with the optimized query
    rag_results = chroma_service.query_meals(rag_query, n_results=10)
    rag_context = "\n".join(
        f"- {r['document']} (day: {r['metadata'].get('day', 'N/A')})"
        for r in rag_results
    ) or "No relevant meal history found."

    other_dishes = ", ".join(m["dish"] for m in current_plan)
    other_meals_for_day = ", ".join(
        f"{m['meal_slot']}: {m['dish']}"
        for m in current_plan
        if m["day"] == day
    ) or "none"
    preference_clause = (
        PREFERENCE_CLAUSE.format(preference=preference_text)
        if preference_text
        else NO_PREFERENCE
    )

    system_prompt = BREAKFAST_SYSTEM_TEMPLATE.format(
        day=day,
        other_dishes=other_dishes,
        other_meals_for_day=other_meals_for_day,
        preference_clause=preference_clause,
    )
    user_msg = BREAKFAST_USER_TEMPLATE.format(rag_results=rag_context)

    last_suggestion = None
    last_status = "failed"
    last_warnings: list[str] = []

    for attempt in range(MAX_RETRIES):
        # Step 3: LLM generates one breakfast
        raw = claude_service.call_json(system_prompt, user_msg)
        if isinstance(raw, list):
            raw = raw[0]

        suggestion: PlannedMeal = {
            "day": raw.get("day", day),
            "meal_slot": "breakfast",
            "dish": raw.get("dish", ""),
            "prep_time_min": raw.get("prep_time_min", 0),
            "reason": raw.get("reason", "new"),
            "ingredients": raw.get("ingredients", []),
        }
        last_suggestion = suggestion

        # Step 4: Validator agent
        verified = "not in history"
        if suggestion["reason"] == "from history":
            if chroma_service.meal_exists(suggestion["dish"]):
                verified = f"{suggestion['dish']}: verified in history"
            else:
                verified = f"{suggestion['dish']}: NOT found in history"

        meal_text = (
            f"{suggestion['day']} breakfast: "
            f"{suggestion['dish']} ({suggestion['prep_time_min']}min) - {suggestion['reason']}"
        )
        full_plan_text = "\n".join(
            f"{m['day']} {m['meal_slot']}: {m['dish']}" for m in current_plan
        )

        validation = claude_service.call_json(
            BREAKFAST_VALIDATOR_SYSTEM_PROMPT,
            BREAKFAST_VALIDATOR_USER_TEMPLATE.format(
                meal_text=meal_text,
                full_plan_text=full_plan_text,
                verified_status=verified,
            ),
        )

        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        last_warnings = warnings

        if not errors:
            last_status = "passed_with_warnings" if warnings else "passed"
            break
        elif attempt == MAX_RETRIES - 1:
            last_status = "failed"
            last_warnings = errors + warnings

    return {
        "suggestion": last_suggestion,
        "validation_status": last_status,
        "validation_warnings": last_warnings,
    }


def _order_plan(meal_plan: list[dict]) -> list[dict]:
    """Sort meals breakfast/lunch/dinner within each day, preserving day order."""
    day_order: list[str] = []
    for meal in meal_plan:
        if meal["day"] not in day_order:
            day_order.append(meal["day"])
    return sorted(
        meal_plan,
        key=lambda m: (day_order.index(m["day"]), SLOT_ORDER.get(m["meal_slot"], 99)),
    )


def add_breakfast(current_plan: list[dict], day: str, new_meal: dict) -> dict:
    without_existing = [
        m for m in current_plan
        if not (m["day"] == day and m["meal_slot"] == "breakfast")
    ]
    breakfast = {
        "day": day,
        "meal_slot": "breakfast",
        "dish": new_meal.get("dish", ""),
        "prep_time_min": new_meal.get("prep_time_min", 0),
        "reason": new_meal.get("reason", "new"),
        "ingredients": new_meal.get("ingredients", []),
    }
    updated_plan = _order_plan(without_existing + [breakfast])

    rebuilt = rebuild_grocery_list(updated_plan)
    return {
        "meal_plan": updated_plan,
        "grocery_list": rebuilt["grocery_list"],
        "shopping_validation_status": rebuilt["shopping_validation_status"],
    }


def remove_breakfast(current_plan: list[dict], day: str) -> dict:
    updated_plan = [
        m for m in current_plan
        if not (m["day"] == day and m["meal_slot"] == "breakfast")
    ]

    rebuilt = rebuild_grocery_list(updated_plan)
    return {
        "meal_plan": updated_plan,
        "grocery_list": rebuilt["grocery_list"],
        "shopping_validation_status": rebuilt["shopping_validation_status"],
    }
