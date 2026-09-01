"use client";

import { Loader2, Sparkles } from "lucide-react";
import MealDayCard from "./MealDayCard";
import ActionButtons from "./ActionButtons";
import StatusIndicator from "./StatusIndicator";
import { PlannedMeal, AppState } from "@/lib/types";

interface Props {
  mealPlan: PlannedMeal[];
  appState: AppState;
  validationWarnings?: string[];
  onGenerate: () => void;
  onSwap: () => void;
  onApprove: () => void;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function MealPlanPanel({
  mealPlan,
  appState,
  validationWarnings,
  onGenerate,
  onSwap,
  onApprove,
}: Props) {
  const groupedByDay = DAYS.map((day) => ({
    day,
    meals: mealPlan.filter((m) => m.day === day),
  })).filter((g) => g.meals.length > 0);

  const isLoadingState = appState === "generating" || appState === "swapping";

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Next Week Meal Plan
      </h2>

      {appState === "idle" && (
        <div className="text-center py-12 text-gray-500">
          <p>Upload your meal history to get started</p>
        </div>
      )}

      {appState === "ready" && (
        <div className="text-center py-12">
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Ready! Click Generate to create your meal plan
          </p>
          <button
            onClick={onGenerate}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Generate Meal Plan
          </button>
        </div>
      )}

      {isLoadingState && (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mx-auto mb-3" />
          <p className="text-gray-500">
            {appState === "swapping" ? "Regenerating plan..." : "Generating your meal plan..."}
          </p>
        </div>
      )}

      {(appState === "plan_ready" || appState === "approved") && groupedByDay.length > 0 && (
        <>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {groupedByDay.map(({ day, meals }) => (
              <MealDayCard key={day} day={day} meals={meals} />
            ))}
          </div>

          {validationWarnings && validationWarnings.length > 0 && (
            <div className="mt-3">
              {validationWarnings.map((w, i) => (
                <StatusIndicator key={i} status="error" message={w} />
              ))}
            </div>
          )}

          <div className="mt-4">
            <ActionButtons
              onApprove={onApprove}
              onSwap={onSwap}
              disabled={isLoadingState}
              approved={appState === "approved"}
            />
          </div>
        </>
      )}

      {appState === "error" && (
        <div className="text-center py-12">
          <StatusIndicator status="error" message="Something went wrong. Please try again." />
          <button
            onClick={onGenerate}
            className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
