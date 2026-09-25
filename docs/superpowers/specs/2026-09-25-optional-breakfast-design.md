# Optional Per-Day Breakfast — Design Spec

## Overview

Add an opt-in breakfast slot to each day of the meal plan. Breakfast is never
generated automatically — the user usually skips it. When they want one for a
given day, a per-day trigger asks the LLM for a single breakfast grounded in
their meal history via RAG, gated by the Validator agent, and presented for
approval before it touches the plan or the shopping list.

## Context

Two facts about the existing system shape this design:

1. **Breakfast is already absent by default.** `app/prompts/meal_planner.py`
   instructs "Generate exactly 14 meals (7 days x 2 meals)" — lunch and dinner
   only. No change to plan generation is required.
2. **The pipeline already exists.** `app/agents/single_meal_swap.py` implements
   RAG-query-generation → ChromaDB retrieval → single-meal generation →
   Validator retry loop, and `apply_swap` rebuilds and re-validates the shopping
   list. Breakfast is that same pipeline, inserting a slot rather than replacing
   one.

This work is therefore additive composition over proven machinery, not new
machinery.

## Goals

1. Each of the seven days offers a breakfast trigger; no breakfast is generated
   unless the user asks for that specific day.
2. A triggered breakfast is retrieved from meal history via RAG when a suitable
   dish exists, and invented by the LLM when one does not.
3. The Validator agent gates both the generated meal and the rebuilt shopping
   list, with retries, exactly as the swap flow does.
4. The suggestion is approved before it enters the plan. Nothing mutates the
   plan or the shopping list until the user accepts.
5. An accepted breakfast can be swapped (via the existing per-meal swap) or
   removed, each recomputing the shopping list.

## Non-Goals

- Changing how lunch and dinner are generated.
- Persisting breakfasts across a whole-plan regeneration (see Behavioral
  Decisions).
- A per-day breakfast preference distinct from the existing global dietary
  preference.

## Behavioral Decisions

| Question | Decision |
|---|---|
| Suggestion lands directly, or approved first? | **Approved first**, reusing the existing accept/reject overlay. Consistent with swap; the shopping list moves only on accept. |
| Which days? | **All seven.** Saturday and Sunday included. |
| What can you do with an added breakfast? | **Swap and remove.** Swap comes free from the existing per-meal button; remove is new. |
| Does a whole-plan Generate / Swap Plan keep breakfasts? | **No.** A new plan has no breakfast slots. The user re-triggers the days they want. |
| When does a breakfast reach ChromaDB history? | On **Approve Plan**, like every other meal. No new indexing path. |

## Architecture

### Flow

```
User clicks "Add breakfast" on Monday
    |
    v
POST /api/suggest-breakfast { day: "Monday" }
    |
    v
Backend (app/agents/breakfast.py):
  1. Load dietary preference from preference_service (if set)
  2. LLM call #1 -> optimized breakfast RAG query
  3. ChromaDB query_meals(query, n_results=10) -> relevant history
  4. LLM call #2 -> exactly one breakfast meal
     - prefers a history dish; invents one, reason "new", when none fits
     - must not duplicate any dish already in the plan
     - balanced against that day's existing lunch and dinner
  5. LLM call #3 (Validator agent) -> errors / warnings
     - "from history" dishes checked against chroma_service.meal_exists
  6. errors -> retry from step 4, up to MAX_RETRIES (3)
  7. Return { suggestion, validation_status, validation_warnings }
    |
    v
Frontend renders the suggestion overlay at the top of Monday's meal list
    |
    v
Reject -> overlay clears; trigger is available again for a fresh suggestion
Accept -> POST /api/accept-breakfast { day, new_meal }
    |
    v
Backend:
  1. Insert the slot into _current_plan, ordering the day breakfast/lunch/dinner
  2. Rebuild the full shopping list via the shopping organiser prompts
  3. Validate the shopping list via the Validator agent
  4. Return { meal_plan, grocery_list, shopping_validation_status }
    |
    v
Frontend updates the day card and the shopping list panel
```

Removal is the same tail: `DELETE /api/breakfast/{day}` drops the slot, rebuilds
the list, re-validates, and returns the same shape.

### Validator coverage

The Validator agent runs at both points the user's request calls for:

- **Per meal**, in the generation retry loop — duplicate detection against the
  full current plan, nutritional balance for the day, plausibility, and
  history verification for any dish claiming `reason: "from history"`.
- **Per shopping list**, after every mutation (accept and remove) — the
  existing `SHOPPING_LIST_SYSTEM_PROMPT` / `SHOPPING_LIST_USER_TEMPLATE` pair.

