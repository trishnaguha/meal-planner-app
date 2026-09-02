import pytest


@pytest.fixture
def sample_meal_entry():
    return {
        "day": "Saturday",
        "dishes": ["keema paratha", "cabbage"],
        "quantity": 5,
        "prep_notes": "Make cabbage",
        "tags": ["indian", "paratha", "protein", "vegetable"],
        "original_text": "Saturday 5 keema paratha. Make cabbage",
    }


@pytest.fixture
def sample_planned_meal():
    return {
        "day": "Monday",
        "meal_slot": "lunch",
        "dish": "keema paratha",
        "prep_time_min": 30,
        "reason": "past favorite",
        "ingredients": ["ground meat", "flour", "onion", "spices"],
    }


@pytest.fixture
def sample_grocery_item():
    return {
        "name": "ground meat",
        "quantity": "1 kg",
        "category": "protein",
        "used_in": ["keema paratha"],
    }
