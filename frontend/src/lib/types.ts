export interface MealEntry {
  day: string;
  dishes: string[];
  quantity: number;
  prep_notes: string;
  tags: string[];
  original_text: string;
}

export interface PlannedMeal {
  day: string;
  meal_slot: string;
  dish: string;
  prep_time_min: number;
  reason: string;
  ingredients: string[];
}

export interface GroceryItem {
  name: string;
  quantity: string;
  category: string;
  used_in: string[];
}

export interface UploadResponse {
  status: string;
  meals_indexed: number;
  parsed_meals: MealEntry[];
}

export interface MealPlanResponse {
  meal_plan: PlannedMeal[];
  grocery_list: GroceryItem[];
  validation_status: string;
  validation_warnings: string[];
  shopping_validation_status: string;
}

export interface SwapSingleMealResponse {
  suggestion: PlannedMeal;
  validation_status: string;
  validation_warnings: string[];
}

export interface MealHistoryResponse {
  meals: { id: string; document: string; metadata: Record<string, string> }[];
  total: number;
}

export type AppState =
  | "idle"
  | "uploading"
  | "ready"
  | "generating"
  | "plan_ready"
  | "swapping"
  | "approved"
  | "error";
