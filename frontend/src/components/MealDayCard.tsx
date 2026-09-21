import { Star, Clock } from "lucide-react";
import { PlannedMeal } from "@/lib/types";

interface Props {
  day: string;
  meals: PlannedMeal[];
  index: number;
}

const SLOT_LABELS: Record<string, { short: string; color: string }> = {
  lunch: { short: "L", color: "#f97316" },
  dinner: { short: "D", color: "#ef4444" },
};

export default function MealDayCard({ day, meals, index }: Props) {
  return (
    <div
      className="spice-strip rounded-xl p-3.5 pl-4 transition-all duration-300 animate-fade-in-up overflow-hidden"
      style={{
        background: "var(--glass-bg)",
        animationDelay: `${index * 60}ms`,
      }}
    >
      <h3
        className="font-semibold text-sm mb-2.5 tracking-tight"
        style={{ color: "var(--text-primary)" }}
      >
        {day}
      </h3>
      <div className="space-y-2">
        {meals.map((meal, i) => {
          const slot = SLOT_LABELS[meal.meal_slot] || {
            short: meal.meal_slot[0]?.toUpperCase() || "?",
            color: "var(--text-tertiary)",
          };
          return (
            <div key={i} className="flex items-start gap-2.5 text-sm group">
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
            </div>
          );
        })}
      </div>
    </div>
  );
}
