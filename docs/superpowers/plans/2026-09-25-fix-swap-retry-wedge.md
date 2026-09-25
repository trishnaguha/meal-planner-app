# Fix Per-Meal Swap Retry Wedge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the per-meal swap button re-triggerable after a user rejects a suggestion, instead of leaving the slot stuck on a spinning, disabled button forever.

**Architecture:** The bug is entirely in frontend state. `useMealPlan`'s `swappingMeal` is overloaded to mean both "a swap request is in flight" and "this slot owns the suggestion overlay," and the reject path clears only `swapSuggestion`. The fix narrows `swappingMeal` to in-flight-only (always cleared in `finally`) and re-gates the overlay in `MealDayCard` on `swapSuggestion` alone. The two changes must land together because the current overlay render condition depends on the stale flag. The frontend has no test runner today, so the plan adds Vitest + React Testing Library first.

**Tech Stack:** Next.js 16.3.4, React 19.2.8, TypeScript (strict), Vitest 3, @testing-library/react 16, jsdom

**Spec:** `docs/superpowers/specs/2026-09-22-single-meal-swap-design.md`

## Global Constraints

- Frontend code stays TypeScript strict-mode clean — `tsconfig.json` has `"strict": true`.
- Path alias `@/*` → `./src/*` must resolve in tests as well as in the app.
- No backend changes. `/api/swap-single-meal` and `/api/accept-swap` contracts (`backend/app/api/routes.py:191-229`) stay exactly as they are.
- No new runtime dependencies. Vitest, jsdom, and Testing Library go in `devDependencies` only.
- Do not touch the whole-plan `swap()` / `ActionButtons` flow. This plan is scoped to the per-meal swap button in `MealDayCard`.
- Existing behaviour that must survive: accepting a suggestion still replaces the meal, regenerates the grocery list, and clears the overlay.

## Review Focus

Failure modes the design implies but that the current code does not exercise. Each has a test assigned to the task that owns the code.

1. **Reject then retry the same slot** — the reported bug. Second click must issue a second `POST /api/swap-single-meal` and render a fresh suggestion. → Task 2.
2. **Spinner outliving the request** — once a suggestion is on screen the request is done, so the button must show `RefreshCw` and be clickable, not `Loader2`. → Task 2.
3. **Accept failing (backend 500 / network drop)** — the slot must recover: overlay stays so the user can retry accepting, and the swap button un-disables. Today it wedges identically to the reject path. → Task 2.
4. **Swap request failing** — a rejected promise must clear the in-flight flag and surface `error`, leaving the slot clickable again. → Task 2.
5. **Two slots swapped concurrently** — clicking slot B while slot A is in flight must not let A's late response clear B's spinner or overwrite B's suggestion. Nothing globally disables the other slots' buttons, so this is reachable. → Task 3.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `frontend/package.json` | scripts + devDeps | Modify — add `test` script and test devDeps |
| `frontend/vitest.config.mts` | test runner config (jsdom, `@/*` alias) | Create |
| `frontend/vitest.setup.ts` | registers `@testing-library/jest-dom` matchers | Create |
| `frontend/src/hooks/__tests__/useMealPlan.test.ts` | swap state-machine regression tests | Create |
| `frontend/src/components/__tests__/MealDayCard.test.tsx` | overlay + button render-gating tests | Create |
| `frontend/src/hooks/useMealPlan.ts` | owns swap state; the root-cause fix | Modify (`:76-132`) |
| `frontend/src/components/MealDayCard.tsx` | renders slot row, swap button, overlay | Modify (`:94`, `:106-118`) |

---

### Task 1: Frontend test harness

