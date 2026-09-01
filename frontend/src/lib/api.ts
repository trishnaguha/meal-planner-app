import axios from "axios";
import {
  UploadResponse,
  MealPlanResponse,
  MealHistoryResponse,
} from "./types";

const client = axios.create({ baseURL: "/api" });

export const api = {
  async uploadMeals(formData: FormData): Promise<UploadResponse> {
    const { data } = await client.post<UploadResponse>(
      "/upload-meals",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  async generatePlan(): Promise<MealPlanResponse> {
    const { data } = await client.post<MealPlanResponse>("/generate-plan");
    return data;
  },

  async swapMeal(excludedDishes: string[]): Promise<MealPlanResponse> {
    const { data } = await client.post<MealPlanResponse>("/swap-meal", {
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
};
