/**
 * End-to-end regression guard for the per-meal swap retry wedge.
 *
 * These render the real page with the real useMealPlan hook and real
 * components — only the HTTP layer is mocked. The hook and component unit
 * tests each hold one side of the seam; the reported bug lived in the seam
 * itself (the button was disabled, so the click never reached the hook).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Home from "@/app/page";
import { api } from "@/lib/api";
import type { MealPlanResponse, SwapSingleMealResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: {
    uploadMeals: vi.fn(),
    generatePlan: vi.fn(),
    swapMeal: vi.fn(),
    approvePlan: vi.fn(),
    getMealHistory: vi.fn(),
    getCurrentPlan: vi.fn(),
    getShoppingList: vi.fn(),
    getPreferences: vi.fn(),
    savePreferences: vi.fn(),
    swapSingleMeal: vi.fn(),
    acceptSwap: vi.fn(),
  },
}));

const PLAN_RESPONSE: MealPlanResponse = {
  meal_plan: [
    {
      day: "Monday",
      meal_slot: "lunch",
      dish: "Dal Rice",
      prep_time_min: 30,
      reason: "new",
      ingredients: ["dal", "rice"],
    },
  ],
  grocery_list: [],
  validation_status: "passed",
  validation_warnings: [],
  shopping_validation_status: "passed",
};

function suggestionResponse(dish: string): SwapSingleMealResponse {
  return {
    suggestion: {
      day: "Monday",
      meal_slot: "lunch",
      dish,
      prep_time_min: 25,
      reason: "new",
      ingredients: ["paneer", "onion"],
    },
    validation_status: "passed",
    validation_warnings: [],
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getMealHistory).mockResolvedValue({ meals: [], total: 12 });
  vi.mocked(api.getPreferences).mockResolvedValue({ dietary_preference: "" });
  vi.mocked(api.generatePlan).mockResolvedValue(PLAN_RESPONSE);
});

async function renderPlannedWeek(user: ReturnType<typeof userEvent.setup>) {
  render(<Home />);
  await user.click(
    await screen.findByRole("button", { name: "Generate Meal Plan" })
  );
  await screen.findByText("Dal Rice");
}

describe("per-meal swap, end to end", () => {
  it("re-triggers the swap request after the user rejects a suggestion", async () => {
    const user = userEvent.setup();
    vi.mocked(api.swapSingleMeal)
      .mockResolvedValueOnce(suggestionResponse("Paneer Wrap"))
      .mockResolvedValueOnce(suggestionResponse("Chana Masala"));

    await renderPlannedWeek(user);

    await user.click(screen.getByLabelText("Swap this meal"));
    await screen.findByText("Paneer Wrap");
    expect(api.swapSingleMeal).toHaveBeenCalledTimes(1);

    await user.click(screen.getByLabelText("Reject suggestion"));
    await waitFor(() =>
      expect(screen.queryByText("Paneer Wrap")).not.toBeInTheDocument()
    );

    // The reported bug: this click landed on a disabled button and sent nothing.
    await user.click(screen.getByLabelText("Swap this meal"));

    await screen.findByText("Chana Masala");
    expect(api.swapSingleMeal).toHaveBeenCalledTimes(2);
  });

  it("survives three reject-and-retry cycles", async () => {
    const user = userEvent.setup();
    vi.mocked(api.swapSingleMeal).mockImplementation(async () =>
      suggestionResponse(`Suggestion ${vi.mocked(api.swapSingleMeal).mock.calls.length}`)
    );

    await renderPlannedWeek(user);

    for (let cycle = 1; cycle <= 3; cycle++) {
      await user.click(screen.getByLabelText("Swap this meal"));
      await screen.findByText(`Suggestion ${cycle}`);
      await user.click(screen.getByLabelText("Reject suggestion"));
      await waitFor(() =>
        expect(screen.queryByText(`Suggestion ${cycle}`)).not.toBeInTheDocument()
      );
    }

    expect(api.swapSingleMeal).toHaveBeenCalledTimes(3);
  });

  it("tells the user when the swap request fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.swapSingleMeal).mockRejectedValue(new Error("Network Error"));

    await renderPlannedWeek(user);
    await user.click(screen.getByLabelText("Swap this meal"));

    expect(await screen.findByText("Network Error")).toBeInTheDocument();
  });

  it("clears the error message once a later swap succeeds", async () => {
    const user = userEvent.setup();
    vi.mocked(api.swapSingleMeal)
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce(suggestionResponse("Paneer Wrap"));

    await renderPlannedWeek(user);
    await user.click(screen.getByLabelText("Swap this meal"));
    await screen.findByText("Network Error");

    await user.click(screen.getByLabelText("Swap this meal"));

    await screen.findByText("Paneer Wrap");
    expect(screen.queryByText("Network Error")).not.toBeInTheDocument();
  });
});
