"use client";

import { useRef, useState } from "react";
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
  const swapRequestId = useRef(0);

  // A whole-plan change invalidates any per-meal suggestion — it was computed
  // against a plan that no longer exists — and any per-meal request still in
  // flight, whose response would otherwise land on the new plan.
  const invalidatePendingSwap = () => {
    swapRequestId.current += 1;
    setSwapSuggestion(null);
    setSwappingMeal(null);
  };

  const generate = async () => {
    invalidatePendingSwap();
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
    invalidatePendingSwap();
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
    setSwappingMeal({ day, mealSlot });
    setSwapSuggestion(null);
    setError(null);
    try {
      const data = await api.swapSingleMeal(day, mealSlot, currentDish);
      if (requestId !== swapRequestId.current) return null;
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
      if (requestId !== swapRequestId.current) return null;
      setError(err instanceof Error ? err.message : "Failed to swap meal");
      return null;
    } finally {
      if (requestId === swapRequestId.current) {
        setSwappingMeal(null);
      }
    }
  };

  const acceptSwap = async () => {
    if (!swapSuggestion) return false;
    const requestId = ++swapRequestId.current;
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
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept swap");
      return false;
    } finally {
      setIsLoading(false);
      if (requestId === swapRequestId.current) {
        setSwappingMeal(null);
      }
    }
  };

  const rejectSwap = () => {
    invalidatePendingSwap();
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
