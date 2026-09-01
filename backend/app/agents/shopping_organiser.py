from app.agents.state import MealPlannerState, GroceryItem
from app.prompts.shopping_organiser import SYSTEM_PROMPT, USER_TEMPLATE
from app.services.claude_service import claude_service


def shopping_organiser_node(state: MealPlannerState) -> dict:
    meal_plan = state.get("meal_plan", [])

    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} - ingredients: {', '.join(m.get('ingredients', []))}"
        for m in meal_plan
    )

    raw_list = claude_service.call_json(
        SYSTEM_PROMPT,
        USER_TEMPLATE.format(meal_plan_text=meal_plan_text),
    )

    if isinstance(raw_list, dict):
        raw_list = [raw_list]

    grocery_list: list[GroceryItem] = []
    for item in raw_list:
        grocery: GroceryItem = {
            "name": item.get("name", ""),
            "quantity": item.get("quantity", ""),
            "category": item.get("category", ""),
            "used_in": item.get("used_in", []),
        }
        grocery_list.append(grocery)

    return {
        "grocery_list": grocery_list,
        "shopping_retry_count": 0,
    }
