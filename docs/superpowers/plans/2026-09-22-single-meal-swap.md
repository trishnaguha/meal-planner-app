# Single Meal Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-meal swap buttons that use LLM + RAG to suggest replacement meals based on user preferences and meal history, with validation and shopping list updates.

**Architecture:** Three-step LLM flow — (1) LLM optimizes natural language preference into a RAG query, (2) meal planner agent logic generates one replacement meal from RAG results, (3) validator agent checks the suggestion. After user acceptance, shopping organiser + validator regenerate the shopping list. Preferences stored as JSON file, optional for swap.

**Tech Stack:** Python/FastAPI, Anthropic SDK, ChromaDB, LangGraph (existing agents reused), Next.js 16/React 19, TypeScript, Tailwind CSS 4, Axios

**Spec:** `docs/superpowers/specs/2026-09-22-single-meal-swap-design.md`

## Global Constraints

- Backend Python 3.12+, dependencies in `requirements.txt`
- Frontend Next.js 16.3.4, React 19 — read `node_modules/next/dist/docs/` before writing frontend code
- Claude model: `claude-sonnet-4-20250514` via `ClaudeService`
- ChromaDB collection: `meal_history` with cosine distance
- Single-user app — no auth, no user IDs
- Existing "Swap Plan" button and full LangGraph pipeline must remain untouched
- All backend tests use `pytest` with `unittest.mock`, `FastAPI TestClient`
- Frontend axios `directClient` (baseURL `http://localhost:8000/api`) for heavy calls

---

### Task 1: Preference Service (Backend)

**Files:**
- Create: `backend/app/services/preference_service.py`
- Test: `backend/tests/test_preference_service.py`

**Interfaces:**
- Consumes: nothing (standalone service)
- Produces:
  - `PreferenceService.get() -> dict | None` — returns `{"dietary_preference": "..."}` or `None`
  - `PreferenceService.save(dietary_preference: str) -> dict` — writes and returns `{"dietary_preference": "..."}`
  - `preference_service` — module-level singleton instance

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_preference_service.py`:

```python
import json
import os
from unittest.mock import patch

import pytest

from app.services.preference_service import PreferenceService


@pytest.fixture
def tmp_prefs_path(tmp_path):
    return str(tmp_path / "preferences.json")


@pytest.fixture
def service(tmp_prefs_path):
    return PreferenceService(path=tmp_prefs_path)


def test_get_returns_none_when_no_file(service):
    result = service.get()
    assert result is None


def test_save_creates_file_and_returns_preference(service, tmp_prefs_path):
    result = service.save("protein and vegetables with carbohydrate")
    assert result == {"dietary_preference": "protein and vegetables with carbohydrate"}
    assert os.path.exists(tmp_prefs_path)


def test_get_returns_saved_preference(service):
    service.save("high protein meals")
    result = service.get()
    assert result == {"dietary_preference": "high protein meals"}


def test_save_overwrites_existing(service):
    service.save("old preference")
    service.save("new preference")
    result = service.get()
    assert result == {"dietary_preference": "new preference"}


def test_get_returns_none_for_corrupt_file(service, tmp_prefs_path):
    os.makedirs(os.path.dirname(tmp_prefs_path), exist_ok=True)
    with open(tmp_prefs_path, "w") as f:
        f.write("not valid json")
    result = service.get()
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_preference_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.preference_service'`

- [ ] **Step 3: Implement PreferenceService**

Create `backend/app/services/preference_service.py`:

```python
import json
import os

from app.config import settings


class PreferenceService:
    def __init__(self, path: str | None = None):
        self._path = path or os.path.join(
            os.path.dirname(settings.chroma_db_path), "preferences.json"
        )

    def get(self) -> dict | None:
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, dietary_preference: str) -> dict:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {"dietary_preference": dietary_preference}
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
        return data


preference_service = PreferenceService()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_preference_service.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/preference_service.py backend/tests/test_preference_service.py
git commit -m "feat: add preference service for dietary preference storage"
```

---

### Task 2: Single Meal Swap Prompts (Backend)

**Files:**
- Create: `backend/app/prompts/single_meal_swap.py`
- Test: `backend/tests/test_single_meal_swap_prompts.py`

**Interfaces:**
- Consumes: nothing (string templates)
- Produces:
  - `RAG_QUERY_SYSTEM_PROMPT` — system prompt for RAG query generation
  - `RAG_QUERY_USER_TEMPLATE` — user template with `{preference_or_context}`, `{meal_slot}`, `{day}`, `{current_dish}`
  - `SINGLE_MEAL_SYSTEM_TEMPLATE` — system template with `{day}`, `{meal_slot}`, `{other_dishes}`, `{other_meal_for_day}`, `{preference_clause}`
  - `SINGLE_MEAL_USER_TEMPLATE` — user template with `{current_dish}`, `{rag_results}`
  - `PREFERENCE_CLAUSE` — template with `{preference}`
  - `NO_PREFERENCE` — empty string
  - `SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT` — system prompt for single meal validation
  - `SINGLE_MEAL_VALIDATOR_USER_TEMPLATE` — user template with `{meal_text}`, `{full_plan_text}`, `{verified_status}`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_single_meal_swap_prompts.py`:

```python
from app.prompts.single_meal_swap import (
    RAG_QUERY_SYSTEM_PROMPT,
    RAG_QUERY_USER_TEMPLATE,
    SINGLE_MEAL_SYSTEM_TEMPLATE,
    SINGLE_MEAL_USER_TEMPLATE,
    PREFERENCE_CLAUSE,
    NO_PREFERENCE,
    SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT,
    SINGLE_MEAL_VALIDATOR_USER_TEMPLATE,
)


def test_rag_query_user_template_formats():
    result = RAG_QUERY_USER_TEMPLATE.format(
        preference_or_context="protein and vegetables",
        meal_slot="lunch",
        day="Monday",
        current_dish="dal rice",
    )
    assert "protein and vegetables" in result
    assert "lunch" in result
    assert "Monday" in result
    assert "dal rice" in result


def test_single_meal_system_template_formats_with_preference():
    result = SINGLE_MEAL_SYSTEM_TEMPLATE.format(
        day="Monday",
        meal_slot="lunch",
        other_dishes="dal rice, keema paratha",
        other_meal_for_day="dinner: chicken curry",
        preference_clause=PREFERENCE_CLAUSE.format(preference="high protein"),
    )
    assert "Monday" in result
    assert "lunch" in result
    assert "dal rice, keema paratha" in result
    assert "high protein" in result


def test_single_meal_system_template_formats_without_preference():
    result = SINGLE_MEAL_SYSTEM_TEMPLATE.format(
        day="Monday",
        meal_slot="lunch",
        other_dishes="dal rice",
        other_meal_for_day="dinner: chicken curry",
        preference_clause=NO_PREFERENCE,
    )
    assert "Monday" in result
    assert "dietary preference" not in result.lower() or NO_PREFERENCE == ""


