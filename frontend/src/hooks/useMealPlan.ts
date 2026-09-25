"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { PlannedMeal, GroceryItem, MealSuggestion } from "@/lib/types";

export function useMealPlan() {
  const [mealPlan, setMealPlan] = useState<PlannedMeal[]>([]);
  const [groceryList, setGroceryList] = useState<GroceryItem[]>([]);
  const [validationStatus, setValidationStatus] = useState("");
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mealSuggestion, setMealSuggestion] = useState<MealSuggestion | null>(null);
  const [pendingMeal, setPendingMeal] = useState<{
    day: string;
    mealSlot: string;
  } | null>(null);
  const swapRequestId = useRef(0);

  // A whole-plan change invalidates any per-meal suggestion — it was computed
  // against a plan that no longer exists — and any per-meal request still in
  // flight, whose response would otherwise land on the new plan.
  const invalidatePendingSuggestion = () => {
    swapRequestId.current += 1;
    setMealSuggestion(null);
    setPendingMeal(null);
  };

  const generate = async () => {
    invalidatePendingSuggestion();
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
    invalidatePendingSuggestion();
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
    const requestId = ++swapRequestId.current;
    setPendingMeal({ day, mealSlot });
    setMealSuggestion(null);
    setError(null);
    try {
      const data = await api.swapSingleMeal(day, mealSlot, currentDish);
      if (requestId !== swapRequestId.current) return null;
      const originalMeal = mealPlan.find(
        (m) => m.day === day && m.meal_slot === mealSlot
      );
      if (originalMeal) {
        setMealSuggestion({
          kind: "swap",
          day,
          mealSlot,
          originalMeal,
          suggestedMeal: data.suggestion,
        });
      }
      return data;
    } catch (err) {
      if (requestId !== swapRequestId.current) return null;
      setError(err instanceof Error ? err.message : "Failed to swap meal");
      return null;
    } finally {
      if (requestId === swapRequestId.current) {
        setPendingMeal(null);
      }
    }
  };

  const suggestBreakfast = async (day: string) => {
    const requestId = ++swapRequestId.current;
    setPendingMeal({ day, mealSlot: "breakfast" });
    setMealSuggestion(null);
    setError(null);
    try {
      const data = await api.suggestBreakfast(day);
      if (requestId !== swapRequestId.current) return null;
      setMealSuggestion({
        kind: "breakfast",
        day,
        mealSlot: "breakfast",
        suggestedMeal: data.suggestion,
      });
      // The Validator gated this suggestion; a verdict the user never sees is
      // a gate that did not run for them.
      setValidationWarnings(
        data.validation_status === "passed" ? [] : data.validation_warnings || []
      );
      return data;
    } catch (err) {
      if (requestId !== swapRequestId.current) return null;
      setError(err instanceof Error ? err.message : "Failed to suggest breakfast");
      return null;
    } finally {
      if (requestId === swapRequestId.current) {
        setPendingMeal(null);
      }
    }
  };

  const acceptSuggestion = async () => {
    if (!mealSuggestion) return false;
    const requestId = ++swapRequestId.current;
    setIsLoading(true);
    setError(null);
    try {
      const data =
        mealSuggestion.kind === "breakfast"
          ? await api.acceptBreakfast(mealSuggestion.day, mealSuggestion.suggestedMeal)
          : await api.acceptSwap(
              mealSuggestion.day,
              mealSuggestion.mealSlot,
              mealSuggestion.suggestedMeal
            );
      // The server response is authoritative about the plan itself, so it
      // lands even when this accept has been superseded.
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      // These endpoints re-validate the shopping list only; the plan-level
      // warnings belong to the plan that just changed, so clear them.
      setValidationWarnings([]);
      // The suggestion slot, though, may already hold a newer suggestion.
      if (requestId === swapRequestId.current) {
        setMealSuggestion(null);
      }
      return true;
    } catch (err) {
      if (requestId === swapRequestId.current) {
        setError(err instanceof Error ? err.message : "Failed to accept suggestion");
      }
      return false;
    } finally {
      setIsLoading(false);
      if (requestId === swapRequestId.current) {
        setPendingMeal(null);
      }
    }
  };

  const removeBreakfast = async (day: string) => {
    invalidatePendingSuggestion();
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.removeBreakfast(day);
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove breakfast");
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const rejectSuggestion = () => {
    invalidatePendingSuggestion();
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
    suggestBreakfast,
    removeBreakfast,
    acceptSuggestion,
    rejectSuggestion,
    mealSuggestion,
    pendingMeal,
  };
}
