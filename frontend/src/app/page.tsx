"use client";

import { useState, useEffect } from "react";
import Header from "@/components/Header";
import MealHistoryPanel from "@/components/MealHistoryPanel";
import PreferencesPanel from "@/components/PreferencesPanel";
import MealPlanPanel from "@/components/MealPlanPanel";
import ShoppingListPanel from "@/components/ShoppingListPanel";
import { useMealPlan } from "@/hooks/useMealPlan";
import { api } from "@/lib/api";
import { AppState, PlannedMeal } from "@/lib/types";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [existingMealCount, setExistingMealCount] = useState(0);
  const [isAccepting, setIsAccepting] = useState(false);
  const {
    mealPlan,
    groceryList,
    validationWarnings,
    generate,
    swap,
    approve,
    swapSingleMeal,
    suggestBreakfast,
    removeBreakfast,
    acceptSuggestion,
    rejectSuggestion,
    mealSuggestion,
    pendingMeal,
    error,
  } = useMealPlan();

  useEffect(() => {
    api.getMealHistory().then((data) => {
      if (data.total > 0) {
        setExistingMealCount(data.total);
        setAppState("ready");
      }
    }).catch(() => {});
  }, []);

  const handleUploadComplete = () => {
    setAppState("ready");
  };

  const handleGenerate = async () => {
    setAppState("generating");
    const result = await generate();
    setAppState(result ? "plan_ready" : "error");
  };

  const handleSwap = async () => {
    setAppState("swapping");
    const result = await swap();
    setAppState(result ? "plan_ready" : "error");
  };

  const handleApprove = async () => {
    const success = await approve();
    if (success) setAppState("approved");
  };

  const handleSwapSingleMeal = async (
    day: string,
    mealSlot: string,
    currentDish: string
  ) => {
    await swapSingleMeal(day, mealSlot, currentDish);
  };

  const handleAddBreakfast = async (day: string) => {
    await suggestBreakfast(day);
  };

  const handleRemoveBreakfast = async (day: string) => {
    await removeBreakfast(day);
  };

  const handleAcceptSuggestion = async () => {
    setIsAccepting(true);
    await acceptSuggestion();
    setIsAccepting(false);
  };

  const handleRejectSuggestion = () => {
    rejectSuggestion();
  };

  return (
    <div className="min-h-screen min-h-dvh flex flex-col relative">
      {/* Ambient gradient orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div
          className="absolute w-[500px] h-[500px] rounded-full blur-[120px] opacity-20"
          style={{
            background: "var(--accent)",
            top: "-10%",
            right: "-5%",
          }}
        />
        <div
          className="absolute w-[400px] h-[400px] rounded-full blur-[120px] opacity-10"
          style={{
            background: "var(--accent-end)",
            bottom: "10%",
            left: "-5%",
          }}
        />
      </div>

      <Header />

      <main className="flex-1 px-4 sm:px-6 py-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-4 xl:col-span-3">
            <MealHistoryPanel onUploadComplete={handleUploadComplete} existingMealCount={existingMealCount} />
            <div className="mt-5">
              <PreferencesPanel />
            </div>
          </div>
          <div className="lg:col-span-8 xl:col-span-9">
            <MealPlanPanel
              mealPlan={mealPlan}
              appState={appState}
              validationWarnings={validationWarnings}
              onGenerate={handleGenerate}
              onSwap={handleSwap}
              onApprove={handleApprove}
              onSwapMeal={handleSwapSingleMeal}
              pendingMeal={pendingMeal}
              mealSuggestion={mealSuggestion}
              onAcceptSuggestion={handleAcceptSuggestion}
              onRejectSuggestion={handleRejectSuggestion}
              onAddBreakfast={handleAddBreakfast}
              onRemoveBreakfast={handleRemoveBreakfast}
              isAccepting={isAccepting}
              swapError={error}
            />
          </div>
        </div>

        <div className="mt-5">
          <ShoppingListPanel groceryList={groceryList} appState={appState} />
        </div>
      </main>
    </div>
  );
}
