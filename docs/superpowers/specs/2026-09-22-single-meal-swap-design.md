# Single Meal Swap with Preferences — Design Spec

## Overview

Add a per-meal "Swap" button on each meal card that replaces a single meal using LLM + RAG, guided by optional user dietary preferences. The existing "Swap Plan" (full-week regeneration) remains unchanged.

## Goals

1. User can swap any individual lunch or dinner without regenerating the rest of the week
2. Dietary preferences are configurable in the UI (natural language text), optional — not required for swap
3. Swap suggestions are grounded in the user's meal history via RAG (semantic search on ChromaDB)
4. The meal planner agent's rules apply to single-meal swaps (history preference, nutritional balance)
5. Meal and shopping list validation runs on every swap
6. Timeouts prevent the app from hanging during LLM/RAG calls

## Architecture

### Three-Step LLM Flow for Swap

```
User clicks Swap on a meal (e.g., Monday Lunch "dal")
    |
    v
POST /api/swap-single-meal { day, meal_slot, current_dish }
    |
    v
Backend:
  1. Load user preferences from data/preferences.json (if set)
  2. LLM call #1: Send preference (or day+slot context) to Claude
     -> Claude generates an optimized RAG search query
  3. ChromaDB: query_meals(optimized_query) -> relevant meal history
  4. LLM call #2 (via meal planner agent logic):
     - Uses meal planner system prompt + rules
     - Scoped to generate 1 meal (not 14)
     - History context = RAG results from step 3 (not get_all_meals)
     - Includes: preference (if set), current plan dishes (avoid duplicates),
       day/slot being swapped
     - Strongly prefers dishes from meal logs (deterministic)
  5. LLM call #3 (via validator agent logic):
     - Checks "from history" dishes exist in ChromaDB
     - Checks no duplicate dishes across current plan
     - Checks nutritional fit for the day
  6. If validation fails -> retry from step 4 (up to 2 times)
  7. Return validated suggestion to frontend
    |
    v
Frontend shows suggestion overlay (Accept / Reject)
    |
    v
If rejected -> user clicks Swap again for a new suggestion
If accepted -> POST /api/accept-swap { day, meal_slot, new_meal }
    |
    v
Backend:
  1. Replace single meal in in-memory _current_plan
  2. Regenerate full shopping list via shopping_organiser agent
  3. Validate shopping list via shopping_validator agent (with retries)
  4. Return updated plan + shopping list
    |
    v
Frontend updates meal card + shopping list
```

### Preferences Management

```
User opens Preferences panel in the UI
    |
    v
Types dietary preference in natural language
  (e.g., "protein and/or vegetables with carbohydrate")
    |
    v
POST /api/preferences { dietary_preference: "..." }
    |
    v
Backend stores to backend/data/preferences.json
```

Preferences are optional. When not set, the swap still works — LLM uses day+slot context for the RAG query, and meal history provides implicit preference signal. When set, the natural language preference is sent to the LLM first, which formulates an optimized query for ChromaDB.

## Components

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `services/preference_service.py` | Read/write preferences to `data/preferences.json` |
| `prompts/single_meal_swap.py` | Prompts for RAG query generation + single meal generation |
| `agents/single_meal_swap.py` | Orchestrates the three-step LLM flow |

### Backend — Modified Files

| File | Change |
|------|--------|
| `api/routes.py` | Add `GET/POST /api/preferences`, `POST /api/swap-single-meal`, `POST /api/accept-swap` |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `components/PreferencesPanel.tsx` | Text input for dietary preference with save button |
| `components/SwapSuggestion.tsx` | Overlay showing suggested meal with Accept/Reject |
| `hooks/usePreferences.ts` | Load/save preferences via API |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `lib/types.ts` | Add `SwapSingleMealResponse` type |
| `lib/api.ts` | Add API functions for preferences + single-meal swap + accept-swap |
| `components/MealDayCard.tsx` | Add per-meal Swap button |
| `components/MealPlanPanel.tsx` | Wire swap suggestion overlay, pass callbacks |
| `hooks/useMealPlan.ts` | Add `swapSingleMeal()` and `acceptSwap()` |
| `app/page.tsx` | Wire preferences panel, single-meal swap handlers |

