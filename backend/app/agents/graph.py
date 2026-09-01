from langgraph.graph import StateGraph, START, END

from app.agents.state import MealPlannerState
from app.agents.history_analyser import history_analyser_node
from app.agents.meal_planner import meal_planner_node
from app.agents.validator import meal_validator_node, shopping_validator_node
from app.agents.shopping_organiser import shopping_organiser_node


def route_by_action(state: MealPlannerState) -> str:
    action = state.get("action", "generate")
    if action == "upload":
        return "history_analyser"
    return "meal_planner"


def route_after_meal_validation(state: MealPlannerState) -> str:
    status = state.get("validation_status", "passed")
    retry_count = state.get("retry_count", 0)

    if status in ("passed", "passed_with_warnings"):
        return "shopping_organiser"
    if retry_count >= 2:
        return "shopping_organiser"
    return "meal_planner"


def route_after_shopping_validation(state: MealPlannerState) -> str:
    status = state.get("shopping_validation_status", "passed")
    retry_count = state.get("shopping_retry_count", 0)

    if status in ("passed", "passed_with_warnings"):
        return END
    if retry_count >= 2:
        return END
    return "shopping_organiser"


def build_graph():
    graph = StateGraph(MealPlannerState)

    graph.add_node("history_analyser", history_analyser_node)
    graph.add_node("meal_planner", meal_planner_node)
    graph.add_node("meal_validator", meal_validator_node)
    graph.add_node("shopping_organiser", shopping_organiser_node)
    graph.add_node("shopping_validator", shopping_validator_node)

    graph.add_conditional_edges(
        START,
        route_by_action,
        {"history_analyser": "history_analyser", "meal_planner": "meal_planner"},
    )

    graph.add_edge("history_analyser", END)
    graph.add_edge("meal_planner", "meal_validator")

    graph.add_conditional_edges(
        "meal_validator",
        route_after_meal_validation,
        {
            "shopping_organiser": "shopping_organiser",
            "meal_planner": "meal_planner",
        },
    )

    graph.add_edge("shopping_organiser", "shopping_validator")

    graph.add_conditional_edges(
        "shopping_validator",
        route_after_shopping_validation,
        {
            END: END,
            "shopping_organiser": "shopping_organiser",
        },
    )

    return graph.compile()