Status resolves to `passed`, `passed_with_warnings`, or `failed`, matching the
swap flow.

### Shared shopping-list rebuild

`apply_swap` currently inlines roughly forty-five lines that rebuild the grocery
list and validate it. `add_breakfast` and `remove_breakfast` need the same
lines verbatim. Rather than carry three copies, extract:

```python
def rebuild_grocery_list(meal_plan: list[dict]) -> dict:
    """Regenerate the grocery list for a plan and validate it.

    Returns {"grocery_list": [...], "shopping_validation_status": "..."}.
    """
```

Place it in `app/agents/shopping_organiser.py` beside the existing node, and
have `apply_swap` call it. This is the only existing behavior touched, and it
is behavior-preserving — the swap flow's observable output is unchanged.

## File Structure

**Backend — create:**

- `app/agents/breakfast.py` — `generate_breakfast_suggestion`, `add_breakfast`,
  `remove_breakfast`
- `app/prompts/breakfast.py` — RAG query prompts, generation prompts, validator
  prompts for the breakfast slot
- `tests/test_breakfast.py`
- `tests/test_breakfast_prompts.py`

**Backend — modify:**

- `app/agents/shopping_organiser.py` — add `rebuild_grocery_list`
- `app/agents/single_meal_swap.py` — `apply_swap` delegates to it
- `app/api/routes.py` — three routes, two request models
- `tests/test_routes.py` — route coverage
- `tests/test_single_meal_swap.py` — confirm the extraction preserves behavior

**Frontend — modify:**

No new frontend components. The trigger, the remove control, and the overlay
placement all live in `MealDayCard.tsx`, which already owns per-meal controls
and the swap overlay; a separate component would split one day's controls
across two files for no gain.


- `src/lib/types.ts` — `SuggestBreakfastResponse`; widen the suggestion shape
- `src/lib/api.ts` — `suggestBreakfast`, `acceptBreakfast`, `removeBreakfast`
- `src/hooks/useMealPlan.ts` — `kind` discriminant on the suggestion state
- `src/components/MealDayCard.tsx` — `B` chip, trigger, remove control, overlay
  placement
- `src/components/MealPlanPanel.tsx` — thread the new callbacks
- `src/app/page.tsx` — wire the hook to the panel
- `src/hooks/__tests__/useMealPlan.test.ts`
- `src/components/__tests__/MealDayCard.test.tsx`
- `src/app/__tests__/page.test.tsx`

## Interfaces

### Backend

```python
def generate_breakfast_suggestion(day: str, current_plan: list[dict]) -> dict:
    """Returns {"suggestion": PlannedMeal, "validation_status": str,
                "validation_warnings": list[str]}."""

def add_breakfast(current_plan: list[dict], day: str, new_meal: dict) -> dict:
    """Returns {"meal_plan": [...], "grocery_list": [...],
                "shopping_validation_status": str}."""

def remove_breakfast(current_plan: list[dict], day: str) -> dict:
    """Same return shape as add_breakfast."""
```

### HTTP

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/suggest-breakfast` | `{ day }` | `{ suggestion, validation_status, validation_warnings }` |
| POST | `/api/accept-breakfast` | `{ day, new_meal }` | `{ meal_plan, grocery_list, shopping_validation_status }` |
| DELETE | `/api/breakfast/{day}` | — | `{ meal_plan, grocery_list, shopping_validation_status }` |

All three return HTTP 400 with `{"status": "error", "message": ...}` when no
plan has been generated, matching `/api/swap-single-meal`.

`POST /api/accept-breakfast` returns 400 when the day already has a breakfast,
and `DELETE /api/breakfast/{day}` returns 400 when it has none. Those two
guards live in the route layer; the agent functions themselves are tolerant —
`add_breakfast` on an occupied day replaces, `remove_breakfast` on an empty day
is a no-op — so they stay pure functions over a plan and are testable without a
request.

### Frontend suggestion state

The hook's existing single-suggestion state widens rather than forks:

```ts
type MealSuggestion = {
  kind: "swap" | "breakfast";
  day: string;
  mealSlot: string;
  originalMeal?: PlannedMeal;   // absent for breakfast — it replaces nothing
  suggestedMeal: PlannedMeal;
};
```

`acceptSwap` dispatches on `kind` to `api.acceptSwap` or `api.acceptBreakfast`.

This reuse is deliberate. The suggestion state already carries the request-token
guard and `invalidatePendingSwap` added in commits `178c143` and `1a76d2d` to
fix the reject-then-retry wedge. Widening it means the breakfast path inherits
that fix rather than reproducing the bug, and a regression cannot appear in one
path alone.

## UI

Each day card gains a trigger when that day has no breakfast:

```
Monday                          [+ Add breakfast]
  L  Dal Rice                30m           [swap]
  D  Paneer Butter Masala    45m           [swap]
