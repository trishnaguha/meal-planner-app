"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { PlannedMeal, GroceryItem } from "@/lib/types";

export function useMealPlan() {
  const [mealPlan, setMealPlan] = useState<PlannedMeal[]>([]);
  const [groceryList, setGroceryList] = useState<GroceryItem[]>([]);
  const [validationStatus, setValidationStatus] = useState("");
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [swapSuggestion, setSwapSuggestion] = useState<{
    day: string;
    mealSlot: string;
    originalMeal: PlannedMeal;
    suggestedMeal: PlannedMeal;
  } | null>(null);
  const [swappingMeal, setSwappingMeal] = useState<{
    day: string;
    mealSlot: string;
  } | null>(null);

  const generate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.generatePlan();
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      setValidationStatus(data.validation_status);
      setValidationWarnings(data.validation_warnings || []);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate plan");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const swap = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const excludedDishes = mealPlan.map((m) => m.dish);
      const data = await api.swapMeal(excludedDishes);
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      setValidationStatus(data.validation_status);
      setValidationWarnings(data.validation_warnings || []);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to swap plan");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const approve = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.approvePlan();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve plan");
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const swapSingleMeal = async (
    day: string,
    mealSlot: string,
    currentDish: string
  ) => {
    setSwappingMeal({ day, mealSlot });
    setSwapSuggestion(null);
    setError(null);
    try {
      const data = await api.swapSingleMeal(day, mealSlot, currentDish);
      const originalMeal = mealPlan.find(
        (m) => m.day === day && m.meal_slot === mealSlot
      );
      if (originalMeal) {
        setSwapSuggestion({
          day,
          mealSlot,
          originalMeal,
          suggestedMeal: data.suggestion,
        });
      }
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to swap meal");
      setSwappingMeal(null);
      return null;
    }
  };

  const acceptSwap = async () => {
    if (!swapSuggestion) return false;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.acceptSwap(
        swapSuggestion.day,
        swapSuggestion.mealSlot,
        swapSuggestion.suggestedMeal
      );
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      setValidationStatus(data.validation_status);
      setValidationWarnings(data.validation_warnings || []);
      setSwapSuggestion(null);
      setSwappingMeal(null);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept swap");
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const rejectSwap = () => {
    setSwapSuggestion(null);
  };

  return {
    mealPlan,
    groceryList,
    validationStatus,
    validationWarnings,
    generate,
    swap,
    approve,
    isLoading,
    error,
    swapSingleMeal,
    acceptSwap,
    rejectSwap,
    swapSuggestion,
    swappingMeal,
  };
}
