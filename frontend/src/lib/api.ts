import axios from "axios";
import {
  UploadResponse,
  MealPlanResponse,
  MealHistoryResponse,
  SwapSingleMealResponse,
  PlannedMeal,
} from "./types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const client = axios.create({ baseURL: "/api", timeout: 600_000 });
const directClient = axios.create({ baseURL: `${BACKEND_URL}/api`, timeout: 600_000 });

export const api = {
  async uploadMeals(formData: FormData): Promise<UploadResponse> {
    const { data } = await directClient.post<UploadResponse>(
      "/upload-meals",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  async generatePlan(): Promise<MealPlanResponse> {
    const { data } = await directClient.post<MealPlanResponse>("/generate-plan");
    return data;
  },

  async swapMeal(excludedDishes: string[]): Promise<MealPlanResponse> {
    const { data } = await directClient.post<MealPlanResponse>("/swap-meal", {
      excluded_dishes: excludedDishes,
    });
    return data;
  },

  async approvePlan(
    mealPlan?: Record<string, unknown>[]
  ): Promise<{ status: string; meals_saved: number }> {
    const { data } = await client.post("/approve-plan", {
      meal_plan: mealPlan,
    });
    return data;
  },

  async getMealHistory(): Promise<MealHistoryResponse> {
    const { data } = await client.get<MealHistoryResponse>("/meal-history");
    return data;
  },

  async getCurrentPlan(): Promise<MealPlanResponse> {
    const { data } = await client.get<MealPlanResponse>("/current-plan");
    return data;
  },

  async getShoppingList(): Promise<{
    grocery_list: import("./types").GroceryItem[];
    shopping_validation_status: string;
  }> {
    const { data } = await client.get("/shopping-list");
    return data;
  },

  async getPreferences(): Promise<{ dietary_preference?: string }> {
    const { data } = await client.get<{ dietary_preference?: string }>("/preferences");
    return data;
  },

  async savePreferences(dietary_preference: string): Promise<{ dietary_preference: string }> {
    const { data } = await client.post<{ dietary_preference: string }>("/preferences", {
      dietary_preference,
    });
    return data;
  },

  async swapSingleMeal(
    day: string,
    mealSlot: string,
    currentDish: string
  ): Promise<SwapSingleMealResponse> {
    const { data } = await directClient.post<SwapSingleMealResponse>(
      "/swap-single-meal",
      {
        day,
        meal_slot: mealSlot,
        current_dish: currentDish,
      },
      { timeout: 60_000 }
    );
    return data;
  },

  async acceptSwap(
    day: string,
    mealSlot: string,
    newMeal: PlannedMeal
  ): Promise<MealPlanResponse> {
    const { data } = await directClient.post<MealPlanResponse>(
      "/accept-swap",
      {
        day,
        meal_slot: mealSlot,
        new_meal: newMeal,
      },
      { timeout: 90_000 }
    );
    return data;
  },
};