```

While the request is in flight the trigger shows a spinner. On response, the
suggestion overlay renders **at the top of the day's meal list**, above lunch:

```
Monday
  +--------------------------------------+
  | Suggested breakfast: Poha      15m   |
  |                  [Accept]  [Reject]  |
  +--------------------------------------+
  L  Dal Rice                30m
  D  Paneer Butter Masala    45m
```

This is the one new UI shape. The swap overlay attaches beneath an existing meal
row; a breakfast suggestion has no row to attach to, so it is positioned at the
head of the day rather than under a sibling.

After acceptance:

```
Monday
  B  Poha                    15m     [swap] [x]
  L  Dal Rice                30m           [swap]
  D  Paneer Butter Masala    45m           [swap]
```

`SLOT_LABELS` in `MealDayCard.tsx` gains `breakfast: { short: "B", color: "#eab308" }`,
sitting alongside the existing lunch orange and dinner red.

## Error Handling

| Condition | Behavior |
|---|---|
| No plan generated yet | 400 from all three routes; the trigger is not rendered, since day cards only exist once a plan does |
| LLM/RAG failure | The hook's `error` state renders through the `swapError` path already wired into `MealPlanPanel` |
| Validator returns errors on every attempt | `validation_status: "failed"` with errors surfaced as warnings; the suggestion is still returned so the user can judge it, matching swap |
| Empty meal history | Expected, not an error — the generation prompt directs the LLM to invent a breakfast with `reason: "new"` |
| Reject, then trigger again | A fresh request fires; guaranteed by the inherited request-token guard |
| Two days triggered in quick succession | The newer request wins; the older response is discarded by the token guard |

## Testing

**Backend (`pytest`)** — `tests/test_breakfast.py`, mirroring
`tests/test_single_meal_swap.py`:

- A RAG query is generated and passed to `chroma_service.query_meals`
- The generated meal is returned with `meal_slot == "breakfast"`
- Empty history produces a suggestion with `reason: "new"` rather than an error
- The Validator agent runs; validator errors trigger a regeneration attempt
- `MAX_RETRIES` exhausted yields `validation_status: "failed"` with the errors
- `add_breakfast` inserts the slot and orders the day breakfast/lunch/dinner
- `add_breakfast` and `remove_breakfast` both rebuild and re-validate the list
- `remove_breakfast` on a day with no breakfast leaves the plan unchanged

`tests/test_routes.py` — 400 with no plan for all three routes, 400 on
duplicate add and on remove-with-nothing-to-remove, and the happy paths.

`tests/test_single_meal_swap.py` — existing assertions must still pass after
`apply_swap` delegates to `rebuild_grocery_list`.

**Frontend (`vitest`)**:

- Hook: triggering sets the in-flight flag for the right day; a suggestion
  arrives with `kind: "breakfast"` and no `originalMeal`; reject clears it;
  **trigger-after-reject fires a second request**; a stale response is discarded
  when a second day is triggered; accept routes to `api.acceptBreakfast`, not
  `api.acceptSwap`
- Card: the trigger renders only for days without a breakfast; the overlay
  renders above lunch; the remove control appears only on a breakfast row
- Page: an end-to-end reject-and-retry cycle against a mocked HTTP layer

## Review Focus

Input classes the tests above should pin, most likely to bite first:

1. **Trigger a breakfast, reject, trigger again** — the exact shape of the bug
   just fixed for swap. The shared state makes it unlikely, which is precisely
   why it needs its own test rather than an assumption.
2. **Accept a breakfast while a swap suggestion for another day is open** —
   single-suggestion state means one must supersede the other; the survivor
   must be the newer one, and no stale spinner may remain.
3. **Remove the last remaining breakfast when it is a day's only meal** — the
   day group disappears from `groupedByDay`, which filters out empty days.
4. **Accept a breakfast whose dish duplicates an existing lunch** — the
   Validator should catch it in the retry loop; if it slips through, the plan
   holds a duplicate the swap validator would have rejected.
5. **A day already holding a breakfast** — the trigger must not render, and the
   route must refuse a second insert rather than producing two breakfast rows.
