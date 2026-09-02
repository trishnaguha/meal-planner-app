"use client";

import { Loader2, Sparkles, CalendarDays } from "lucide-react";
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

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

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
    <div className="glass rounded-2xl p-5 animate-fade-in-up delay-100">
      <h2
        className="text-base font-semibold mb-4 flex items-center gap-2"
        style={{ color: "var(--text-primary)" }}
      >
        <span
          className="w-1.5 h-5 rounded-full"
          style={{
            background: "linear-gradient(180deg, var(--accent), var(--accent-end))",
          }}
        />
        Next Week
      </h2>

      {appState === "idle" && (
        <div className="text-center py-16 animate-fade-in-up">
          <CalendarDays
            className="w-12 h-12 mx-auto mb-4"
            style={{ color: "var(--text-tertiary)" }}
          />
          <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
            Upload your meal history to get started
          </p>
        </div>
      )}

      {appState === "ready" && (
        <div className="text-center py-16 animate-scale-in">
          <p className="text-sm mb-5" style={{ color: "var(--text-secondary)" }}>
            History loaded. Ready to plan your week.
          </p>
          <button
            onClick={onGenerate}
            className="btn-accent inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm"
          >
            <Sparkles className="w-4 h-4" />
            Generate Meal Plan
          </button>
        </div>
      )}

      {isLoadingState && (
        <div className="text-center py-16 animate-fade-in-up">
          <div
            className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center loading-gradient"
          >
            <Loader2 className="w-5 h-5 animate-spin text-white" />
          </div>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {appState === "swapping"
              ? "Finding alternatives..."
              : "Crafting your meal plan..."}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
            This may take a moment
          </p>
        </div>
      )}

      {(appState === "plan_ready" || appState === "approved") &&
        groupedByDay.length > 0 && (
          <>
            <div className="space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
              {groupedByDay.map(({ day, meals }, index) => (
                <MealDayCard key={day} day={day} meals={meals} index={index} />
              ))}
            </div>

            {validationWarnings && validationWarnings.length > 0 && (
              <div className="mt-3 space-y-1">
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
        <div className="text-center py-16 animate-fade-in-up">
          <StatusIndicator
            status="error"
            message="Something went wrong"
          />
          <button
            onClick={onGenerate}
            className="btn-accent mt-4 px-5 py-2 rounded-xl text-sm"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}
