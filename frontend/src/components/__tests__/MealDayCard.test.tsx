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
  kind: "swap" as const,
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
      pendingMeal={null}
      mealSuggestion={null}
      onAcceptSuggestion={vi.fn()}
      onRejectSuggestion={vi.fn()}
      isAccepting={false}
      {...props}
    />
  );
}

describe("MealDayCard swap button", () => {
  it("renders the suggestion overlay without an in-flight flag", () => {
    renderCard({ mealSuggestion: SUGGESTION, pendingMeal: null });
    expect(screen.getByText("Paneer Wrap")).toBeInTheDocument();
  });

  it("leaves the swap button enabled while a suggestion is showing", () => {
    renderCard({ mealSuggestion: SUGGESTION, pendingMeal: null });
    expect(screen.getByLabelText("Swap this meal")).toBeEnabled();
  });

  it("disables the swap button only while the request is in flight", () => {
    renderCard({ pendingMeal: { day: "Monday", mealSlot: "lunch" } });
    expect(screen.getByLabelText("Swap this meal")).toBeDisabled();
  });

  it("re-triggers onSwapMeal when clicked after a suggestion is showing", async () => {
    const onSwapMeal = vi.fn();
    renderCard({ mealSuggestion: SUGGESTION, pendingMeal: null, onSwapMeal });

    await userEvent.click(screen.getByLabelText("Swap this meal"));

    expect(onSwapMeal).toHaveBeenCalledWith("Monday", "lunch", "Dal Rice");
  });

  it("does not show another day's suggestion", () => {
    renderCard({ mealSuggestion: { ...SUGGESTION, day: "Tuesday" } });
    expect(screen.queryByText("Paneer Wrap")).not.toBeInTheDocument();
  });
});

describe("MealDayCard breakfast", () => {
  const LUNCH = {
    day: "Monday", meal_slot: "lunch", dish: "Dal Rice",
    prep_time_min: 30, reason: "new", ingredients: ["dal"],
  };
  const BREAKFAST = {
    day: "Monday", meal_slot: "breakfast", dish: "Poha",
    prep_time_min: 15, reason: "new", ingredients: ["flattened rice"],
  };

  it("offers the breakfast trigger on a day without one", () => {
    render(
      <MealDayCard day="Monday" meals={[LUNCH]} index={0} onAddBreakfast={vi.fn()} />
    );

    expect(screen.getByLabelText("Add breakfast")).toBeInTheDocument();
  });

  it("hides the breakfast trigger once the day has a breakfast", () => {
    // Review Focus 5: no second insert is offered.
    render(
      <MealDayCard
        day="Monday"
        meals={[BREAKFAST, LUNCH]}
        index={0}
        onAddBreakfast={vi.fn()}
      />
    );

    expect(screen.queryByLabelText("Add breakfast")).not.toBeInTheDocument();
  });

  it("calls onAddBreakfast with the day", async () => {
    const onAddBreakfast = vi.fn();
    const user = userEvent.setup();
    render(
      <MealDayCard day="Monday" meals={[LUNCH]} index={0} onAddBreakfast={onAddBreakfast} />
    );

    await user.click(screen.getByLabelText("Add breakfast"));

    expect(onAddBreakfast).toHaveBeenCalledWith("Monday");
  });

  it("shows a remove control only on the breakfast row", () => {
    render(
      <MealDayCard
        day="Monday"
        meals={[BREAKFAST, LUNCH]}
        index={0}
        onRemoveBreakfast={vi.fn()}
      />
    );

    expect(screen.getAllByLabelText("Remove breakfast")).toHaveLength(1);
  });

  it("renders a breakfast suggestion above the day's meals", () => {
    render(
      <MealDayCard
        day="Monday"
        meals={[LUNCH]}
        index={0}
        mealSuggestion={{
          kind: "breakfast",
          day: "Monday",
          mealSlot: "breakfast",
          suggestedMeal: BREAKFAST,
        }}
        onAcceptSuggestion={vi.fn()}
        onRejectSuggestion={vi.fn()}
      />
    );

    const overlay = screen.getByText("Poha");
    const lunch = screen.getByText("Dal Rice");
    expect(overlay.compareDocumentPosition(lunch)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );
  });

  it("does not render another day's breakfast suggestion", () => {
    render(
      <MealDayCard
        day="Tuesday"
        meals={[{ ...LUNCH, day: "Tuesday" }]}
        index={0}
        mealSuggestion={{
          kind: "breakfast",
          day: "Monday",
          mealSlot: "breakfast",
          suggestedMeal: BREAKFAST,
        }}
        onAcceptSuggestion={vi.fn()}
        onRejectSuggestion={vi.fn()}
      />
    );

    expect(screen.queryByText("Poha")).not.toBeInTheDocument();
  });

  it("spins the trigger while a breakfast request is in flight", () => {
    const { container } = render(
      <MealDayCard
        day="Monday"
        meals={[LUNCH]}
        index={0}
        onAddBreakfast={vi.fn()}
        pendingMeal={{ day: "Monday", mealSlot: "breakfast" }}
      />
    );

    expect(screen.getByLabelText("Add breakfast")).toBeDisabled();
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });
});
