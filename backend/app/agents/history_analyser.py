import uuid

from app.agents.state import MealPlannerState, MealEntry
from app.prompts.history_analyser import SYSTEM_PROMPT, USER_TEMPLATE
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service
from app.services.file_parser import parse_file, parse_text


def history_analyser_node(state: MealPlannerState) -> dict:
    if state.get("input_source") == "file_upload" and state.get("uploaded_file_path"):
        raw_text = parse_file(state["uploaded_file_path"], state.get("file_type", "txt"))
    else:
        raw_text = parse_text(state.get("raw_text", ""))

    if not raw_text:
        return {"parsed_meals": [], "embedding_status": "empty"}

    parsed = claude_service.call_json(
        SYSTEM_PROMPT,
        USER_TEMPLATE.format(raw_text=raw_text),
    )

    if isinstance(parsed, dict):
        parsed = [parsed]

    meal_entries: list[MealEntry] = []
    chroma_docs = []

    for record in parsed:
        entry: MealEntry = {
            "day": record.get("day", "unspecified"),
            "dishes": record.get("dishes", []),
            "quantity": record.get("quantity", 1),
            "prep_notes": record.get("prep_notes", ""),
            "tags": record.get("tags", []),
            "original_text": raw_text,
        }
        meal_entries.append(entry)

        for dish in entry["dishes"]:
            chroma_docs.append(
                {
                    "id": f"meal_{uuid.uuid4().hex[:8]}",
                    "text": f"{dish} - {entry['day']} - {', '.join(entry['tags'])}",
                    "metadata": {
                        "day": entry["day"],
                        "dish": dish,
                        "tags": ",".join(entry["tags"]),
                        "quantity": str(entry["quantity"]),
                        "prep_notes": entry["prep_notes"],
                    },
                }
            )

    if chroma_docs:
        chroma_service.add_meals(chroma_docs)

    return {
        "parsed_meals": meal_entries,
        "embedding_status": "complete",
    }