### Untouched

- `agents/graph.py` — existing LangGraph pipeline unchanged
- `agents/meal_planner.py` — existing full-plan generator unchanged
- `components/ActionButtons.tsx` — existing "Swap Plan" button unchanged

## Data Model

### New Types — Backend

```python
# In preference_service.py
class UserPreferences(TypedDict):
    dietary_preference: str  # natural language, e.g., "protein and/or vegetables with carbohydrate"

# Pydantic request/response models in routes.py
class PreferenceRequest(BaseModel):
    dietary_preference: str

class SwapSingleMealRequest(BaseModel):
    day: str
    meal_slot: str
    current_dish: str

class AcceptSwapRequest(BaseModel):
    day: str
    meal_slot: str
    new_meal: dict
```

### New Types — Frontend

```typescript
export interface SwapSingleMealResponse {
  suggestion: PlannedMeal;
  validation_status: string;
  validation_warnings: string[];
}
```

## Prompts

### RAG Query Generator Prompt

```
System: You are a search query optimizer. Given a user's dietary preference
and the meal context, generate a concise search query for finding relevant
meals in a food database.

Return ONLY the search query string, no explanation.

User: Preference: {preference_or_context}
Meal slot: {meal_slot} on {day}
Current dish to replace: {current_dish}
```

When no preference is set, the input becomes: `"Preference: balanced meal for {meal_slot} on {day}"`.

### Single Meal Planner Prompt

Reuses the meal planner agent's system prompt rules but scoped to 1 meal:

```
System: You are a meal planner. Suggest exactly ONE replacement meal for
{day} {meal_slot}.

Rules:
- Use dishes from the user's meal history. Pick directly from what they
  have eaten before.
- If no suitable history dish fits, you may suggest something new.
- The dish must NOT duplicate any dish already in the plan:
  {other_dishes}
- Balance protein, carbs, and vegetables for {day}, considering the other
  meal that day: {other_meal_for_day}
- Estimate prep time in minutes.
- Mark reason as "from history" if from history, or "new" if new.
- List key ingredients.
{preference_clause}

Return a single JSON object:
{ "day": "...", "meal_slot": "...", "dish": "...", "prep_time_min": N,
  "reason": "...", "ingredients": [...] }

User: Based on the user's relevant meal history below, suggest a
replacement for "{current_dish}".

RELEVANT MEAL HISTORY:
{rag_results}

Generate the replacement meal now.
```

### Single Meal Validator

Reuses the existing `meal_validator_node` logic but adapted for one meal in context of the full plan. Checks:
1. If `reason == "from history"`, verify dish exists in ChromaDB via `meal_exists()`
2. Dish name doesn't appear elsewhere in the current plan
3. Basic nutritional check against the other meal for the same day

## Timeout Strategy

| Layer | Timeout | Behavior |
|-------|---------|----------|
| Frontend: swap-single-meal axios | 60s | Error toast: "Swap took too long, try again" |
| Frontend: accept-swap axios | 90s | Error toast for shopping list regen |
| Backend: Claude API call (each) | 45s | `timeout` param on `messages.create`, raises `APITimeoutError` |
| Backend: ChromaDB query | 10s | Wraps `query_meals()` call |
| Backend: overall swap endpoint | 120s | FastAPI route-level handling |

## UI Behavior

- **Swap button**: Small `RefreshCw` icon on each meal row in `MealDayCard`, visible on hover (desktop) or always visible (mobile)
- **Loading state**: The specific meal shows a spinner overlay; rest of the plan remains visible and non-interactive for that meal only
- **Suggestion overlay**: Inline card below the meal being swapped showing: dish name, prep time, reason badge, ingredients list, Accept/Reject buttons
- **After acceptance**: Meal card updates in-place, shopping list panel refreshes
- **Preferences panel**: Collapsible panel below the Meal History panel. Text area for natural language input. Save button. Shows current saved preference if one exists.
