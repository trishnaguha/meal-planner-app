from app.agents.state import MealPlannerState, PlannedMeal
from app.prompts.meal_planner import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    EXCLUSION_CLAUSE,
    NO_EXCLUSION,
)
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service


def meal_planner_node(state: MealPlannerState) -> dict:
    history_results = chroma_service.get_all_meals()

    history_context = "\n".join(
        f"- {r['document']} (day: {r['metadata'].get('day', 'N/A')})"
        for r in history_results
    ) or "No meal history available. Generate a balanced plan from scratch."

    excluded = state.get("excluded_dishes", [])
    if excluded:
        exclusion_clause = EXCLUSION_CLAUSE.format(excluded=", ".join(excluded))
    else:
        exclusion_clause = NO_EXCLUSION

    system = SYSTEM_PROMPT.format(exclusion_clause=exclusion_clause)
    user_msg = USER_TEMPLATE.format(history_context=history_context)

    raw_plan = claude_service.call_json(system, user_msg)

    if isinstance(raw_plan, dict):
        raw_plan = [raw_plan]

    meal_plan: list[PlannedMeal] = []
    for item in raw_plan:
        meal: PlannedMeal = {
            "day": item.get("day", ""),
            "meal_slot": item.get("meal_slot", ""),
            "dish": item.get("dish", ""),
            "prep_time_min": item.get("prep_time_min", 0),
            "reason": item.get("reason", "new"),
            "ingredients": item.get("ingredients", []),
        }
        meal_plan.append(meal)

    return {"meal_plan": meal_plan, "retry_count": 0}