def test_single_meal_user_template_formats():
    result = SINGLE_MEAL_USER_TEMPLATE.format(
        current_dish="dal rice",
        rag_results="- keema paratha - Saturday - indian,protein",
    )
    assert "dal rice" in result
    assert "keema paratha" in result


def test_validator_template_formats():
    result = SINGLE_MEAL_VALIDATOR_USER_TEMPLATE.format(
        meal_text="Monday lunch: chicken curry (30min) - from history",
        full_plan_text="Monday lunch: dal\nMonday dinner: chicken curry",
        verified_status="chicken curry: verified in history",
    )
    assert "chicken curry" in result
    assert "Monday" in result


def test_no_preference_is_empty():
    assert NO_PREFERENCE == ""


def test_rag_query_system_prompt_exists():
    assert len(RAG_QUERY_SYSTEM_PROMPT) > 0
    assert "search" in RAG_QUERY_SYSTEM_PROMPT.lower() or "query" in RAG_QUERY_SYSTEM_PROMPT.lower()


def test_validator_system_prompt_exists():
    assert len(SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_single_meal_swap_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the prompts**

Create `backend/app/prompts/single_meal_swap.py`:

```python
RAG_QUERY_SYSTEM_PROMPT = """You are a search query optimizer. Given a user's dietary preference and meal context, generate a concise search query for finding relevant meals in a food database.

The query should combine key food terms that would match stored meal descriptions. Focus on ingredient types, cuisine styles, and meal characteristics.

Return ONLY the search query string, no explanation or formatting."""

RAG_QUERY_USER_TEMPLATE = """Preference: {preference_or_context}
Meal slot: {meal_slot} on {day}
Current dish to replace: {current_dish}"""

SINGLE_MEAL_SYSTEM_TEMPLATE = """You are a meal planner. Suggest exactly ONE replacement meal for {day} {meal_slot}.

Rules:
- Use dishes from the user's meal history. Pick directly from what they have eaten before.
- If no suitable history dish fits, you may suggest something new for variety.
- The dish must NOT duplicate any of these dishes already in the plan: {other_dishes}
- Balance protein, carbs, and vegetables for {day}, considering the other meal that day: {other_meal_for_day}
- Estimate prep time in minutes.
- Mark reason as "from history" if the dish comes from the user's meal history, or "new" if it is a new suggestion.
- List key ingredients for the meal.
{preference_clause}

Return a single JSON object:
{{
  "day": "{day}",
  "meal_slot": "{meal_slot}",
  "dish": "dish name",
  "prep_time_min": 30,
  "reason": "from history",
  "ingredients": ["ingredient1", "ingredient2"]
}}"""

SINGLE_MEAL_USER_TEMPLATE = """Based on the user's relevant meal history below, suggest a replacement for "{current_dish}".

RELEVANT MEAL HISTORY:
{rag_results}

Generate the replacement meal now."""

PREFERENCE_CLAUSE = "- User's dietary preference: {preference}. Prioritize meals that align with this preference."
NO_PREFERENCE = ""

SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT = """You are a meal validator. Check a single replacement meal for issues:

1. Does the dish duplicate any other dish in the current weekly plan?
2. Is there a reasonable balance of protein, carbs, and vegetables for the day when combined with the other meal?
3. Is the meal plausible and well-formed?

Return a JSON object:
{
  "is_valid": true/false,
  "errors": ["list of critical issues that must be fixed"],
  "warnings": ["list of minor issues that are acceptable"]
}

Be lenient — only flag critical issues like exact duplicates or completely implausible meals."""

SINGLE_MEAL_VALIDATOR_USER_TEMPLATE = """Validate this replacement meal:

REPLACEMENT MEAL:
{meal_text}

FULL CURRENT PLAN (the replacement must not duplicate any dish here):
{full_plan_text}

History verification: {verified_status}"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_single_meal_swap_prompts.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompts/single_meal_swap.py backend/tests/test_single_meal_swap_prompts.py
git commit -m "feat: add prompts for single meal swap RAG query and generation"
```

---

### Task 3: Single Meal Swap Agent (Backend)

**Files:**
- Create: `backend/app/agents/single_meal_swap.py`
- Test: `backend/tests/test_single_meal_swap.py`

**Interfaces:**
- Consumes:
  - `preference_service.get() -> dict | None` (from Task 1)
  - `chroma_service.query_meals(query_text: str, n_results: int) -> list[dict]` (existing)
  - `chroma_service.meal_exists(dish_name: str) -> bool` (existing)
  - `claude_service.call(system: str, user: str) -> str` (existing)
  - `claude_service.call_json(system: str, user: str) -> dict | list` (existing)
  - All prompts from Task 2
- Produces:
  - `generate_swap_suggestion(day: str, meal_slot: str, current_dish: str, current_plan: list[dict]) -> dict` — returns `{"suggestion": PlannedMeal, "validation_status": str, "validation_warnings": list[str]}`
  - `apply_swap(current_plan: list[dict], day: str, meal_slot: str, new_meal: dict) -> dict` — returns `{"meal_plan": list, "grocery_list": list, "shopping_validation_status": str}`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_single_meal_swap.py`:

```python
from unittest.mock import patch, MagicMock

import pytest

from app.agents.single_meal_swap import generate_swap_suggestion, apply_swap


@pytest.fixture
def current_plan():
    return [
        {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils", "rice"]},
        {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
         "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken", "onion", "spices"]},
        {"day": "Tuesday", "meal_slot": "lunch", "dish": "rajma chawal",
         "prep_time_min": 25, "reason": "from history", "ingredients": ["kidney beans", "rice"]},
        {"day": "Tuesday", "meal_slot": "dinner", "dish": "paneer tikka",
         "prep_time_min": 30, "reason": "from history", "ingredients": ["paneer", "bell pepper"]},
    ]


@pytest.fixture
def mock_all_services():
    with (
        patch("app.agents.single_meal_swap.preference_service") as mock_pref,
        patch("app.agents.single_meal_swap.chroma_service") as mock_chroma,
        patch("app.agents.single_meal_swap.claude_service") as mock_claude,
    ):
        mock_pref.get.return_value = {"dietary_preference": "protein and vegetables with carbohydrate"}

        mock_chroma.query_meals.return_value = [
            {"id": "meal_1", "document": "keema paratha - Saturday - indian,protein",
             "metadata": {"dish": "keema paratha", "day": "Saturday", "tags": "indian,protein"}, "distance": 0.3},
            {"id": "meal_2", "document": "egg bhurji - Sunday - protein,indian",
             "metadata": {"dish": "egg bhurji", "day": "Sunday", "tags": "protein,indian"}, "distance": 0.4},
        ]
        mock_chroma.meal_exists.return_value = True

        mock_claude.call.return_value = "protein vegetable indian lunch"

        mock_claude.call_json.side_effect = [
            {
                "day": "Monday",
                "meal_slot": "lunch",
                "dish": "keema paratha",
                "prep_time_min": 30,
                "reason": "from history",
                "ingredients": ["ground meat", "flour", "onion"],
            },
            {
                "is_valid": True,
                "errors": [],
                "warnings": [],
            },
        ]

        yield mock_pref, mock_chroma, mock_claude


def test_generate_swap_returns_suggestion(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    result = generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    assert result["suggestion"]["dish"] == "keema paratha"
    assert result["suggestion"]["day"] == "Monday"
    assert result["suggestion"]["meal_slot"] == "lunch"
    assert result["validation_status"] == "passed"


def test_generate_swap_uses_preference_for_rag(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    mock_claude.call.assert_called_once()
    rag_call_args = mock_claude.call.call_args
    assert "protein and vegetables with carbohydrate" in rag_call_args[0][1]


def test_generate_swap_queries_chromadb_with_llm_output(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    mock_chroma.query_meals.assert_called_once_with("protein vegetable indian lunch", n_results=10)


def test_generate_swap_without_preference(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services
    mock_pref.get.return_value = None

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    rag_call_args = mock_claude.call.call_args
    assert "lunch" in rag_call_args[0][1]
    assert "Monday" in rag_call_args[0][1]


def test_generate_swap_retries_on_validation_failure(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
        {"is_valid": False, "errors": ["Duplicate dish: dal rice"], "warnings": []},
        {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
         "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]},
        {"is_valid": True, "errors": [], "warnings": []},
    ]

    result = generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)
    assert result["suggestion"]["dish"] == "keema paratha"
    assert result["validation_status"] == "passed"


def test_generate_swap_gives_up_after_max_retries(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    mock_claude.call_json.side_effect = [
        {"day": "Monday", "meal_slot": "lunch", "dish": "bad1",
         "prep_time_min": 20, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue1"], "warnings": []},
        {"day": "Monday", "meal_slot": "lunch", "dish": "bad2",
         "prep_time_min": 20, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue2"], "warnings": []},
        {"day": "Monday", "meal_slot": "lunch", "dish": "bad3",
         "prep_time_min": 20, "reason": "new", "ingredients": []},
        {"is_valid": False, "errors": ["issue3"], "warnings": []},
    ]

    result = generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)
    assert result["suggestion"]["dish"] == "bad3"
    assert result["validation_status"] == "failed"


def test_generate_swap_excludes_current_plan_dishes(mock_all_services, current_plan):
    mock_pref, mock_chroma, mock_claude = mock_all_services

    generate_swap_suggestion("Monday", "lunch", "dal rice", current_plan)

    meal_gen_call = mock_claude.call_json.call_args_list[0]
    system_prompt = meal_gen_call[0][0]
    assert "chicken curry" in system_prompt
    assert "rajma chawal" in system_prompt


@pytest.fixture
def mock_apply_services():
    with (
        patch("app.agents.single_meal_swap.claude_service") as mock_claude,
    ):
        mock_claude.call_json.side_effect = [
            [{"name": "lentils", "quantity": "500g", "category": "grains_pantry", "used_in": ["dal"]}],
            {"is_valid": True, "errors": [], "warnings": []},
        ]
        yield mock_claude


def test_apply_swap_replaces_meal(mock_apply_services, current_plan):
    new_meal = {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]}

    result = apply_swap(current_plan, "Monday", "lunch", new_meal)

    updated_plan = result["meal_plan"]
    monday_lunch = [m for m in updated_plan if m["day"] == "Monday" and m["meal_slot"] == "lunch"]
    assert len(monday_lunch) == 1
    assert monday_lunch[0]["dish"] == "keema paratha"


def test_apply_swap_preserves_other_meals(mock_apply_services, current_plan):
    new_meal = {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]}

    result = apply_swap(current_plan, "Monday", "lunch", new_meal)

    updated_plan = result["meal_plan"]
    assert len(updated_plan) == len(current_plan)
    tuesday_meals = [m for m in updated_plan if m["day"] == "Tuesday"]
    assert len(tuesday_meals) == 2


def test_apply_swap_regenerates_shopping_list(mock_apply_services, current_plan):
    new_meal = {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history", "ingredients": ["meat", "flour"]}

    result = apply_swap(current_plan, "Monday", "lunch", new_meal)

    assert "grocery_list" in result
    assert len(result["grocery_list"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_single_meal_swap.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the single meal swap agent**

Create `backend/app/agents/single_meal_swap.py`:

```python
from app.agents.state import PlannedMeal, GroceryItem
from app.prompts.single_meal_swap import (
    RAG_QUERY_SYSTEM_PROMPT,
    RAG_QUERY_USER_TEMPLATE,
    SINGLE_MEAL_SYSTEM_TEMPLATE,
    SINGLE_MEAL_USER_TEMPLATE,
    PREFERENCE_CLAUSE,
    NO_PREFERENCE,
    SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT,
    SINGLE_MEAL_VALIDATOR_USER_TEMPLATE,
)
from app.prompts.shopping_organiser import (
    SYSTEM_PROMPT as SHOPPING_SYSTEM_PROMPT,
    USER_TEMPLATE as SHOPPING_USER_TEMPLATE,
)
from app.prompts.validator import (
    SHOPPING_LIST_SYSTEM_PROMPT,
    SHOPPING_LIST_USER_TEMPLATE,
)
from app.services.preference_service import preference_service
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service

MAX_RETRIES = 3


def generate_swap_suggestion(
    day: str,
    meal_slot: str,
    current_dish: str,
    current_plan: list[dict],
) -> dict:
    prefs = preference_service.get()
    preference_text = prefs["dietary_preference"] if prefs else None

    # Step 1: LLM generates optimized RAG query
    context = preference_text or f"balanced meal for {meal_slot} on {day}"
    rag_query = claude_service.call(
        RAG_QUERY_SYSTEM_PROMPT,
        RAG_QUERY_USER_TEMPLATE.format(
            preference_or_context=context,
            meal_slot=meal_slot,
            day=day,
            current_dish=current_dish,
        ),
    ).strip()

    # Step 2: Query ChromaDB with the optimized query
    rag_results = chroma_service.query_meals(rag_query, n_results=10)
    rag_context = "\n".join(
        f"- {r['document']} (day: {r['metadata'].get('day', 'N/A')})"
        for r in rag_results
    ) or "No relevant meal history found."

    # Build context for meal generation
    other_dishes = ", ".join(
        m["dish"] for m in current_plan
        if not (m["day"] == day and m["meal_slot"] == meal_slot)
    )
    other_meal_for_day = next(
        (f"{m['meal_slot']}: {m['dish']}" for m in current_plan
         if m["day"] == day and m["meal_slot"] != meal_slot),
        "none",
    )
    preference_clause = (
        PREFERENCE_CLAUSE.format(preference=preference_text)
        if preference_text
        else NO_PREFERENCE
    )

    system_prompt = SINGLE_MEAL_SYSTEM_TEMPLATE.format(
        day=day,
        meal_slot=meal_slot,
        other_dishes=other_dishes,
        other_meal_for_day=other_meal_for_day,
        preference_clause=preference_clause,
    )
    user_msg = SINGLE_MEAL_USER_TEMPLATE.format(
        current_dish=current_dish,
        rag_results=rag_context,
    )

    # Retry loop: generate + validate
    last_suggestion = None
    last_status = "failed"
    last_warnings: list[str] = []

    for attempt in range(MAX_RETRIES):
        # Step 3: LLM generates one meal (meal planner agent logic)
        raw = claude_service.call_json(system_prompt, user_msg)
        if isinstance(raw, list):
            raw = raw[0]

        suggestion: PlannedMeal = {
            "day": raw.get("day", day),
            "meal_slot": raw.get("meal_slot", meal_slot),
            "dish": raw.get("dish", ""),
            "prep_time_min": raw.get("prep_time_min", 0),
            "reason": raw.get("reason", "new"),
            "ingredients": raw.get("ingredients", []),
        }
        last_suggestion = suggestion

        # Step 4: Validate (validator agent logic)
        verified = "not in history"
        if suggestion["reason"] == "from history":
            if chroma_service.meal_exists(suggestion["dish"]):
                verified = f"{suggestion['dish']}: verified in history"
            else:
                verified = f"{suggestion['dish']}: NOT found in history"

        meal_text = (
            f"{suggestion['day']} {suggestion['meal_slot']}: "
            f"{suggestion['dish']} ({suggestion['prep_time_min']}min) - {suggestion['reason']}"
        )

        # Build full plan text excluding the slot being swapped
        plan_for_validation = [
            m for m in current_plan
            if not (m["day"] == day and m["meal_slot"] == meal_slot)
        ]
        full_plan_text = "\n".join(
            f"{m['day']} {m['meal_slot']}: {m['dish']}"
            for m in plan_for_validation
        )

        validation = claude_service.call_json(
            SINGLE_MEAL_VALIDATOR_SYSTEM_PROMPT,
            SINGLE_MEAL_VALIDATOR_USER_TEMPLATE.format(
                meal_text=meal_text,
                full_plan_text=full_plan_text,
                verified_status=verified,
            ),
        )

        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        last_warnings = warnings

        if not errors:
            last_status = "passed_with_warnings" if warnings else "passed"
            break
        elif attempt == MAX_RETRIES - 1:
            last_status = "failed"
            last_warnings = errors + warnings

    return {
        "suggestion": last_suggestion,
        "validation_status": last_status,
        "validation_warnings": last_warnings,
    }


def apply_swap(
    current_plan: list[dict],
    day: str,
    meal_slot: str,
    new_meal: dict,
) -> dict:
    updated_plan = []
    for meal in current_plan:
        if meal["day"] == day and meal["meal_slot"] == meal_slot:
            updated_plan.append({
                "day": new_meal.get("day", day),
                "meal_slot": new_meal.get("meal_slot", meal_slot),
                "dish": new_meal.get("dish", ""),
                "prep_time_min": new_meal.get("prep_time_min", 0),
                "reason": new_meal.get("reason", "new"),
                "ingredients": new_meal.get("ingredients", []),
            })
        else:
            updated_plan.append(meal)

    # Regenerate shopping list
    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} - ingredients: {', '.join(m.get('ingredients', []))}"
        for m in updated_plan
    )
    raw_list = claude_service.call_json(
        SHOPPING_SYSTEM_PROMPT,
        SHOPPING_USER_TEMPLATE.format(meal_plan_text=meal_plan_text),
    )
    if isinstance(raw_list, dict):
        raw_list = [raw_list]

    grocery_list: list[GroceryItem] = []
    for item in raw_list:
        grocery_list.append({
            "name": item.get("name", ""),
            "quantity": item.get("quantity", ""),
            "category": item.get("category", ""),
            "used_in": item.get("used_in", []),
        })

    # Validate shopping list
    shopping_list_text = "\n".join(
        f"{item['name']} ({item['quantity']}) [{item['category']}] - used in: {', '.join(item['used_in'])}"
        for item in grocery_list
    )
    shopping_validation = claude_service.call_json(
        SHOPPING_LIST_SYSTEM_PROMPT,
        SHOPPING_LIST_USER_TEMPLATE.format(
            meal_plan_text=meal_plan_text,
            shopping_list_text=shopping_list_text,
        ),
    )

    shopping_errors = shopping_validation.get("errors", [])
    shopping_warnings = shopping_validation.get("warnings", [])
    if shopping_errors:
        shopping_status = "failed"
    elif shopping_warnings:
        shopping_status = "passed_with_warnings"
    else:
        shopping_status = "passed"

    return {
        "meal_plan": updated_plan,
        "grocery_list": grocery_list,
        "shopping_validation_status": shopping_status,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_single_meal_swap.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/single_meal_swap.py backend/tests/test_single_meal_swap.py
git commit -m "feat: add single meal swap agent with RAG query + validation"
```

---

### Task 4: API Routes for Preferences & Single Meal Swap (Backend)

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes:
  - `preference_service.get() -> dict | None` (Task 1)
  - `preference_service.save(dietary_preference: str) -> dict` (Task 1)
  - `generate_swap_suggestion(day, meal_slot, current_dish, current_plan) -> dict` (Task 3)
  - `apply_swap(current_plan, day, meal_slot, new_meal) -> dict` (Task 3)
- Produces:
  - `GET /api/preferences` — returns `{"dietary_preference": "..."}` or `{}`
  - `POST /api/preferences` — body `{"dietary_preference": "..."}`, returns saved preference
  - `POST /api/swap-single-meal` — body `{"day": "...", "meal_slot": "...", "current_dish": "..."}`, returns `{"suggestion": PlannedMeal, "validation_status": str, "validation_warnings": list}`
  - `POST /api/accept-swap` — body `{"day": "...", "meal_slot": "...", "new_meal": {...}}`, returns updated plan + grocery list

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_routes.py`:

```python
def test_get_preferences_empty(client):
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.get.return_value = None
        response = client.get("/api/preferences")
        assert response.status_code == 200
        assert response.json() == {}


def test_save_preferences(client):
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.save.return_value = {"dietary_preference": "high protein"}
        response = client.post(
            "/api/preferences",
            json={"dietary_preference": "high protein"},
        )
        assert response.status_code == 200
        assert response.json()["dietary_preference"] == "high protein"
        mock_pref.save.assert_called_once_with("high protein")


def test_get_preferences_returns_saved(client):
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.get.return_value = {"dietary_preference": "protein and vegetables"}
        response = client.get("/api/preferences")
        assert response.status_code == 200
        assert response.json()["dietary_preference"] == "protein and vegetables"


def test_swap_single_meal(client):
    with patch("app.api.routes.generate_swap_suggestion") as mock_swap:
        mock_swap.return_value = {
            "suggestion": {
                "day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history",
                "ingredients": ["meat", "flour"],
            },
            "validation_status": "passed",
            "validation_warnings": [],
        }
        # Set _current_plan so the route has a plan to reference
        from app.api import routes
        routes._current_plan = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
                 "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
            ],
        }

        response = client.post(
            "/api/swap-single-meal",
            json={"day": "Monday", "meal_slot": "lunch", "current_dish": "dal rice"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["suggestion"]["dish"] == "keema paratha"
        assert data["validation_status"] == "passed"


def test_swap_single_meal_no_plan(client):
    from app.api import routes
    routes._current_plan = {}

    response = client.post(
        "/api/swap-single-meal",
        json={"day": "Monday", "meal_slot": "lunch", "current_dish": "dal rice"},
    )
    assert response.status_code == 400


def test_accept_swap(client):
    with patch("app.api.routes.apply_swap") as mock_apply:
        from app.api import routes
        routes._current_plan = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
                 "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils"]},
            ],
        }
        mock_apply.return_value = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                 "prep_time_min": 30, "reason": "from history", "ingredients": ["meat"]},
            ],
            "grocery_list": [{"name": "meat", "quantity": "1kg", "category": "protein", "used_in": ["keema paratha"]}],
            "shopping_validation_status": "passed",
        }

        response = client.post(
            "/api/accept-swap",
            json={
                "day": "Monday",
                "meal_slot": "lunch",
                "new_meal": {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                             "prep_time_min": 30, "reason": "from history", "ingredients": ["meat"]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meal_plan"][0]["dish"] == "keema paratha"
        assert len(data["grocery_list"]) > 0
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_routes.py::test_get_preferences_empty tests/test_routes.py::test_swap_single_meal tests/test_routes.py::test_accept_swap -v`
Expected: FAIL — routes don't exist yet

- [ ] **Step 3: Add route imports and request models to routes.py**

Add these imports at the top of `backend/app/api/routes.py`:

```python
from app.services.preference_service import preference_service
from app.agents.single_meal_swap import generate_swap_suggestion, apply_swap
```

Add these Pydantic models after the existing `ApproveRequest`:

```python
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

- [ ] **Step 4: Add preference endpoints**

Add after the existing `/shopping-list` endpoint in `routes.py`:

```python
@router.get("/preferences")
async def get_preferences():
    prefs = preference_service.get()
    return prefs or {}


@router.post("/preferences")
async def save_preferences(request: PreferenceRequest):
    return preference_service.save(request.dietary_preference)
```

- [ ] **Step 5: Add swap-single-meal endpoint**

Add after the preference endpoints in `routes.py`:

```python
@router.post("/swap-single-meal")
async def swap_single_meal(request: SwapSingleMealRequest):
    current_plan_meals = _current_plan.get("meal_plan", [])
    if not current_plan_meals:
        return {"status": "error", "message": "No meal plan generated yet"}, 400

    result = generate_swap_suggestion(
        day=request.day,
        meal_slot=request.meal_slot,
        current_dish=request.current_dish,
        current_plan=current_plan_meals,
    )
    return result
```

Note: The 400 status needs to use `fastapi.responses.JSONResponse`. Update the implementation:

```python
from fastapi.responses import JSONResponse

@router.post("/swap-single-meal")
async def swap_single_meal(request: SwapSingleMealRequest):
    current_plan_meals = _current_plan.get("meal_plan", [])
    if not current_plan_meals:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No meal plan generated yet"},
        )

    result = generate_swap_suggestion(
        day=request.day,
        meal_slot=request.meal_slot,
        current_dish=request.current_dish,
        current_plan=current_plan_meals,
    )
    return result
```

- [ ] **Step 6: Add accept-swap endpoint**

Add after swap-single-meal in `routes.py`:

```python
@router.post("/accept-swap")
async def accept_swap_endpoint(request: AcceptSwapRequest):
    global _current_plan
    current_plan_meals = _current_plan.get("meal_plan", [])
    if not current_plan_meals:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No meal plan to update"},
        )

    result = apply_swap(
        current_plan=current_plan_meals,
        day=request.day,
        meal_slot=request.meal_slot,
        new_meal=request.new_meal,
    )
    _current_plan = {
        **_current_plan,
        "meal_plan": result["meal_plan"],
        "grocery_list": result["grocery_list"],
        "shopping_validation_status": result["shopping_validation_status"],
    }
    return result
```

- [ ] **Step 7: Run all route tests**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest tests/test_routes.py -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes.py backend/tests/test_routes.py
git commit -m "feat: add API routes for preferences and single meal swap"
```

---

### Task 5: Frontend Types & API Client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: Backend endpoints from Task 4
- Produces:
  - `SwapSingleMealResponse` type — `{ suggestion: PlannedMeal, validation_status: string, validation_warnings: string[] }`
  - `api.getPreferences()` — `GET /api/preferences`
  - `api.savePreferences(dietary_preference: string)` — `POST /api/preferences`
  - `api.swapSingleMeal(day: string, meal_slot: string, current_dish: string)` — `POST /api/swap-single-meal`
  - `api.acceptSwap(day: string, meal_slot: string, new_meal: PlannedMeal)` — `POST /api/accept-swap`

- [ ] **Step 1: Add SwapSingleMealResponse type to types.ts**

Add after the `MealPlanResponse` interface in `frontend/src/lib/types.ts`:

```typescript
export interface SwapSingleMealResponse {
  suggestion: PlannedMeal;
  validation_status: string;
  validation_warnings: string[];
}
```

- [ ] **Step 2: Add API functions to api.ts**

Add these methods to the `api` object in `frontend/src/lib/api.ts`:

```typescript
  async getPreferences(): Promise<{ dietary_preference?: string }> {
    const { data } = await client.get("/preferences");
    return data;
  },

  async savePreferences(dietary_preference: string): Promise<{ dietary_preference: string }> {
    const { data } = await client.post("/preferences", { dietary_preference });
    return data;
  },

  async swapSingleMeal(
    day: string,
    meal_slot: string,
    current_dish: string
  ): Promise<SwapSingleMealResponse> {
    const { data } = await directClient.post<SwapSingleMealResponse>(
      "/swap-single-meal",
      { day, meal_slot, current_dish },
      { timeout: 60_000 },
    );
    return data;
  },

  async acceptSwap(
    day: string,
    meal_slot: string,
    new_meal: PlannedMeal
  ): Promise<MealPlanResponse> {
    const { data } = await directClient.post<MealPlanResponse>(
      "/accept-swap",
      { day, meal_slot, new_meal },
      { timeout: 90_000 },
    );
    return data;
  },
```

Also add `SwapSingleMealResponse` to the import in `api.ts`:

```typescript
import {
  UploadResponse,
  MealPlanResponse,
  MealHistoryResponse,
  SwapSingleMealResponse,
} from "./types";
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/frontend && npx next build --no-lint 2>&1 | head -30`
Expected: No type errors related to new types

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add frontend types and API client for preferences and single meal swap"
```

---

### Task 6: Preferences Panel (Frontend)

**Files:**
- Create: `frontend/src/hooks/usePreferences.ts`
- Create: `frontend/src/components/PreferencesPanel.tsx`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes:
  - `api.getPreferences()` (Task 5)
  - `api.savePreferences(dietary_preference)` (Task 5)
- Produces:
  - `usePreferences()` hook — `{ preference, isSaving, error, loadPreference, savePreference }`
  - `PreferencesPanel` component — rendered in the left sidebar below MealHistoryPanel

- [ ] **Step 1: Create usePreferences hook**

Create `frontend/src/hooks/usePreferences.ts`:

```typescript
"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export function usePreferences() {
  const [preference, setPreference] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPreferences()
      .then((data) => {
        if (data.dietary_preference) {
          setPreference(data.dietary_preference);
        }
        setIsLoaded(true);
      })
      .catch(() => {
        setIsLoaded(true);
      });
  }, []);

  const savePreference = async (text: string) => {
    setIsSaving(true);
    setError(null);
    try {
      const result = await api.savePreferences(text);
      setPreference(result.dietary_preference);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preference");
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  return { preference, isSaving, isLoaded, error, savePreference };
}
```

- [ ] **Step 2: Create PreferencesPanel component**

Create `frontend/src/components/PreferencesPanel.tsx`:

```typescript
"use client";

import { useState, useEffect } from "react";
import { Settings, Save, Check } from "lucide-react";
import { usePreferences } from "@/hooks/usePreferences";

export default function PreferencesPanel() {
  const { preference, isSaving, isLoaded, error, savePreference } = usePreferences();
  const [text, setText] = useState("");
  const [saved, setSaved] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (isLoaded && preference) {
      setText(preference);
    }
  }, [isLoaded, preference]);

  const handleSave = async () => {
    if (!text.trim()) return;
    const success = await savePreference(text.trim());
    if (success) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  return (
    <div className="glass rounded-2xl p-5 animate-fade-in-up delay-200">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between"
      >
        <h2
          className="text-base font-semibold flex items-center gap-2"
          style={{ color: "var(--text-primary)" }}
        >
          <span
            className="w-1.5 h-5 rounded-full"
            style={{
              background: "linear-gradient(180deg, var(--accent), var(--accent-end))",
            }}
          />
          Dietary Preferences
        </h2>
        <Settings
          className="w-4 h-4 transition-transform duration-200"
          style={{
            color: "var(--text-tertiary)",
            transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
          }}
        />
      </button>

      {isOpen && (
        <div className="mt-4 animate-fade-in-up">
          <p className="text-xs mb-2" style={{ color: "var(--text-tertiary)" }}>
            Describe your dietary preference in natural language. This guides meal swap suggestions.
          </p>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g., protein and/or vegetables with carbohydrate"
            rows={3}
            disabled={isSaving}
            className="glass-input w-full px-3 py-2.5 rounded-xl text-base sm:text-sm resize-none"
          />
          <button
            onClick={handleSave}
            disabled={isSaving || !text.trim()}
            className={`mt-3 w-full px-4 py-3 min-h-[44px] rounded-xl text-sm flex items-center justify-center gap-2 ${
              saved ? "btn-success" : "btn-accent"
            }`}
          >
            {saved ? (
              <>
                <Check className="w-4 h-4" />
                Saved
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {isSaving ? "Saving..." : "Save Preference"}
              </>
            )}
          </button>
          {error && (
            <p className="text-xs mt-2" style={{ color: "var(--error)" }}>
              {error}
            </p>
          )}
        </div>
      )}

      {!isOpen && preference && (
        <p
          className="mt-2 text-xs truncate"
          style={{ color: "var(--text-tertiary)" }}
        >
          {preference}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Wire PreferencesPanel into page.tsx**

In `frontend/src/app/page.tsx`, add the import:

```typescript
import PreferencesPanel from "@/components/PreferencesPanel";
```

Add the component in the left sidebar (`lg:col-span-4 xl:col-span-3` div), after `MealHistoryPanel`:

```tsx
<div className="lg:col-span-4 xl:col-span-3">
  <MealHistoryPanel onUploadComplete={handleUploadComplete} existingMealCount={existingMealCount} />
  <div className="mt-5">
    <PreferencesPanel />
  </div>
</div>
```

- [ ] **Step 4: Verify the preferences panel renders**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/frontend && npx next build --no-lint 2>&1 | head -30`
Expected: Build succeeds with no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/usePreferences.ts frontend/src/components/PreferencesPanel.tsx frontend/src/app/page.tsx
git commit -m "feat: add preferences panel for dietary preference input"
```

---

### Task 7: Per-Meal Swap Button & Suggestion UI (Frontend)

**Files:**
- Create: `frontend/src/components/SwapSuggestion.tsx`
- Modify: `frontend/src/components/MealDayCard.tsx`
- Modify: `frontend/src/components/MealPlanPanel.tsx`
- Modify: `frontend/src/hooks/useMealPlan.ts`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes:
  - `api.swapSingleMeal(day, meal_slot, current_dish)` (Task 5)
  - `api.acceptSwap(day, meal_slot, new_meal)` (Task 5)
  - `PlannedMeal`, `SwapSingleMealResponse` types (Task 5)
- Produces:
  - `SwapSuggestion` component — inline card showing meal suggestion with accept/reject
  - Updated `MealDayCard` with per-meal swap buttons
  - `useMealPlan().swapSingleMeal(day, meal_slot, current_dish)` and `useMealPlan().acceptSwap(day, meal_slot, new_meal)`

- [ ] **Step 1: Add swapSingleMeal and acceptSwap to useMealPlan hook**

In `frontend/src/hooks/useMealPlan.ts`, add new state and functions.

Add import for `SwapSingleMealResponse`:

```typescript
import { PlannedMeal, GroceryItem, SwapSingleMealResponse } from "@/lib/types";
```

Add new state variables inside the hook:

```typescript
const [swapSuggestion, setSwapSuggestion] = useState<SwapSingleMealResponse | null>(null);
const [swappingMeal, setSwappingMeal] = useState<{ day: string; meal_slot: string } | null>(null);
```

Add new functions:

```typescript
const swapSingleMeal = async (day: string, meal_slot: string, current_dish: string) => {
  setSwappingMeal({ day, meal_slot });
  setSwapSuggestion(null);
  setError(null);
  try {
    const data = await api.swapSingleMeal(day, meal_slot, current_dish);
    setSwapSuggestion(data);
    return data;
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to get swap suggestion");
    setSwappingMeal(null);
    return null;
  }
};

const acceptSwap = async (day: string, meal_slot: string, newMeal: PlannedMeal) => {
  setError(null);
  try {
    const data = await api.acceptSwap(day, meal_slot, newMeal);
    setMealPlan(data.meal_plan);
    setGroceryList(data.grocery_list);
    setSwapSuggestion(null);
    setSwappingMeal(null);
    return data;
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to apply swap");
    return null;
  }
};

const rejectSwap = () => {
  setSwapSuggestion(null);
  setSwappingMeal(null);
};
```

Update the return object to include the new values:

```typescript
return {
  mealPlan,
  groceryList,
  validationStatus,
  validationWarnings,
  generate,
  swap,
  approve,
  swapSingleMeal,
  acceptSwap,
  rejectSwap,
  swapSuggestion,
  swappingMeal,
  isLoading,
  error,
};
```

- [ ] **Step 2: Create SwapSuggestion component**

Create `frontend/src/components/SwapSuggestion.tsx`:

```typescript
"use client";

import { Check, X, Star, Clock, Loader2 } from "lucide-react";
import { PlannedMeal } from "@/lib/types";

interface Props {
  suggestion: PlannedMeal;
  validationWarnings?: string[];
  onAccept: () => void;
  onReject: () => void;
  isAccepting?: boolean;
}

export default function SwapSuggestion({
  suggestion,
  validationWarnings,
  onAccept,
  onReject,
  isAccepting,
}: Props) {
  return (
    <div
      className="mt-2 rounded-xl p-3 animate-fade-in-up"
      style={{
        background: "var(--glass-bg)",
        border: "1px solid var(--accent)",
      }}
    >
      <p
        className="text-[10px] font-medium uppercase tracking-wider mb-2"
        style={{ color: "var(--accent)" }}
      >
        Suggested replacement
      </p>
      <div className="flex items-start gap-2 text-sm">
        <span
          className="flex-1 font-medium leading-snug"
          style={{ color: "var(--text-primary)" }}
        >
          {suggestion.dish}
          {suggestion.reason === "from history" && (
            <Star className="inline w-3 h-3 ml-1 text-amber-400 fill-amber-400" />
          )}
        </span>
        <span
          className="flex items-center gap-0.5 text-[11px] shrink-0"
          style={{ color: "var(--text-tertiary)" }}
        >
          <Clock className="w-3 h-3" />
          {suggestion.prep_time_min}m
        </span>
      </div>

      {suggestion.ingredients.length > 0 && (
        <p
          className="text-[11px] mt-1.5 leading-relaxed"
          style={{ color: "var(--text-tertiary)" }}
        >
          {suggestion.ingredients.join(", ")}
        </p>
      )}

      {validationWarnings && validationWarnings.length > 0 && (
        <div className="mt-2 space-y-1">
          {validationWarnings.map((w, i) => (
            <p key={i} className="text-[11px]" style={{ color: "var(--warning, #f59e0b)" }}>
              {w}
            </p>
          ))}
        </div>
      )}

      <div className="flex gap-2 mt-3">
        <button
          onClick={onAccept}
          disabled={isAccepting}
          className="flex-1 btn-accent flex items-center justify-center gap-1.5 px-3 py-2 min-h-[36px] rounded-lg text-xs"
        >
          {isAccepting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Check className="w-3.5 h-3.5" />
          )}
          {isAccepting ? "Applying..." : "Accept"}
        </button>
        <button
          onClick={onReject}
          disabled={isAccepting}
          className="flex-1 btn-glass flex items-center justify-center gap-1.5 px-3 py-2 min-h-[36px] rounded-lg text-xs"
        >
          <X className="w-3.5 h-3.5" />
          Reject
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add swap button to MealDayCard**

Update `frontend/src/components/MealDayCard.tsx`.

Add imports:

```typescript
import { Star, Clock, RefreshCw, Loader2 } from "lucide-react";
import { PlannedMeal, SwapSingleMealResponse } from "@/lib/types";
import SwapSuggestion from "./SwapSuggestion";
```

Update the `Props` interface:

```typescript
interface Props {
  day: string;
  meals: PlannedMeal[];
  index: number;
  onSwapMeal?: (day: string, meal_slot: string, current_dish: string) => void;
  swappingMeal?: { day: string; meal_slot: string } | null;
  swapSuggestion?: SwapSingleMealResponse | null;
  onAcceptSwap?: (day: string, meal_slot: string, newMeal: PlannedMeal) => void;
  onRejectSwap?: () => void;
  isAccepting?: boolean;
  disabled?: boolean;
}
```

Update the component function signature and body:

```typescript
export default function MealDayCard({
  day,
  meals,
  index,
  onSwapMeal,
  swappingMeal,
  swapSuggestion,
  onAcceptSwap,
  onRejectSwap,
  isAccepting,
  disabled,
}: Props) {
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
          const isSwapping =
            swappingMeal?.day === day &&
            swappingMeal?.meal_slot === meal.meal_slot;
          const showSuggestion =
            isSwapping && swapSuggestion && !swappingMeal === false;

          return (
            <div key={i}>
              <div className="flex items-start gap-2.5 text-sm group">
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
                {onSwapMeal && (
                  <button
                    onClick={() => onSwapMeal(day, meal.meal_slot, meal.dish)}
                    disabled={disabled || isSwapping}
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity duration-200 p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 shrink-0 mt-0.5"
                    style={{ color: "var(--text-tertiary)" }}
                    title="Swap this meal"
                  >
                    {isSwapping && !swapSuggestion ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                  </button>
                )}
              </div>
              {isSwapping && swapSuggestion && (
                <SwapSuggestion
                  suggestion={swapSuggestion.suggestion}
                  validationWarnings={swapSuggestion.validation_warnings}
                  onAccept={() =>
                    onAcceptSwap?.(day, meal.meal_slot, swapSuggestion.suggestion)
                  }
                  onReject={() => onRejectSwap?.()}
                  isAccepting={isAccepting}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Update MealPlanPanel to pass swap props**

In `frontend/src/components/MealPlanPanel.tsx`, update the Props interface:

```typescript
import { PlannedMeal, AppState, SwapSingleMealResponse } from "@/lib/types";

interface Props {
  mealPlan: PlannedMeal[];
  appState: AppState;
  validationWarnings?: string[];
  onGenerate: () => void;
  onSwap: () => void;
  onApprove: () => void;
  onSwapMeal?: (day: string, meal_slot: string, current_dish: string) => void;
  swappingMeal?: { day: string; meal_slot: string } | null;
  swapSuggestion?: SwapSingleMealResponse | null;
  onAcceptSwap?: (day: string, meal_slot: string, newMeal: PlannedMeal) => void;
  onRejectSwap?: () => void;
  isAccepting?: boolean;
}
```

Update the destructured props in the component function and pass them to `MealDayCard`:

```typescript
export default function MealPlanPanel({
  mealPlan,
  appState,
  validationWarnings,
  onGenerate,
  onSwap,
  onApprove,
  onSwapMeal,
  swappingMeal,
  swapSuggestion,
  onAcceptSwap,
  onRejectSwap,
  isAccepting,
}: Props) {
```

Update the `MealDayCard` rendering to pass the new props:

```tsx
<MealDayCard
  key={day}
  day={day}
  meals={meals}
  index={index}
  onSwapMeal={appState === "plan_ready" ? onSwapMeal : undefined}
  swappingMeal={swappingMeal}
  swapSuggestion={swapSuggestion}
  onAcceptSwap={onAcceptSwap}
  onRejectSwap={onRejectSwap}
  isAccepting={isAccepting}
  disabled={appState !== "plan_ready"}
/>
```

- [ ] **Step 5: Wire everything into page.tsx**

In `frontend/src/app/page.tsx`, destructure the new values from `useMealPlan`:

```typescript
const {
  mealPlan,
  groceryList,
  validationWarnings,
  generate,
  swap,
  approve,
  swapSingleMeal,
  acceptSwap,
  rejectSwap,
  swapSuggestion,
  swappingMeal,
} = useMealPlan();

const [isAccepting, setIsAccepting] = useState(false);
```

Add handler functions:

```typescript
const handleSwapSingleMeal = async (day: string, meal_slot: string, current_dish: string) => {
  await swapSingleMeal(day, meal_slot, current_dish);
};

const handleAcceptSwap = async (day: string, meal_slot: string, newMeal: PlannedMeal) => {
  setIsAccepting(true);
  const result = await acceptSwap(day, meal_slot, newMeal);
  setIsAccepting(false);
  if (!result) setAppState("error");
};

const handleRejectSwap = () => {
  rejectSwap();
};
```

Add the `PlannedMeal` import at the top:

```typescript
import { AppState, PlannedMeal } from "@/lib/types";
```

Pass the new props to `MealPlanPanel`:

```tsx
<MealPlanPanel
  mealPlan={mealPlan}
  appState={appState}
  validationWarnings={validationWarnings}
  onGenerate={handleGenerate}
  onSwap={handleSwap}
  onApprove={handleApprove}
  onSwapMeal={handleSwapSingleMeal}
  swappingMeal={swappingMeal}
  swapSuggestion={swapSuggestion}
  onAcceptSwap={handleAcceptSwap}
  onRejectSwap={handleRejectSwap}
  isAccepting={isAccepting}
/>
```

- [ ] **Step 6: Verify build succeeds**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/frontend && npx next build --no-lint 2>&1 | head -40`
Expected: Build succeeds with no errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/SwapSuggestion.tsx frontend/src/components/MealDayCard.tsx frontend/src/components/MealPlanPanel.tsx frontend/src/hooks/useMealPlan.ts frontend/src/app/page.tsx
git commit -m "feat: add per-meal swap button with suggestion overlay UI"
```

---

### Task 8: End-to-End Smoke Test

**Files:**
- Modify: `backend/tests/test_integration.py`

**Interfaces:**
- Consumes: All backend components from Tasks 1-4

- [ ] **Step 1: Read existing integration test**

Read `backend/tests/test_integration.py` to understand the existing pattern.

- [ ] **Step 2: Add integration tests for the single meal swap flow**

Add to `backend/tests/test_integration.py`:

```python
def test_single_meal_swap_flow(client, mock_services):
    """Integration test: preference save -> swap single meal -> accept swap."""
    mock_claude, mock_chroma = mock_services

    # Save preference
    with patch("app.api.routes.preference_service") as mock_pref:
        mock_pref.save.return_value = {"dietary_preference": "protein and vegetables"}
        response = client.post(
            "/api/preferences",
            json={"dietary_preference": "protein and vegetables"},
        )
        assert response.status_code == 200

    # Set up a current plan
    from app.api import routes
    routes._current_plan = {
        "meal_plan": [
            {"day": "Monday", "meal_slot": "lunch", "dish": "dal rice",
             "prep_time_min": 20, "reason": "from history", "ingredients": ["lentils", "rice"]},
            {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
             "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken"]},
        ],
        "grocery_list": [],
        "validation_status": "passed",
    }

    # Swap single meal
    with patch("app.api.routes.generate_swap_suggestion") as mock_gen:
        mock_gen.return_value = {
            "suggestion": {
                "day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                "prep_time_min": 30, "reason": "from history",
                "ingredients": ["ground meat", "flour"],
            },
            "validation_status": "passed",
            "validation_warnings": [],
        }
        response = client.post(
            "/api/swap-single-meal",
            json={"day": "Monday", "meal_slot": "lunch", "current_dish": "dal rice"},
        )
        assert response.status_code == 200
        assert response.json()["suggestion"]["dish"] == "keema paratha"

    # Accept swap
    with patch("app.api.routes.apply_swap") as mock_apply:
        mock_apply.return_value = {
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                 "prep_time_min": 30, "reason": "from history", "ingredients": ["ground meat", "flour"]},
                {"day": "Monday", "meal_slot": "dinner", "dish": "chicken curry",
                 "prep_time_min": 35, "reason": "from history", "ingredients": ["chicken"]},
            ],
            "grocery_list": [{"name": "ground meat", "quantity": "500g", "category": "protein", "used_in": ["keema paratha"]}],
            "shopping_validation_status": "passed",
        }
        response = client.post(
            "/api/accept-swap",
            json={
                "day": "Monday",
                "meal_slot": "lunch",
                "new_meal": {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                             "prep_time_min": 30, "reason": "from history", "ingredients": ["ground meat", "flour"]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meal_plan"][0]["dish"] == "keema paratha"
        assert data["meal_plan"][1]["dish"] == "chicken curry"
```

- [ ] **Step 3: Run all tests**

Run: `cd /Users/tguha/claude-workspace/meal-planner-app/backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_integration.py
git commit -m "test: add integration tests for single meal swap flow"
```
