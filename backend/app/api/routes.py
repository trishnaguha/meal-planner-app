import os
import uuid

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.agents.graph import build_graph
from app.config import settings
from app.services.chromadb_service import chroma_service

router = APIRouter(prefix="/api")

meal_graph = build_graph()

_current_plan: dict = {}


class SwapRequest(BaseModel):
    excluded_dishes: list[str]


class ApproveRequest(BaseModel):
    meal_plan: list[dict] | None = None


@router.post("/upload-meals")
async def upload_meals(
    file: UploadFile | None = File(None),
    text: str = Form(""),
):
    if file:
        ext = os.path.splitext(file.filename)[1].lstrip(".")
        save_path = os.path.join(settings.upload_dir, f"{uuid.uuid4().hex}_{file.filename}")
        os.makedirs(settings.upload_dir, exist_ok=True)
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        state = {
            "action": "upload",
            "raw_text": "",
            "uploaded_file_path": save_path,
            "input_source": "file_upload",
            "file_type": ext,
        }
    elif text.strip():
        state = {
            "action": "upload",
            "raw_text": text,
            "input_source": "paste",
            "uploaded_file_path": None,
            "file_type": None,
        }
    else:
        return {"status": "error", "message": "No file or text provided"}

    result = meal_graph.invoke(state)

    parsed = result.get("parsed_meals", [])
    total_dishes = sum(len(m.get("dishes", [])) for m in parsed)

    return {
        "status": result.get("embedding_status", "complete"),
        "meals_indexed": total_dishes,
        "parsed_meals": parsed,
    }


@router.post("/generate-plan")
async def generate_plan():
    global _current_plan
    state = {
        "action": "generate",
        "excluded_dishes": [],
        "retry_count": 0,
        "shopping_retry_count": 0,
    }

    result = meal_graph.invoke(state)
    _current_plan = result

    return {
        "meal_plan": result.get("meal_plan", []),
        "grocery_list": result.get("grocery_list", []),
        "validation_status": result.get("validation_status", ""),
        "validation_warnings": result.get("validation_warnings", []),
        "shopping_validation_status": result.get("shopping_validation_status", ""),
    }


@router.post("/swap-meal")
async def swap_meal(request: SwapRequest):
    global _current_plan
    state = {
        "action": "swap",
        "excluded_dishes": request.excluded_dishes,
        "retry_count": 0,
        "shopping_retry_count": 0,
    }

    result = meal_graph.invoke(state)
    _current_plan = result

    return {
        "meal_plan": result.get("meal_plan", []),
        "grocery_list": result.get("grocery_list", []),
        "validation_status": result.get("validation_status", ""),
        "validation_warnings": result.get("validation_warnings", []),
        "shopping_validation_status": result.get("shopping_validation_status", ""),
    }


@router.post("/approve-plan")
async def approve_plan(request: ApproveRequest):
    global _current_plan
    plan = request.meal_plan or _current_plan.get("meal_plan", [])

    for meal in plan:
        if isinstance(meal, dict):
            chroma_service.add_meals(
                [
                    {
                        "id": f"approved_{uuid.uuid4().hex[:8]}",
                        "text": f"{meal.get('dish', '')} - {meal.get('day', '')} - approved plan",
                        "metadata": {
                            "day": meal.get("day", ""),
                            "dish": meal.get("dish", ""),
                            "tags": "approved",
                        },
                    }
                ]
            )

    return {"status": "approved", "meals_saved": len(plan)}


@router.get("/meal-history")
async def get_meal_history():
    meals = chroma_service.get_all_meals()
    return {"meals": meals, "total": len(meals)}


@router.get("/current-plan")
async def get_current_plan():
    return {
        "meal_plan": _current_plan.get("meal_plan", []),
        "grocery_list": _current_plan.get("grocery_list", []),
        "validation_status": _current_plan.get("validation_status", ""),
        "validation_warnings": _current_plan.get("validation_warnings", []),
    }


@router.get("/shopping-list")
async def get_shopping_list():
    return {
        "grocery_list": _current_plan.get("grocery_list", []),
        "shopping_validation_status": _current_plan.get("shopping_validation_status", ""),
    }
