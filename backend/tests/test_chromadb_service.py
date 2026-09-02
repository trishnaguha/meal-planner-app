import pytest
from app.services.chromadb_service import ChromaDBService


@pytest.fixture
def chroma_service():
    service = ChromaDBService(path=None, collection_name="test_meals")
    yield service
    service.clear()


def test_add_and_query_meals(chroma_service):
    meals = [
        {
            "id": "meal_1",
            "text": "keema paratha with spicy ground meat filling",
            "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian,protein"},
        },
        {
            "id": "meal_2",
            "text": "cabbage stir fry with garlic",
            "metadata": {"day": "Saturday", "dish": "cabbage stir fry", "tags": "vegetable"},
        },
    ]
    chroma_service.add_meals(meals)
    assert chroma_service.get_collection_count() == 2


def test_query_returns_relevant_results(chroma_service):
    meals = [
        {
            "id": "meal_1",
            "text": "keema paratha with spicy ground meat",
            "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian,protein"},
        },
        {
            "id": "meal_2",
            "text": "plain rice with dal lentils",
            "metadata": {"day": "Monday", "dish": "dal rice", "tags": "indian,lentils"},
        },
    ]
    chroma_service.add_meals(meals)
    results = chroma_service.query_meals("spicy meat dish", n_results=1)
    assert len(results) == 1
    assert results[0]["metadata"]["dish"] == "keema paratha"


def test_meal_exists(chroma_service):
    meals = [
        {
            "id": "meal_1",
            "text": "keema paratha",
            "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian"},
        },
    ]
    chroma_service.add_meals(meals)
    assert chroma_service.meal_exists("keema paratha") is True
    assert chroma_service.meal_exists("pizza") is False


def test_get_all_meals(chroma_service):
    meals = [
        {
            "id": "meal_1",
            "text": "keema paratha",
            "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian"},
        },
        {
            "id": "meal_2",
            "text": "dal rice",
            "metadata": {"day": "Monday", "dish": "dal rice", "tags": "indian"},
        },
    ]
    chroma_service.add_meals(meals)
    all_meals = chroma_service.get_all_meals()
    assert len(all_meals) == 2
