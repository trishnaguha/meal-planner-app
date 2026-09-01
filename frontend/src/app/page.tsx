"use client";

import { useState } from "react";
import Header from "@/components/Header";
import MealHistoryPanel from "@/components/MealHistoryPanel";
import MealPlanPanel from "@/components/MealPlanPanel";
import ShoppingListPanel from "@/components/ShoppingListPanel";
import { useMealPlan } from "@/hooks/useMealPlan";
import { AppState } from "@/lib/types";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("idle");
  const {
    mealPlan,
    groceryList,
    validationWarnings,
    generate,
    swap,
    approve,
    isLoading,
  } = useMealPlan();

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

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <MealHistoryPanel onUploadComplete={handleUploadComplete} />
          </div>
          <div className="lg:col-span-2">
            <MealPlanPanel
              mealPlan={mealPlan}
              appState={appState}
              validationWarnings={validationWarnings}
              onGenerate={handleGenerate}
              onSwap={handleSwap}
              onApprove={handleApprove}
            />
          </div>
        </div>
        <div className="mt-6">
          <ShoppingListPanel groceryList={groceryList} appState={appState} />
        </div>
      </main>
    </div>
  );
}
