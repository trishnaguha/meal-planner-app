from unittest.mock import patch, MagicMock

import pytest

from app.agents.graph import build_graph, route_by_action, route_after_meal_validation, route_after_shopping_validation


def test_route_by_action_upload():
    state = {"action": "upload"}
    assert route_by_action(state) == "history_analyser"


def test_route_by_action_generate():
    state = {"action": "generate"}
    assert route_by_action(state) == "meal_planner"


def test_route_by_action_swap():
    state = {"action": "swap"}
    assert route_by_action(state) == "meal_planner"


def test_route_after_meal_validation_passed():
    state = {"validation_status": "passed", "retry_count": 0}
    assert route_after_meal_validation(state) == "shopping_organiser"


def test_route_after_meal_validation_passed_with_warnings():
    state = {"validation_status": "passed_with_warnings", "retry_count": 0}
    assert route_after_meal_validation(state) == "shopping_organiser"


def test_route_after_meal_validation_failed_retry():
    state = {"validation_status": "failed", "retry_count": 1}
    assert route_after_meal_validation(state) == "meal_planner"


def test_route_after_meal_validation_failed_max_retries():
    state = {"validation_status": "failed", "retry_count": 2}
    assert route_after_meal_validation(state) == "shopping_organiser"


def test_route_after_shopping_validation_passed():
    state = {"shopping_validation_status": "passed", "shopping_retry_count": 0}
    assert route_after_shopping_validation(state) == "__end__"


def test_route_after_shopping_validation_failed_retry():
    state = {"shopping_validation_status": "failed", "shopping_retry_count": 1}
    assert route_after_shopping_validation(state) == "shopping_organiser"


def test_route_after_shopping_validation_failed_max_retries():
    state = {"shopping_validation_status": "failed", "shopping_retry_count": 2}
    assert route_after_shopping_validation(state) == "__end__"


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None
