RAG_QUERY_USER_TEMPLATE = """Preference: {preference_or_context}
Meal slot: breakfast on {day}
Find breakfast-appropriate dishes: light, quick to prepare, suitable for a morning meal."""

BREAKFAST_SYSTEM_TEMPLATE = """You are a meal planner. Suggest exactly ONE breakfast for {day}.

Rules:
- Prefer a breakfast-appropriate dish from the user's meal history.
- The user usually skips breakfast, so their history may contain no breakfast
  dishes at all. That is expected, not an error. When nothing in the history
  suits a morning meal, invent a suitable breakfast and mark reason as "new".
- The dish must NOT duplicate any of these dishes already in the plan: {other_dishes}
- Keep it light and quick relative to a main meal.
- Balance it against the other meals that day: {other_meals_for_day}
- Estimate prep time in minutes.
- Mark reason as "from history" only if the dish genuinely comes from the user's
  meal history, otherwise "new".
- List key ingredients for the meal.
{preference_clause}

Return a single JSON object:
{{
  "day": "{day}",
  "meal_slot": "breakfast",
  "dish": "dish name",
  "prep_time_min": 15,
  "reason": "new",
  "ingredients": ["ingredient1", "ingredient2"]
}}"""

BREAKFAST_USER_TEMPLATE = """Based on the user's relevant meal history below, suggest a breakfast.

RELEVANT MEAL HISTORY:
{rag_results}

Generate the breakfast now."""

PREFERENCE_CLAUSE = "- User's dietary preference: {preference}. Prioritize meals that align with this preference."
NO_PREFERENCE = ""

BREAKFAST_VALIDATOR_SYSTEM_PROMPT = """You are a meal validator. Check a single breakfast addition for issues:

1. Does the dish duplicate any other dish in the current weekly plan?
2. Is the dish plausible as a breakfast - light and quick relative to a main meal?
3. Does it fit reasonably with the other meals planned for that day?

Return a JSON object:
{
  "is_valid": true/false,
  "errors": ["list of critical issues that must be fixed"],
  "warnings": ["list of minor issues that are acceptable"]
}

A breakfast invented by you rather than drawn from history is NOT an error - the
user has little breakfast history. Be lenient: only flag critical issues like
exact duplicates or dishes that are implausible as a morning meal."""

BREAKFAST_VALIDATOR_USER_TEMPLATE = """Validate this breakfast addition:

BREAKFAST:
{meal_text}

FULL CURRENT PLAN (the breakfast must not duplicate any dish here):
{full_plan_text}

History verification: {verified_status}"""