There is no test runner in `frontend/` today (`package.json` has only `dev`, `build`, `start`, `lint`). This task adds one and proves it runs. It ships a trivial passing test only — the real tests arrive in Task 2, which is why this task is separately reviewable: a reviewer can reject the toolchain choice without rejecting the bug fix.

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.mts`
- Create: `frontend/vitest.setup.ts`
- Test: `frontend/src/hooks/__tests__/smoke.test.ts` (deleted at the end of this task)

**Interfaces:**
- Consumes: nothing.
- Produces: `npm test` (alias for `vitest run`) and `npm run test:watch`, executing `*.test.ts` / `*.test.tsx` under `frontend/src/` in a jsdom environment with the `@/*` alias resolved.

- [ ] **Step 1: Install the test dependencies**

Run from `frontend/`:

```bash
npm install --save-dev vitest@^3 jsdom@^26 @vitejs/plugin-react@^5 \
  @testing-library/react@^16 @testing-library/dom@^10 @testing-library/jest-dom@^6 \
  @testing-library/user-event@^14
```

`@testing-library/react` v16 is the version that supports React 19; do not install v15 or earlier.

- [ ] **Step 2: Create the Vitest config**

Create `frontend/vitest.config.mts`. The `.mts` extension matters — the project is CommonJS-by-default and Vitest needs ESM here.

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
```

- [ ] **Step 3: Create the setup file**

Create `frontend/vitest.setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
```

- [ ] **Step 4: Add the test scripts**

In `frontend/package.json`, add to `"scripts"` (keep the existing four):

```json
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 5: Add a smoke test to prove the harness works**

Create `frontend/src/hooks/__tests__/smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useMealPlan } from "@/hooks/useMealPlan";

describe("test harness", () => {
  it("renders a hook from the @/ alias in jsdom", () => {
    const { result } = renderHook(() => useMealPlan());
    expect(result.current.mealPlan).toEqual([]);
    expect(result.current.swappingMeal).toBeNull();
  });
});
```

- [ ] **Step 6: Run the smoke test**

Run: `npm test` (from `frontend/`)
Expected: PASS, 1 test. If the `@/hooks/useMealPlan` import fails to resolve, the alias in Step 2 is wrong — fix it before continuing.

- [ ] **Step 7: Delete the smoke test**

```bash
rm src/hooks/__tests__/smoke.test.ts
```

It has served its purpose; Task 2 puts real tests in that directory.

- [ ] **Step 8: Check the tree is still typeclean and lints**

Run: `npx tsc --noEmit && npm run lint`
Expected: both clean. If `tsc` complains about `vitest.setup.ts` globals, confirm `"globals": true` is set in the config.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.mts frontend/vitest.setup.ts
git commit -m "test: add vitest + react testing library harness to frontend

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Fix the reject/retry wedge

The root cause. `useMealPlan.ts:76-103` sets `swappingMeal` when a swap starts and clears it only in the `catch` — the success path deliberately leaves it set, because `MealDayCard.tsx:106-109` requires `isSwapping` to be true before it renders the overlay. `rejectSwap` (`useMealPlan.ts:130-132`) clears only `swapSuggestion`, so `swappingMeal` survives the reject and `disabled={isSwapping}` (`MealDayCard.tsx:94`) permanently kills the button while `Loader2` spins.

Hook and component change together in one task: fixing the hook alone would clear `swappingMeal` on success and the overlay would stop rendering entirely.

**Files:**
- Modify: `frontend/src/hooks/useMealPlan.ts:76-132`
- Modify: `frontend/src/components/MealDayCard.tsx:94`, `:106-118`
- Test: `frontend/src/hooks/__tests__/useMealPlan.test.ts` (create)
- Test: `frontend/src/components/__tests__/MealDayCard.test.tsx` (create)

**Interfaces:**
- Consumes: `npm test` from Task 1.
- Produces: unchanged public surface from `useMealPlan()` — `swappingMeal: { day, mealSlot } | null` now means *request in flight only*, and `swapSuggestion` alone drives the overlay. `MealDayCard`'s props are unchanged.

- [ ] **Step 1: Write the failing hook tests**

Create `frontend/src/hooks/__tests__/useMealPlan.test.ts`:

```ts
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
});
```

- [ ] **Step 2: Run the hook tests to verify they fail**

Run: `npm test -- src/hooks/__tests__/useMealPlan.test.ts`
Expected: FAIL. `"clears the in-flight flag once a suggestion arrives"`, `"clears the in-flight flag when the suggestion is rejected"`, `"re-triggers the swap after a reject..."`, and `"keeps the suggestion and unwedges the slot when accept fails"` all fail with `swappingMeal` being `{ day: "Monday", mealSlot: "lunch" }` instead of `null`. That failure *is* the reported bug, reproduced.

- [ ] **Step 3: Write the failing component tests**

Create `frontend/src/components/__tests__/MealDayCard.test.tsx`:

```tsx
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
```

- [ ] **Step 4: Run the component tests to verify they fail**

Run: `npm test -- src/components/__tests__/MealDayCard.test.tsx`
Expected: FAIL. `"renders the suggestion overlay without an in-flight flag"`, `"leaves the swap button enabled..."`, and `"re-triggers onSwapMeal..."` fail, because the overlay currently requires `isSwapping` to be true and the button is disabled whenever it is.

- [ ] **Step 5: Decouple the overlay from the in-flight flag**

In `frontend/src/components/MealDayCard.tsx`, replace the overlay render block (currently lines 106-118):

```tsx
              {isSwapping &&
                swapSuggestion &&
                swapSuggestion.day === day &&
```

with:

```tsx
              {swapSuggestion &&
                swapSuggestion.day === day &&
```

Leave the rest of the condition (`swapSuggestion.mealSlot === meal.meal_slot && onAcceptSwap && onRejectSwap`) and the `<SwapSuggestion />` element untouched. `disabled={isSwapping}` on line 94 stays as-is — it is correct once `isSwapping` genuinely means "in flight."

- [ ] **Step 6: Narrow `swappingMeal` to in-flight-only in the hook**

In `frontend/src/hooks/useMealPlan.ts`, replace `swapSingleMeal` (lines 76-103) with:

```ts
  const swapSingleMeal = async (
    day: string,
    mealSlot: string,
    currentDish: string
  ) => {
    setSwappingMeal({ day, mealSlot });
    setSwapSuggestion(null);
    setError(null);
    try {
      const data = await api.swapSingleMeal(day, mealSlot, currentDish);
      const originalMeal = mealPlan.find(
        (m) => m.day === day && m.meal_slot === mealSlot
      );
      if (originalMeal) {
        setSwapSuggestion({
          day,
          mealSlot,
          originalMeal,
          suggestedMeal: data.suggestion,
        });
      }
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to swap meal");
      return null;
    } finally {
      setSwappingMeal(null);
    }
  };
```

The `finally` is the fix: every exit — success, no-matching-meal, or thrown error — releases the slot.

- [ ] **Step 7: Release the slot when accept fails**

Still in `frontend/src/hooks/useMealPlan.ts`, change the `finally` block of `acceptSwap` (currently lines 125-127) from:

```ts
    } finally {
      setIsLoading(false);
    }
```

to:

```ts
    } finally {
      setIsLoading(false);
      setSwappingMeal(null);
    }
```

`swapSuggestion` is deliberately *not* cleared here — on a failed accept the overlay should stay so the user can retry accepting or reject and swap again.

- [ ] **Step 8: Make reject release both pieces of state**

Replace `rejectSwap` (currently lines 130-132) with:

```ts
  const rejectSwap = () => {
    setSwapSuggestion(null);
    setSwappingMeal(null);
  };
```

Belt-and-braces given Step 6, but it makes the invariant local and obvious: after a reject the slot owns nothing.

- [ ] **Step 9: Run the full suite**

Run: `npm test`
Expected: PASS, 12 tests across the two files.

- [ ] **Step 10: Typecheck and lint**

Run: `npx tsc --noEmit && npm run lint`
Expected: both clean.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/hooks/useMealPlan.ts frontend/src/components/MealDayCard.tsx \
  frontend/src/hooks/__tests__/useMealPlan.test.ts \
  frontend/src/components/__tests__/MealDayCard.test.tsx
git commit -m "fix: allow retrying a per-meal swap after rejecting a suggestion

swappingMeal meant both 'request in flight' and 'this slot owns the
overlay'. rejectSwap cleared only swapSuggestion, so the flag survived
and left the slot's button disabled with a spinner forever, making the
swap impossible to re-trigger.

Narrow swappingMeal to in-flight-only (cleared in finally on every exit)
and gate the overlay on swapSuggestion alone.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Guard against stale responses from concurrent slot swaps

Review Focus item 5. Nothing disables the other slots' swap buttons, so a user can start a swap on Monday lunch and immediately start one on Tuesday dinner. With Task 2 in place, whichever request settles *first* clears `swappingMeal` — killing the second slot's spinner while its request is still running — and a late first response overwrites the second slot's suggestion. A request token fixes both.

**Files:**
- Modify: `frontend/src/hooks/useMealPlan.ts`
- Test: `frontend/src/hooks/__tests__/useMealPlan.test.ts` (append)

**Interfaces:**
- Consumes: the `swapSingleMeal` from Task 2 Step 6.
- Produces: no public surface change. `swappingMeal` now always reflects the *most recent* swap request; responses from superseded requests are discarded.

- [ ] **Step 1: Write the failing test**

Append to the `describe("useMealPlan per-meal swap", ...)` block in `frontend/src/hooks/__tests__/useMealPlan.test.ts`:

```ts
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npm test -- src/hooks/__tests__/useMealPlan.test.ts -t "stale response"`
Expected: FAIL at the first assertion — `swappingMeal` is `null` because the first request's `finally` cleared the dinner slot's flag.

- [ ] **Step 3: Add the request token**

In `frontend/src/hooks/useMealPlan.ts`, add `useRef` to the React import on line 3:

```ts
import { useRef, useState } from "react";
```

Add the ref next to the state declarations, just after the `swappingMeal` declaration (line 23):

```ts
  const swapRequestId = useRef(0);
```

Then replace `swapSingleMeal` with the token-guarded version:

```ts
  const swapSingleMeal = async (
    day: string,
    mealSlot: string,
    currentDish: string
  ) => {
    const requestId = ++swapRequestId.current;
    setSwappingMeal({ day, mealSlot });
    setSwapSuggestion(null);
    setError(null);
    try {
      const data = await api.swapSingleMeal(day, mealSlot, currentDish);
      if (requestId !== swapRequestId.current) return null;
      const originalMeal = mealPlan.find(
        (m) => m.day === day && m.meal_slot === mealSlot
      );
      if (originalMeal) {
        setSwapSuggestion({
          day,
          mealSlot,
          originalMeal,
          suggestedMeal: data.suggestion,
        });
      }
      return data;
    } catch (err) {
      if (requestId !== swapRequestId.current) return null;
      setError(err instanceof Error ? err.message : "Failed to swap meal");
      return null;
    } finally {
      if (requestId === swapRequestId.current) {
        setSwappingMeal(null);
      }
    }
  };
```

Only the newest request is allowed to write state. A superseded request returns `null` and touches nothing.

- [ ] **Step 4: Invalidate in-flight requests on reject and accept**

A user who rejects a suggestion and then does something else should not be ambushed by a late response. Bump the token in `rejectSwap`:

```ts
  const rejectSwap = () => {
    swapRequestId.current += 1;
    setSwapSuggestion(null);
    setSwappingMeal(null);
  };
```

and at the top of `acceptSwap`, immediately after the `if (!swapSuggestion) return false;` guard:

```ts
    swapRequestId.current += 1;
```

- [ ] **Step 5: Run the full suite**

Run: `npm test`
Expected: PASS, 13 tests. Task 2's tests must all still pass — in the single-request case `requestId === swapRequestId.current` always holds, so behaviour is unchanged.

- [ ] **Step 6: Typecheck and lint**

Run: `npx tsc --noEmit && npm run lint`
Expected: both clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/useMealPlan.ts frontend/src/hooks/__tests__/useMealPlan.test.ts
git commit -m "fix: discard stale per-meal swap responses when a newer swap starts

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Manual verification against the running app

Automated tests mock `api`, so they never prove the real request fires on retry. This task confirms it end-to-end.

**Files:** none modified.

**Interfaces:**
- Consumes: the fixes from Tasks 2 and 3.
- Produces: a verified end-to-end retry flow.

- [ ] **Step 1: Start the backend**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Get to a generated plan**

Open http://localhost:3000. If no history is loaded, upload a meal history file, then click **Generate Meal Plan** and wait for the week to render.

- [ ] **Step 4: Run the reported reproduction with the network panel open**

Open DevTools → Network, filter to `swap-single-meal`, then:

1. Hover Monday's lunch row, click the swap (↻) button.
2. Confirm one `POST /api/swap-single-meal` fires and the suggestion overlay appears.
3. Confirm the ↻ button is a refresh icon again (not a spinner) and is clickable.
4. Click **✗** to reject. Confirm the overlay disappears and the button stays a refresh icon.
5. Click ↻ again.

Expected: a **second** `POST /api/swap-single-meal` fires and a new suggestion overlay renders. Before this fix, step 5 produced no request at all and the button sat spinning.

- [ ] **Step 5: Repeat the reject/retry cycle three times**

Confirm the slot never wedges and each retry fires its own request.

- [ ] **Step 6: Confirm accept still works**

On the fourth suggestion, click **✓**. Expected: the meal in the plan updates to the suggested dish, the overlay closes, the shopping list re-renders, and the slot's ↻ button is usable again.

- [ ] **Step 7: Check the concurrent-slot case**

Click ↻ on Monday lunch, and within a second click ↻ on Tuesday lunch. Expected: only Tuesday shows a spinner once Monday's response lands; exactly one suggestion overlay is on screen at the end, on Tuesday.

- [ ] **Step 8: Check the failure path**

Stop the backend (Ctrl-C), then click ↻ on any meal. Expected: the spinner stops when the request fails, the button becomes clickable again, and the slot is not wedged. Restart the backend and confirm a retry succeeds.

- [ ] **Step 9: Commit nothing; report results**

Note any step that deviated from Expected. If steps 4-6 pass, the reported bug is fixed.

---

## Test Plan Summary

| # | What it proves | Where | Type |
|---|---|---|---|
| 1 | Suggestion arriving clears the in-flight flag (spinner stops) | `useMealPlan.test.ts` | unit |
| 2 | Reject clears both suggestion and in-flight flag | `useMealPlan.test.ts` | unit |
| 3 | **Retry after reject fires a second request and yields a new suggestion** | `useMealPlan.test.ts` | unit |
| 4 | Failed swap request releases the slot and sets `error` | `useMealPlan.test.ts` | unit |
| 5 | Failed accept keeps the overlay but releases the slot | `useMealPlan.test.ts` | unit |
| 6 | Successful accept clears both and updates the plan | `useMealPlan.test.ts` | unit |
| 7 | In-flight flag is set while the request is pending | `useMealPlan.test.ts` | unit |
| 8 | Overlay renders on `swapSuggestion` alone | `MealDayCard.test.tsx` | component |
| 9 | Swap button stays enabled while a suggestion shows | `MealDayCard.test.tsx` | component |
| 10 | Swap button is disabled only while in flight | `MealDayCard.test.tsx` | component |
| 11 | Clicking the button with a suggestion showing re-fires `onSwapMeal` | `MealDayCard.test.tsx` | component |
| 12 | A suggestion for another day does not leak into this card | `MealDayCard.test.tsx` | component |
| 13 | Stale response from a superseded slot is discarded | `useMealPlan.test.ts` | unit |
| 14 | Real reject→retry cycle fires a real second HTTP request | Task 4 | manual |
| 15 | Three consecutive reject/retry cycles never wedge | Task 4 | manual |
| 16 | Accept after several retries still updates plan + grocery list | Task 4 | manual |
| 17 | Backend-down retry recovers | Task 4 | manual |

Row 3 is the regression test for the reported bug; it fails on the current `main` and passes after Task 2.

**Not covered, deliberately:** the backend is unchanged, so `backend/tests/test_single_meal_swap.py` and `test_integration.py` need no additions — but run `cd backend && pytest` once before opening the PR to confirm nothing drifted.
