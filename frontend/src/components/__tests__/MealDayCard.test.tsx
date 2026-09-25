import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MealDayCard from "@/components/MealDayCard";
import type { PlannedMeal } from "@/lib/types";

const MEALS: PlannedMeal[] = [
  {
    day: "Monday",
    meal_slot: "lunch",
    dish: "Dal Rice",
    prep_time_min: 30,
    reason: "new",
    ingredients: ["dal", "rice"],
  },
];

const SUGGESTION = {
  day: "Monday",
  mealSlot: "lunch",
  originalMeal: MEALS[0],
  suggestedMeal: {
    day: "Monday",
    meal_slot: "lunch",
    dish: "Paneer Wrap",
    prep_time_min: 25,
    reason: "new",
    ingredients: ["paneer", "roti", "onion"],
  },
};

function renderCard(props: Partial<React.ComponentProps<typeof MealDayCard>> = {}) {
  return render(
    <MealDayCard
      day="Monday"
      meals={MEALS}
      index={0}
      onSwapMeal={vi.fn()}
      swappingMeal={null}
      swapSuggestion={null}
      onAcceptSwap={vi.fn()}
      onRejectSwap={vi.fn()}
      isAccepting={false}
      {...props}
    />
  );
}

describe("MealDayCard swap button", () => {
  it("renders the suggestion overlay without an in-flight flag", () => {
    renderCard({ swapSuggestion: SUGGESTION, swappingMeal: null });
    expect(screen.getByText("Paneer Wrap")).toBeInTheDocument();
  });

  it("leaves the swap button enabled while a suggestion is showing", () => {
    renderCard({ swapSuggestion: SUGGESTION, swappingMeal: null });
    expect(screen.getByLabelText("Swap this meal")).toBeEnabled();
  });

  it("disables the swap button only while the request is in flight", () => {
    renderCard({ swappingMeal: { day: "Monday", mealSlot: "lunch" } });
    expect(screen.getByLabelText("Swap this meal")).toBeDisabled();
  });

  it("re-triggers onSwapMeal when clicked after a suggestion is showing", async () => {
    const onSwapMeal = vi.fn();
    renderCard({ swapSuggestion: SUGGESTION, swappingMeal: null, onSwapMeal });

    await userEvent.click(screen.getByLabelText("Swap this meal"));

    expect(onSwapMeal).toHaveBeenCalledWith("Monday", "lunch", "Dal Rice");
  });

  it("does not show another day's suggestion", () => {
    renderCard({ swapSuggestion: { ...SUGGESTION, day: "Tuesday" } });
    expect(screen.queryByText("Paneer Wrap")).not.toBeInTheDocument();
  });
});
