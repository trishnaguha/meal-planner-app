import { Star, Clock } from "lucide-react";
import { PlannedMeal } from "@/lib/types";

interface Props {
  day: string;
  meals: PlannedMeal[];
}

const SLOT_LABELS: Record<string, string> = {
  breakfast: "B",
  lunch: "L",
  dinner: "D",
};

export default function MealDayCard({ day, meals }: Props) {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
      <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-2">
        {day}
      </h3>
      <div className="space-y-1.5">
        {meals.map((meal, i) => (
          <div key={i} className="flex items-start gap-2 text-sm">
            <span className="font-mono text-xs text-gray-400 w-4 shrink-0 mt-0.5">
              {SLOT_LABELS[meal.meal_slot] || meal.meal_slot[0]?.toUpperCase()}
            </span>
            <span className="text-gray-700 dark:text-gray-300 flex-1">
              {meal.dish}
              {meal.reason === "past favorite" && (
                <Star className="inline w-3.5 h-3.5 ml-1 text-amber-400 fill-amber-400" />
              )}
            </span>
            <span className="flex items-center gap-0.5 text-xs text-gray-400 shrink-0">
              <Clock className="w-3 h-3" />
              {meal.prep_time_min}m
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
