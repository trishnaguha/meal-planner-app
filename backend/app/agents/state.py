from typing import TypedDict, Literal


class MealEntry(TypedDict):
    day: str
    dishes: list[str]
    quantity: int
    prep_notes: str
    tags: list[str]
    original_text: str


class PlannedMeal(TypedDict):
    day: str
    meal_slot: str
    dish: str
    prep_time_min: int
    reason: str
    ingredients: list[str]


class GroceryItem(TypedDict):
    name: str
    quantity: str
    category: str
    used_in: list[str]


class MealPlannerState(TypedDict, total=False):
    raw_text: str
    uploaded_file_path: str | None
    input_source: Literal["paste", "file_upload"]
    file_type: str | None
    action: Literal["upload", "generate", "swap", "approve"]
    parsed_meals: list[MealEntry]
    embedding_status: str
    meal_plan: list[PlannedMeal]
    excluded_dishes: list[str]
    validation_status: Literal["passed", "failed", "passed_with_warnings"]
    validation_errors: list[str]
    validation_warnings: list[str]
    retry_count: int
    grocery_list: list[GroceryItem]
    shopping_validation_status: Literal["passed", "failed", "passed_with_warnings"]
    shopping_validation_errors: list[str]
    shopping_retry_count: int
