import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useMealPlan } from "@/hooks/useMealPlan";
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

const PLAN = [
  {
    day: "Monday",
    meal_slot: "lunch",
    dish: "Dal Rice",
    prep_time_min: 30,
    reason: "new",
    ingredients: ["dal", "rice"],
  },
  {
    day: "Monday",
    meal_slot: "dinner",
    dish: "Roti Sabzi",
    prep_time_min: 40,
    reason: "new",
    ingredients: ["flour", "potato"],
  },
];

const PLAN_RESPONSE: MealPlanResponse = {
  meal_plan: PLAN,
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
      ingredients: ["paneer"],
    },
    validation_status: "passed",
    validation_warnings: [],
  };
}

async function renderWithPlan() {
  vi.mocked(api.generatePlan).mockResolvedValue(PLAN_RESPONSE);
  const { result } = renderHook(() => useMealPlan());
  await act(async () => {
    await result.current.generate();
  });
  return result;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useMealPlan per-meal swap", () => {
  it("clears the in-flight flag once a suggestion arrives", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal).mockResolvedValue(suggestionResponse("Paneer Wrap"));

    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });

    expect(result.current.swapSuggestion?.suggestedMeal.dish).toBe("Paneer Wrap");
    expect(result.current.swappingMeal).toBeNull();
  });

  it("clears the in-flight flag when the suggestion is rejected", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal).mockResolvedValue(suggestionResponse("Paneer Wrap"));

    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });
    act(() => {
      result.current.rejectSwap();
    });

    expect(result.current.swapSuggestion).toBeNull();
    expect(result.current.swappingMeal).toBeNull();
  });

  it("re-triggers the swap after a reject and returns a fresh suggestion", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal)
      .mockResolvedValueOnce(suggestionResponse("Paneer Wrap"))
      .mockResolvedValueOnce(suggestionResponse("Chana Masala"));

    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });
    act(() => {
      result.current.rejectSwap();
    });
    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });

    expect(api.swapSingleMeal).toHaveBeenCalledTimes(2);
    expect(result.current.swapSuggestion?.suggestedMeal.dish).toBe("Chana Masala");
    expect(result.current.swappingMeal).toBeNull();
  });

  it("clears the in-flight flag and sets error when the swap request fails", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal).mockRejectedValue(new Error("boom"));

    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });

    expect(result.current.swappingMeal).toBeNull();
    expect(result.current.error).toBe("boom");
  });

  it("keeps the suggestion and unwedges the slot when accept fails", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal).mockResolvedValue(suggestionResponse("Paneer Wrap"));
    vi.mocked(api.acceptSwap).mockRejectedValue(new Error("accept failed"));

    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });
    await act(async () => {
      await result.current.acceptSwap();
    });

    expect(result.current.swappingMeal).toBeNull();
    expect(result.current.swapSuggestion?.suggestedMeal.dish).toBe("Paneer Wrap");
    expect(result.current.error).toBe("accept failed");
  });

  it("clears both pieces of state on a successful accept", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal).mockResolvedValue(suggestionResponse("Paneer Wrap"));
    vi.mocked(api.acceptSwap).mockResolvedValue({
      ...PLAN_RESPONSE,
      meal_plan: [{ ...PLAN[0], dish: "Paneer Wrap" }, PLAN[1]],
    });

    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });
    await act(async () => {
      await result.current.acceptSwap();
    });

    expect(result.current.swapSuggestion).toBeNull();
    expect(result.current.swappingMeal).toBeNull();
    expect(result.current.mealPlan[0].dish).toBe("Paneer Wrap");
  });

  it("shows the in-flight flag while the request is pending", async () => {
    const result = await renderWithPlan();
    let resolveSwap: (v: SwapSingleMealResponse) => void = () => {};
    vi.mocked(api.swapSingleMeal).mockReturnValue(
      new Promise<SwapSingleMealResponse>((resolve) => {
        resolveSwap = resolve;
      })
    );

    act(() => {
      void result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });
    await waitFor(() => {
      expect(result.current.swappingMeal).toEqual({ day: "Monday", mealSlot: "lunch" });
    });

    await act(async () => {
      resolveSwap(suggestionResponse("Paneer Wrap"));
    });
    expect(result.current.swappingMeal).toBeNull();
  });

  it("ignores a stale response when a second slot swap supersedes the first", async () => {
    const result = await renderWithPlan();

    let resolveFirst: (v: SwapSingleMealResponse) => void = () => {};
    let resolveSecond: (v: SwapSingleMealResponse) => void = () => {};
    vi.mocked(api.swapSingleMeal)
      .mockReturnValueOnce(
        new Promise<SwapSingleMealResponse>((r) => {
          resolveFirst = r;
        })
      )
      .mockReturnValueOnce(
        new Promise<SwapSingleMealResponse>((r) => {
          resolveSecond = r;
        })
      );

    act(() => {
      void result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });
    act(() => {
      void result.current.swapSingleMeal("Monday", "dinner", "Roti Sabzi");
    });

    // The superseded first request settles last.
    await act(async () => {
      resolveFirst(suggestionResponse("Stale Dish"));
    });

    // Still waiting on the dinner request, so the dinner slot keeps its spinner.
    expect(result.current.swappingMeal).toEqual({ day: "Monday", mealSlot: "dinner" });
    expect(result.current.swapSuggestion).toBeNull();

    await act(async () => {
      resolveSecond({
        ...suggestionResponse("Veg Pulao"),
        suggestion: {
          day: "Monday",
          meal_slot: "dinner",
          dish: "Veg Pulao",
          prep_time_min: 35,
          reason: "new",
          ingredients: ["rice"],
        },
      });
    });

    expect(result.current.swappingMeal).toBeNull();
    expect(result.current.swapSuggestion?.mealSlot).toBe("dinner");
    expect(result.current.swapSuggestion?.suggestedMeal.dish).toBe("Veg Pulao");
  });

  it("does not clear another slot's spinner when an accept settles", async () => {
    const result = await renderWithPlan();
    vi.mocked(api.swapSingleMeal).mockResolvedValueOnce(suggestionResponse("Paneer Wrap"));
    await act(async () => {
      await result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });

    let resolveAccept: (v: MealPlanResponse) => void = () => {};
    vi.mocked(api.acceptSwap).mockReturnValue(
      new Promise<MealPlanResponse>((r) => {
        resolveAccept = r;
      })
    );
    act(() => {
      void result.current.acceptSwap();
    });

    // While the accept is in flight the user starts a swap on another slot.
    vi.mocked(api.swapSingleMeal).mockReturnValueOnce(
      new Promise<SwapSingleMealResponse>(() => {})
    );
    act(() => {
      void result.current.swapSingleMeal("Monday", "dinner", "Roti Sabzi");
    });
    expect(result.current.swappingMeal).toEqual({ day: "Monday", mealSlot: "dinner" });

    await act(async () => {
      resolveAccept(PLAN_RESPONSE);
    });

    // The dinner request is still running, so its spinner must survive.
    expect(result.current.swappingMeal).toEqual({ day: "Monday", mealSlot: "dinner" });
  });

  it("drops a pending per-meal suggestion when the whole plan is regenerated", async () => {
    const result = await renderWithPlan();

    let resolveSwap: (v: SwapSingleMealResponse) => void = () => {};
    vi.mocked(api.swapSingleMeal).mockReturnValue(
      new Promise<SwapSingleMealResponse>((r) => {
        resolveSwap = r;
      })
    );
    act(() => {
      void result.current.swapSingleMeal("Monday", "lunch", "Dal Rice");
    });

    // Whole-plan swap lands first and replaces every meal.
    vi.mocked(api.swapMeal).mockResolvedValue({
      ...PLAN_RESPONSE,
      meal_plan: [{ ...PLAN[0], dish: "Rajma Chawal" }, PLAN[1]],
    });
    await act(async () => {
      await result.current.swap();
    });

    // The per-meal response arrives afterwards, computed against the old plan.
    await act(async () => {
      resolveSwap(suggestionResponse("Stale Suggestion"));
    });

    expect(result.current.swapSuggestion).toBeNull();
    expect(result.current.swappingMeal).toBeNull();
    expect(result.current.mealPlan[0].dish).toBe("Rajma Chawal");
  });
});
