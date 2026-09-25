import { Star, Clock, RefreshCw, Loader2, Plus, X } from "lucide-react";
import { MealSuggestion, PlannedMeal } from "@/lib/types";
import SwapSuggestion from "./SwapSuggestion";

interface Props {
  day: string;
  meals: PlannedMeal[];
  index: number;
  onSwapMeal?: (day: string, mealSlot: string, currentDish: string) => void;
  mealSuggestion?: MealSuggestion | null;
  pendingMeal?: { day: string; mealSlot: string } | null;
  onAcceptSuggestion?: () => void;
  onRejectSuggestion?: () => void;
  onAddBreakfast?: (day: string) => void;
  onRemoveBreakfast?: (day: string) => void;
  isAccepting?: boolean;
}

const SLOT_LABELS: Record<string, { short: string; color: string }> = {
  breakfast: { short: "B", color: "#eab308" },
  lunch: { short: "L", color: "#f97316" },
  dinner: { short: "D", color: "#ef4444" },
};

export default function MealDayCard({
  day,
  meals,
  index,
  onSwapMeal,
  mealSuggestion,
  pendingMeal,
  onAcceptSuggestion,
  onRejectSuggestion,
  onAddBreakfast,
  onRemoveBreakfast,
  isAccepting = false,
}: Props) {
  const hasBreakfast = meals.some((m) => m.meal_slot === "breakfast");
  const isAddingBreakfast =
    pendingMeal?.day === day && pendingMeal?.mealSlot === "breakfast";
  const breakfastSuggestion =
    mealSuggestion?.kind === "breakfast" && mealSuggestion.day === day
      ? mealSuggestion
      : null;

  return (
    <div
      className="spice-strip rounded-xl p-3.5 pl-4 transition-all duration-300 animate-fade-in-up overflow-hidden"
      style={{
        background: "var(--glass-bg)",
        animationDelay: `${index * 60}ms`,
      }}
    >
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <h3
          className="font-semibold text-sm tracking-tight"
          style={{ color: "var(--text-primary)" }}
        >
          {day}
        </h3>
        {!hasBreakfast && onAddBreakfast && (
          <button
            onClick={() => onAddBreakfast(day)}
            disabled={isAddingBreakfast}
            className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg hover:bg-white/5 transition-colors shrink-0"
            style={{ color: "var(--text-tertiary)" }}
            aria-label="Add breakfast"
          >
            {isAddingBreakfast ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Plus className="w-3 h-3" />
            )}
            Breakfast
          </button>
        )}
      </div>
      {breakfastSuggestion && onAcceptSuggestion && onRejectSuggestion && (
        <div className="mb-2">
          <SwapSuggestion
            meal={breakfastSuggestion.suggestedMeal}
            onAccept={onAcceptSuggestion}
            onReject={onRejectSuggestion}
            isAccepting={isAccepting}
          />
        </div>
      )}
      <div className="space-y-2">
        {meals.map((meal, i) => {
          const slot = SLOT_LABELS[meal.meal_slot] || {
            short: meal.meal_slot[0]?.toUpperCase() || "?",
            color: "var(--text-tertiary)",
          };
          const isSwapping =
            pendingMeal?.day === day &&
            pendingMeal?.mealSlot === meal.meal_slot;
          return (
            <div key={i}>
              <div className="flex items-start gap-2.5 text-sm group">
                <span
                  className="text-[10px] font-bold w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5"
                  style={{
                    background: `${slot.color}15`,
                    color: slot.color,
                  }}
                >
                  {slot.short}
                </span>
                <span
                  className="flex-1 leading-snug"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {meal.dish}
                  {meal.reason === "from history" && (
                    <Star className="inline w-3 h-3 ml-1 text-amber-400 fill-amber-400" />
                  )}
                </span>
                <span
                  className="flex items-center gap-0.5 text-[11px] shrink-0 mt-0.5"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  <Clock className="w-3 h-3" />
                  {meal.prep_time_min}m
                </span>
                {onSwapMeal && (
                  <button
                    onClick={() =>
                      onSwapMeal(day, meal.meal_slot, meal.dish)
                    }
                    disabled={isSwapping}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-white/5 shrink-0"
                    aria-label="Swap this meal"
                  >
                    {isSwapping ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                  </button>
                )}
                {meal.meal_slot === "breakfast" && onRemoveBreakfast && (
                  <button
                    onClick={() => onRemoveBreakfast(day)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-white/5 shrink-0"
                    aria-label="Remove breakfast"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              {mealSuggestion?.kind === "swap" &&
                mealSuggestion.day === day &&
                mealSuggestion.mealSlot === meal.meal_slot &&
                onAcceptSuggestion &&
                onRejectSuggestion && (
                  <SwapSuggestion
                    meal={mealSuggestion.suggestedMeal}
                    onAccept={onAcceptSuggestion}
                    onReject={onRejectSuggestion}
                    isAccepting={isAccepting}
                  />
                )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
