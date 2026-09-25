from app.agents.state import PlannedMeal, GroceryItem
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
from app.prompts.shopping_organiser import (
    SYSTEM_PROMPT as SHOPPING_SYSTEM_PROMPT,
    USER_TEMPLATE as SHOPPING_USER_TEMPLATE,
)
from app.prompts.validator import (
    SHOPPING_LIST_SYSTEM_PROMPT,
    SHOPPING_LIST_USER_TEMPLATE,
)
from app.services.preference_service import preference_service
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service

MAX_RETRIES = 3


def generate_swap_suggestion(
    day: str,
    meal_slot: str,
    current_dish: str,
    current_plan: list[dict],
) -> dict:
    prefs = preference_service.get()
    preference_text = prefs["dietary_preference"] if prefs else None

    # Step 1: LLM generates optimized RAG query
    context = preference_text or f"balanced meal for {meal_slot} on {day}"
    rag_query = claude_service.call(
        RAG_QUERY_SYSTEM_PROMPT,
        RAG_QUERY_USER_TEMPLATE.format(
            preference_or_context=context,
            meal_slot=meal_slot,
            day=day,
            current_dish=current_dish,
        ),
    ).strip()

    # Step 2: Query ChromaDB with the optimized query
    rag_results = chroma_service.query_meals(rag_query, n_results=10)
    rag_context = "\n".join(
        f"- {r['document']} (day: {r['metadata'].get('day', 'N/A')})"
        for r in rag_results
    ) or "No relevant meal history found."

    # Build context for meal generation
    other_dishes = ", ".join(
        m["dish"] for m in current_plan
        if not (m["day"] == day and m["meal_slot"] == meal_slot)
    )
    other_meal_for_day = next(
        (f"{m['meal_slot']}: {m['dish']}" for m in current_plan
         if m["day"] == day and m["meal_slot"] != meal_slot),
        "none",
    )
    preference_clause = (
        PREFERENCE_CLAUSE.format(preference=preference_text)
        if preference_text
        else NO_PREFERENCE
    )

    system_prompt = SINGLE_MEAL_SYSTEM_TEMPLATE.format(
        day=day,
        meal_slot=meal_slot,
        other_dishes=other_dishes,
        other_meal_for_day=other_meal_for_day,
        preference_clause=preference_clause,
    )
    user_msg = SINGLE_MEAL_USER_TEMPLATE.format(
        current_dish=current_dish,
        rag_results=rag_context,
    )

    # Retry loop: generate + validate
    last_suggestion = None
    last_status = "failed"
    last_warnings: list[str] = []

    for attempt in range(MAX_RETRIES):
        # Step 3: LLM generates one meal (meal planner agent logic)
        raw = claude_service.call_json(system_prompt, user_msg)
        if isinstance(raw, list):
            raw = raw[0]

        suggestion: PlannedMeal = {
            "day": raw.get("day", day),
            "meal_slot": raw.get("meal_slot", meal_slot),
            "dish": raw.get("dish", ""),
            "prep_time_min": raw.get("prep_time_min", 0),
            "reason": raw.get("reason", "new"),
            "ingredients": raw.get("ingredients", []),
        }
        last_suggestion = suggestion

        # Step 4: Validate (validator agent logic)
        verified = "not in history"
        if suggestion["reason"] == "from history":
            if chroma_service.meal_exists(suggestion["dish"]):
                verified = f"{suggestion['dish']}: verified in history"
            else:
                verified = f"{suggestion['dish']}: NOT found in history"

        meal_text = (
            f"{suggestion['day']} {suggestion['meal_slot']}: "
            f"{suggestion['dish']} ({suggestion['prep_time_min']}min) - {suggestion['reason']}"
        )

        # Build full plan text excluding the slot being swapped
        plan_for_validation = [
            m for m in current_plan
            if not (m["day"] == day and m["meal_slot"] == meal_slot)
        ]
        full_plan_text = "\n".join(
            f"{m['day']} {m['meal_slot']}: {m['dish']}"
            for m in plan_for_validation
        )

        validation = claude_service.call_json(
            SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT,
            SINGLE_MEAL_VALIDATOR_USER_TEMPLATE.format(
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


def apply_swap(
    current_plan: list[dict],
    day: str,
    meal_slot: str,
    new_meal: dict,
) -> dict:
    updated_plan = []
    for meal in current_plan:
        if meal["day"] == day and meal["meal_slot"] == meal_slot:
            updated_plan.append({
                "day": new_meal.get("day", day),
                "meal_slot": new_meal.get("meal_slot", meal_slot),
                "dish": new_meal.get("dish", ""),
                "prep_time_min": new_meal.get("prep_time_min", 0),
                "reason": new_meal.get("reason", "new"),
                "ingredients": new_meal.get("ingredients", []),
            })
        else:
            updated_plan.append(meal)

    # Regenerate shopping list
    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} - ingredients: {', '.join(m.get('ingredients', []))}"
        for m in updated_plan
    )
    raw_list = claude_service.call_json(
        SHOPPING_SYSTEM_PROMPT,
        SHOPPING_USER_TEMPLATE.format(meal_plan_text=meal_plan_text),
    )
    if isinstance(raw_list, dict):
        raw_list = [raw_list]

    grocery_list: list[GroceryItem] = []
    for item in raw_list:
        grocery_list.append({
            "name": item.get("name", ""),
            "quantity": item.get("quantity", ""),
            "category": item.get("category", ""),
            "used_in": item.get("used_in", []),
        })

    # Validate shopping list
    shopping_list_text = "\n".join(
        f"{item['name']} ({item['quantity']}) [{item['category']}] - used in: {', '.join(item['used_in'])}"
        for item in grocery_list
    )
    shopping_validation = claude_service.call_json(
        SHOPPING_LIST_SYSTEM_PROMPT,
        SHOPPING_LIST_USER_TEMPLATE.format(
            meal_plan_text=meal_plan_text,
            shopping_list_text=shopping_list_text,
        ),
    )

    shopping_errors = shopping_validation.get("errors", [])
    shopping_warnings = shopping_validation.get("warnings", [])
    if shopping_errors:
        shopping_status = "failed"
    elif shopping_warnings:
        shopping_status = "passed_with_warnings"
    else:
        shopping_status = "passed"

    return {
        "meal_plan": updated_plan,
        "grocery_list": grocery_list,
        "shopping_validation_status": shopping_status,
    }
