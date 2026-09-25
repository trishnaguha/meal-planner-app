import os
import uuid

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.agents.graph import build_graph
from app.agents.single_meal_swap import generate_swap_suggestion, apply_swap
from app.agents.breakfast import (
    generate_breakfast_suggestion,
    add_breakfast,
    remove_breakfast,
)
from app.config import settings
from app.services.chromadb_service import chroma_service
from app.services.preference_service import preference_service

router = APIRouter(prefix="/api")

meal_graph = build_graph()

_current_plan: dict = {}


class SwapRequest(BaseModel):
    excluded_dishes: list[str]


class ApproveRequest(BaseModel):
    meal_plan: list[dict] | None = None


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


class SuggestBreakfastRequest(BaseModel):
    day: str


class AcceptBreakfastRequest(BaseModel):
    day: str
    new_meal: dict


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


@router.get("/preferences")
async def get_preferences():
    prefs = preference_service.get()
    return prefs or {}


@router.post("/preferences")
async def save_preferences(request: PreferenceRequest):
    return preference_service.save(request.dietary_preference)


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


@router.post("/suggest-breakfast")
async def suggest_breakfast(request: SuggestBreakfastRequest):
    current_plan_meals = _current_plan.get("meal_plan", [])
    if not current_plan_meals:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No meal plan generated yet"},
        )

    return generate_breakfast_suggestion(
        day=request.day,
        current_plan=current_plan_meals,
    )


@router.post("/accept-breakfast")
async def accept_breakfast_endpoint(request: AcceptBreakfastRequest):
    global _current_plan
    current_plan_meals = _current_plan.get("meal_plan", [])
    if not current_plan_meals:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No meal plan to update"},
        )

    if any(
        m["day"] == request.day and m["meal_slot"] == "breakfast"
        for m in current_plan_meals
    ):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"{request.day} already has a breakfast",
            },
        )

    result = add_breakfast(
        current_plan=current_plan_meals,
        day=request.day,
        new_meal=request.new_meal,
    )
    _current_plan = {
        **_current_plan,
        "meal_plan": result["meal_plan"],
        "grocery_list": result["grocery_list"],
        "shopping_validation_status": result["shopping_validation_status"],
    }
    return result


@router.delete("/breakfast/{day}")
async def remove_breakfast_endpoint(day: str):
    global _current_plan
    current_plan_meals = _current_plan.get("meal_plan", [])
    if not current_plan_meals:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No meal plan to update"},
        )

    if not any(
        m["day"] == day and m["meal_slot"] == "breakfast"
        for m in current_plan_meals
    ):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"{day} has no breakfast"},
        )

    result = remove_breakfast(current_plan=current_plan_meals, day=day)
    _current_plan = {
        **_current_plan,
        "meal_plan": result["meal_plan"],
        "grocery_list": result["grocery_list"],
        "shopping_validation_status": result["shopping_validation_status"],
    }
    return result
