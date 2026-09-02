from app.agents.state import MealEntry, PlannedMeal, GroceryItem, MealPlannerState


def test_meal_entry_structure(sample_meal_entry):
    entry: MealEntry = sample_meal_entry
    assert entry["day"] == "Saturday"
    assert "keema paratha" in entry["dishes"]
    assert entry["quantity"] == 5
    assert "indian" in entry["tags"]


def test_planned_meal_structure(sample_planned_meal):
    meal: PlannedMeal = sample_planned_meal
    assert meal["day"] == "Monday"
    assert meal["meal_slot"] == "lunch"
    assert meal["dish"] == "keema paratha"
    assert meal["prep_time_min"] == 30


def test_grocery_item_structure(sample_grocery_item):
    item: GroceryItem = sample_grocery_item
    assert item["name"] == "ground meat"
    assert item["category"] == "protein"
    assert "keema paratha" in item["used_in"]


def test_meal_planner_state_partial():
    state: MealPlannerState = {
        "action": "upload",
        "raw_text": "Saturday 5 keema paratha",
    }
    assert state["action"] == "upload"
    assert "keema" in state["raw_text"]
