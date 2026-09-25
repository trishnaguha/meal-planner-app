import { Check, X, Clock } from "lucide-react";
import { PlannedMeal } from "@/lib/types";

interface Props {
  meal: PlannedMeal;
  onAccept: () => void;
  onReject: () => void;
  isAccepting: boolean;
}

export default function SwapSuggestion({
  meal,
  onAccept,
  onReject,
  isAccepting,
}: Props) {
  return (
    <div
      className="mt-2 p-3 rounded-lg animate-fade-in-up"
      style={{
        background: "var(--accent-glow)",
        border: "1px solid var(--accent)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p
            className="text-sm font-medium mb-1"
            style={{ color: "var(--text-primary)" }}
          >
            {meal.dish}
          </p>
          <div
            className="flex items-center gap-1.5 text-xs mb-2"
            style={{ color: "var(--text-tertiary)" }}
          >
            <Clock className="w-3 h-3" />
            {meal.prep_time_min}m
          </div>
          <p
            className="text-xs leading-relaxed mb-2"
            style={{ color: "var(--text-secondary)" }}
          >
            {meal.ingredients.slice(0, 3).join(", ")}
            {meal.ingredients.length > 3 && "..."}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={onAccept}
            disabled={isAccepting}
            className="btn-success p-2 rounded-lg min-h-[36px] min-w-[36px] flex items-center justify-center"
            aria-label="Accept suggestion"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={onReject}
            disabled={isAccepting}
            className="btn-glass p-2 rounded-lg min-h-[36px] min-w-[36px] flex items-center justify-center"
            aria-label="Reject suggestion"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
