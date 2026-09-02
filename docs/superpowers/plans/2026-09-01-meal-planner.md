# Meal Planner App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-agent meal planning app that analyzes past meal history via RAG, generates validated weekly meal plans, and produces organized grocery shopping lists.

**Architecture:** Four LangGraph agents (History Analyser, Meal Planner, Validator, Shopping Organiser) orchestrated via a StateGraph with conditional edges. FastAPI backend exposes REST endpoints that trigger graph actions. Next.js frontend provides a three-panel dashboard (upload/paste, meal plan with approve/swap, shopping list). ChromaDB stores embedded meal history for RAG retrieval.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, ChromaDB, Anthropic SDK, Next.js (App Router), Tailwind CSS, TypeScript

**Spec:** `docs/superpowers/specs/2026-09-01-meal-planner-design.md`

## Global Constraints

- Python 3.11+ required (union type syntax `str | None`)
- Claude model: `claude-sonnet-4-20250514`
- ChromaDB embeddings: default `all-MiniLM-L6-v2` (no external embedding API)
- LangGraph `^0.4` — use `START`/`END` from `langgraph.graph`
- All agent nodes are pure functions: `(state: MealPlannerState) -> dict` returning partial state updates
- Frontend proxies `/api/*` to `http://localhost:8000` via Next.js rewrites
- No dish repeats within a weekly meal plan
- Validator max 2 retries before passing with warnings

---

### Task 1: Backend Foundation — Config, State Schema, FastAPI App

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/state.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/prompts/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/pyproject.toml`
- Create: `backend/.gitignore`
- Test: `backend/tests/__init__.py`
- Test: `backend/tests/conftest.py`
- Test: `backend/tests/test_state.py`

**Interfaces:**
- Produces: `Settings` class with `anthropic_api_key`, `chroma_db_path`, `chroma_collection_name`, `upload_dir`, `claude_model` — imported as `from app.config import settings`
- Produces: `MealEntry`, `PlannedMeal`, `GroceryItem`, `MealPlannerState` TypedDicts — imported as `from app.agents.state import MealPlannerState, MealEntry, PlannedMeal, GroceryItem`
- Produces: FastAPI app instance — imported as `from app.main import app`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "meal-planner-backend"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi>=0.115.0
uvicorn>=0.30.0
anthropic>=0.52.0
langgraph>=0.4.0
chromadb>=0.5.0
python-multipart>=0.0.9
pypdf2>=3.0.0
pandas>=2.2.0
pydantic>=2.9.0
pydantic-settings>=2.5.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
```

- [ ] **Step 3: Create `backend/.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
CHROMA_DB_PATH=./data/chroma_db
CHROMA_COLLECTION_NAME=meal_history
UPLOAD_DIR=./uploads
CLAUDE_MODEL=claude-sonnet-4-20250514
```

- [ ] **Step 4: Create `backend/.gitignore`**

```
__pycache__/
*.pyc
.env
data/chroma_db/
uploads/*
!uploads/.gitkeep
.pytest_cache/
```

- [ ] **Step 5: Create empty `__init__.py` files**

Create empty files at:
- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/agents/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/prompts/__init__.py`
- `backend/tests/__init__.py`

- [ ] **Step 6: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    chroma_db_path: str = "./data/chroma_db"
    chroma_collection_name: str = "meal_history"
    upload_dir: str = "./uploads"
    claude_model: str = "claude-sonnet-4-20250514"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 7: Create `backend/app/agents/state.py`**

```python
from typing import TypedDict, Literal


class MealEntry(TypedDict):
    day: str
    dishes: list[str]
    quantity: int
    prep_notes: str
    tags: list[str]
    original_text: str


class PlannedMeal(TypedDict):
    day: str
    meal_slot: str
    dish: str
    prep_time_min: int
    reason: str
    ingredients: list[str]


class GroceryItem(TypedDict):
    name: str
    quantity: str
    category: str
    used_in: list[str]


class MealPlannerState(TypedDict, total=False):
    raw_text: str
    uploaded_file_path: str | None
    input_source: Literal["paste", "file_upload"]
    file_type: str | None
    action: Literal["upload", "generate", "swap", "approve"]
    parsed_meals: list[MealEntry]
    embedding_status: str
    meal_plan: list[PlannedMeal]
    excluded_dishes: list[str]
    validation_status: Literal["passed", "failed", "passed_with_warnings"]
    validation_errors: list[str]
    validation_warnings: list[str]
    retry_count: int
    grocery_list: list[GroceryItem]
    shopping_validation_status: Literal["passed", "failed", "passed_with_warnings"]
    shopping_validation_errors: list[str]
    shopping_retry_count: int
```

- [ ] **Step 8: Create `backend/app/main.py`**

```python
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.chroma_db_path, exist_ok=True)
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(title="Meal Planner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Write the failing test for state schema**

Create `backend/tests/conftest.py`:

```python
import pytest


@pytest.fixture
def sample_meal_entry():
    return {
        "day": "Saturday",
        "dishes": ["keema paratha", "cabbage"],
        "quantity": 5,
        "prep_notes": "Make cabbage",
        "tags": ["indian", "paratha", "protein", "vegetable"],
        "original_text": "Saturday 5 keema paratha. Make cabbage",
    }


@pytest.fixture
def sample_planned_meal():
    return {
        "day": "Monday",
        "meal_slot": "lunch",
        "dish": "keema paratha",
        "prep_time_min": 30,
        "reason": "past favorite",
        "ingredients": ["ground meat", "flour", "onion", "spices"],
    }


@pytest.fixture
def sample_grocery_item():
    return {
        "name": "ground meat",
        "quantity": "1 kg",
        "category": "protein",
        "used_in": ["keema paratha"],
    }
```

Create `backend/tests/test_state.py`:

```python
from app.agents.state import MealEntry, PlannedMeal, GroceryItem, MealPlannerState


def test_meal_entry_structure(sample_meal_entry):
    entry: MealEntry = sample_meal_entry
    assert entry["day"] == "Saturday"
    assert "keema paratha" in entry["dishes"]
    assert entry["quantity"] == 5
    assert "indian" in entry["tags"]


def test_planned_meal_structure(sample_planned_meal):
    meal: PlannedMeal = sample_planned_meal
    assert meal["day"] == "Monday"
    assert meal["meal_slot"] == "lunch"
    assert meal["dish"] == "keema paratha"
    assert meal["prep_time_min"] == 30


def test_grocery_item_structure(sample_grocery_item):
    item: GroceryItem = sample_grocery_item
    assert item["name"] == "ground meat"
    assert item["category"] == "protein"
    assert "keema paratha" in item["used_in"]


def test_meal_planner_state_partial():
    state: MealPlannerState = {
        "action": "upload",
        "raw_text": "Saturday 5 keema paratha",
    }
    assert state["action"] == "upload"
    assert "keema" in state["raw_text"]
```

- [ ] **Step 10: Run tests to verify they pass**

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_state.py -v
```

Expected: 4 tests PASS

- [ ] **Step 11: Verify FastAPI app starts**

```bash
cd backend
timeout 5 uvicorn app.main:app --port 8000 || true
curl -s http://localhost:8000/health
```

Expected: `{"status": "ok"}`

- [ ] **Step 12: Commit**

```bash
git add backend/
git commit -m "feat: backend foundation — config, state schema, FastAPI app"
```

---

### Task 2: ChromaDB Service

**Files:**
- Create: `backend/app/services/chromadb_service.py`
- Test: `backend/tests/test_chromadb_service.py`

**Interfaces:**
- Consumes: `settings.chroma_db_path`, `settings.chroma_collection_name` from `app.config`
- Produces: `ChromaDBService` class with methods:
  - `add_meals(meals: list[dict]) -> None` — embed and store meal records
  - `query_meals(query_text: str, n_results: int = 10) -> list[dict]` — RAG retrieval
  - `get_all_meals() -> list[dict]` — list all stored meals
  - `meal_exists(dish_name: str) -> bool` — check if a dish exists in history
  - `get_collection_count() -> int` — return number of stored documents
  - `clear() -> None` — delete all documents (for testing)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chromadb_service.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_chromadb_service.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.chromadb_service'`

- [ ] **Step 3: Implement `backend/app/services/chromadb_service.py`**

```python
import chromadb
from app.config import settings


class ChromaDBService:
    def __init__(
        self,
        path: str | None = settings.chroma_db_path,
        collection_name: str = settings.chroma_collection_name,
    ):
        if path is None:
            self._client = chromadb.Client()
        else:
            self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_meals(self, meals: list[dict]) -> None:
        self._collection.add(
            ids=[m["id"] for m in meals],
            documents=[m["text"] for m in meals],
            metadatas=[m["metadata"] for m in meals],
        )

    def query_meals(self, query_text: str, n_results: int = 10) -> list[dict]:
        results = self._collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        output = []
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
            )
        return output

    def get_all_meals(self) -> list[dict]:
        results = self._collection.get()
        output = []
        for i in range(len(results["ids"])):
            output.append(
                {
                    "id": results["ids"][i],
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i],
                }
            )
        return output

    def meal_exists(self, dish_name: str) -> bool:
        results = self._collection.get(where={"dish": dish_name})
        return len(results["ids"]) > 0

    def get_collection_count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )


chroma_service = ChromaDBService()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_chromadb_service.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/chromadb_service.py backend/tests/test_chromadb_service.py
git commit -m "feat: ChromaDB service — add, query, exists, get_all"
```

---

### Task 3: File Parser Service

**Files:**
- Create: `backend/app/services/file_parser.py`
- Test: `backend/tests/test_file_parser.py`

**Interfaces:**
- Produces: `parse_file(file_path: str, file_type: str) -> str` — returns normalized raw text from any supported format
- Produces: `parse_text(raw_text: str) -> str` — passthrough for pasted text, strips whitespace

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_file_parser.py`:

```python
import json
import os
import tempfile

import pytest

from app.services.file_parser import parse_file, parse_text


def test_parse_text_strips_whitespace():
    result = parse_text("  Saturday 5 keema paratha  \n\n")
    assert result == "Saturday 5 keema paratha"


def test_parse_txt_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Saturday 5 keema paratha. Make cabbage\nSunday 2 dal rice")
        f.flush()
        result = parse_file(f.name, "txt")
    os.unlink(f.name)
    assert "keema paratha" in result
    assert "dal rice" in result


def test_parse_csv_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("day,dish,quantity\nSaturday,keema paratha,5\nSunday,dal rice,2\n")
        f.flush()
        result = parse_file(f.name, "csv")
    os.unlink(f.name)
    assert "Saturday" in result
    assert "keema paratha" in result


def test_parse_json_file():
    data = [
        {"day": "Saturday", "dish": "keema paratha", "quantity": 5},
        {"day": "Sunday", "dish": "dal rice", "quantity": 2},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = parse_file(f.name, "json")
    os.unlink(f.name)
    assert "keema paratha" in result
    assert "dal rice" in result


def test_parse_unsupported_format_raises():
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file("/fake/path.xyz", "xyz")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_file_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `backend/app/services/file_parser.py`**

```python
import json

import pandas as pd


def parse_text(raw_text: str) -> str:
    return raw_text.strip()


def parse_file(file_path: str, file_type: str) -> str:
    file_type = file_type.lower().lstrip(".")

    if file_type == "txt":
        return _parse_txt(file_path)
    elif file_type == "csv":
        return _parse_csv(file_path)
    elif file_type == "json":
        return _parse_json(file_path)
    elif file_type == "pdf":
        return _parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _parse_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _parse_csv(file_path: str) -> str:
    df = pd.read_csv(file_path)
    lines = []
    for _, row in df.iterrows():
        parts = [str(v) for v in row.values if pd.notna(v)]
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _parse_json(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                parts = [str(v) for v in item.values()]
                lines.append(" ".join(parts))
            else:
                lines.append(str(item))
        return "\n".join(lines)
    return json.dumps(data)


def _parse_pdf(file_path: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text.strip())
    return "\n".join(text_parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_file_parser.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/file_parser.py backend/tests/test_file_parser.py
git commit -m "feat: file parser service — txt, csv, json, pdf support"
```

---

### Task 4: Claude Service

**Files:**
- Create: `backend/app/services/claude_service.py`
- Test: `backend/tests/test_claude_service.py`

**Interfaces:**
- Consumes: `settings.anthropic_api_key`, `settings.claude_model` from `app.config`
- Produces: `ClaudeService` class with methods:
  - `call(system_prompt: str, user_message: str) -> str` — send a message to Claude, return text response
  - `call_json(system_prompt: str, user_message: str) -> dict` — send a message, parse JSON from response

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_claude_service.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.services.claude_service import ClaudeService


@pytest.fixture
def mock_claude():
    with patch("app.services.claude_service.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello from Claude")]
        mock_client.messages.create.return_value = mock_response

        service = ClaudeService(api_key="test-key")
        yield service, mock_client


def test_call_returns_text(mock_claude):
    service, mock_client = mock_claude
    result = service.call("You are helpful.", "Say hello")
    assert result == "Hello from Claude"
    mock_client.messages.create.assert_called_once()


def test_call_json_parses_response(mock_claude):
    service, mock_client = mock_claude
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"dishes": ["keema paratha"]}')]
    mock_client.messages.create.return_value = mock_response

    result = service.call_json("Parse meals.", "Saturday 5 keema paratha")
    assert result == {"dishes": ["keema paratha"]}


def test_call_json_handles_markdown_fenced_json(mock_claude):
    service, mock_client = mock_claude
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='```json\n{"dishes": ["dal"]}\n```')]
    mock_client.messages.create.return_value = mock_response

    result = service.call_json("Parse meals.", "Monday dal")
    assert result == {"dishes": ["dal"]}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_claude_service.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `backend/app/services/claude_service.py`**

```python
import json
import re

import anthropic

from app.config import settings


class ClaudeService:
    def __init__(
        self,
        api_key: str = settings.anthropic_api_key,
        model: str = settings.claude_model,
    ):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def call(self, system_prompt: str, user_message: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def call_json(self, system_prompt: str, user_message: str) -> dict | list:
        text = self.call(system_prompt, user_message)
        return self._extract_json(text)

    def _extract_json(self, text: str) -> dict | list:
        fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1).strip())
        return json.loads(text.strip())


claude_service = ClaudeService()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_claude_service.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/claude_service.py backend/tests/test_claude_service.py
git commit -m "feat: Claude service — text and JSON LLM calls with mock tests"
```

---

### Task 5: History Analyser Agent

**Files:**
- Create: `backend/app/prompts/history_analyser.py`
- Create: `backend/app/agents/history_analyser.py`
- Test: `backend/tests/test_history_analyser.py`

**Interfaces:**
- Consumes: `ClaudeService.call_json()` from `app.services.claude_service`
- Consumes: `ChromaDBService.add_meals()` from `app.services.chromadb_service`
- Consumes: `parse_file()`, `parse_text()` from `app.services.file_parser`
- Consumes: `MealPlannerState`, `MealEntry` from `app.agents.state`
- Produces: `history_analyser_node(state: MealPlannerState) -> dict` — returns `{"parsed_meals": [...], "embedding_status": "complete"}`

- [ ] **Step 1: Create `backend/app/prompts/history_analyser.py`**

```python
SYSTEM_PROMPT = """You are a meal log parser. Given raw text containing meal notes, extract structured meal records.

Each record should have:
- day: the day of the week mentioned (e.g., "Saturday")
- dishes: list of dish names mentioned
- quantity: number of servings if mentioned, default to 1
- prep_notes: any cooking instructions or notes
- tags: categorize each entry with relevant tags (e.g., "indian", "protein", "vegetable", "breakfast", "quick")

Return a JSON array of records. Example:
Input: "Saturday 5 keema paratha. Make cabbage"
Output:
[
  {
    "day": "Saturday",
    "dishes": ["keema paratha", "cabbage"],
    "quantity": 5,
    "prep_notes": "Make cabbage",
    "tags": ["indian", "paratha", "protein", "vegetable"]
  }
]

Parse ALL meals from the input. If a line has multiple dishes, include them all. If no day is specified, use "unspecified"."""

USER_TEMPLATE = "Parse the following meal notes into structured records:\n\n{raw_text}"
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_history_analyser.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.agents.history_analyser import history_analyser_node


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.history_analyser.claude_service") as mock_claude,
        patch("app.agents.history_analyser.chroma_service") as mock_chroma,
    ):
        mock_claude.call_json.return_value = [
            {
                "day": "Saturday",
                "dishes": ["keema paratha", "cabbage"],
                "quantity": 5,
                "prep_notes": "Make cabbage",
                "tags": ["indian", "paratha", "protein", "vegetable"],
            }
        ]
        yield mock_claude, mock_chroma


def test_history_analyser_parses_text(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {
        "raw_text": "Saturday 5 keema paratha. Make cabbage",
        "input_source": "paste",
        "action": "upload",
    }

    result = history_analyser_node(state)

    assert len(result["parsed_meals"]) == 1
    assert result["parsed_meals"][0]["day"] == "Saturday"
    assert "keema paratha" in result["parsed_meals"][0]["dishes"]
    assert result["embedding_status"] == "complete"


def test_history_analyser_stores_in_chromadb(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {
        "raw_text": "Saturday 5 keema paratha. Make cabbage",
        "input_source": "paste",
        "action": "upload",
    }

    history_analyser_node(state)

    mock_chroma.add_meals.assert_called_once()
    call_args = mock_chroma.add_meals.call_args[0][0]
    assert len(call_args) == 2  # two dishes: keema paratha and cabbage
    assert call_args[0]["metadata"]["dish"] == "keema paratha"


def test_history_analyser_handles_file_upload(mock_services):
    mock_claude, mock_chroma = mock_services

    with patch("app.agents.history_analyser.parse_file", return_value="Saturday 5 keema paratha"):
        state = {
            "raw_text": "",
            "uploaded_file_path": "/tmp/meals.txt",
            "input_source": "file_upload",
            "file_type": "txt",
            "action": "upload",
        }

        result = history_analyser_node(state)
        assert result["embedding_status"] == "complete"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
pytest tests/test_history_analyser.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `backend/app/agents/history_analyser.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_history_analyser.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/prompts/history_analyser.py backend/app/agents/history_analyser.py backend/tests/test_history_analyser.py
git commit -m "feat: History Analyser agent — parse meal notes, store in ChromaDB"
```

---

### Task 6: Meal Planner Agent

**Files:**
- Create: `backend/app/prompts/meal_planner.py`
- Create: `backend/app/agents/meal_planner.py`
- Test: `backend/tests/test_meal_planner.py`

**Interfaces:**
- Consumes: `ClaudeService.call_json()` from `app.services.claude_service`
- Consumes: `ChromaDBService.query_meals()` from `app.services.chromadb_service`
- Consumes: `MealPlannerState`, `PlannedMeal` from `app.agents.state`
- Produces: `meal_planner_node(state: MealPlannerState) -> dict` — returns `{"meal_plan": [PlannedMeal, ...], "retry_count": 0}`

- [ ] **Step 1: Create `backend/app/prompts/meal_planner.py`**

```python
SYSTEM_PROMPT = """You are a meal planner. Generate a 7-day meal plan (Monday through Sunday) with breakfast, lunch, and dinner for each day.

Rules:
- Balance protein, carbs, and vegetables across each day
- Never repeat the same dish within the week
- Draw from the user's past favorites when possible, but add variety with new suggestions
- Estimate prep time in minutes for each meal
- Mark each meal's reason as "past favorite" if from history, or "new for variety" if new
- List key ingredients for each meal

{exclusion_clause}

Return a JSON array of meal objects:
[
  {{
    "day": "Monday",
    "meal_slot": "breakfast",
    "dish": "Oatmeal with fruit",
    "prep_time_min": 10,
    "reason": "new for variety",
    "ingredients": ["oats", "banana", "honey", "milk"]
  }}
]

Generate exactly 21 meals (7 days x 3 meals)."""

USER_TEMPLATE = """Based on the user's meal history below, generate a balanced 7-day meal plan for next week.

MEAL HISTORY (from most to least relevant):
{history_context}

Generate the meal plan now."""

EXCLUSION_CLAUSE = "IMPORTANT: Do NOT include any of these dishes (user rejected them): {excluded}"
NO_EXCLUSION = ""
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_meal_planner.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.agents.meal_planner import meal_planner_node


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.meal_planner.claude_service") as mock_claude,
        patch("app.agents.meal_planner.chroma_service") as mock_chroma,
    ):
        mock_chroma.query_meals.return_value = [
            {
                "id": "meal_1",
                "document": "keema paratha - Saturday - indian,protein",
                "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian,protein"},
            },
            {
                "id": "meal_2",
                "document": "dal rice - Monday - indian,lentils",
                "metadata": {"day": "Monday", "dish": "dal rice", "tags": "indian,lentils"},
            },
        ]

        mock_claude.call_json.return_value = [
            {
                "day": "Monday",
                "meal_slot": "breakfast",
                "dish": "Oatmeal with fruit",
                "prep_time_min": 10,
                "reason": "new for variety",
                "ingredients": ["oats", "banana", "honey"],
            },
            {
                "day": "Monday",
                "meal_slot": "lunch",
                "dish": "keema paratha",
                "prep_time_min": 30,
                "reason": "past favorite",
                "ingredients": ["ground meat", "flour", "onion"],
            },
        ]
        yield mock_claude, mock_chroma


def test_meal_planner_generates_plan(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {"action": "generate", "excluded_dishes": []}

    result = meal_planner_node(state)

    assert len(result["meal_plan"]) == 2
    assert result["meal_plan"][0]["dish"] == "Oatmeal with fruit"
    assert result["meal_plan"][1]["reason"] == "past favorite"


def test_meal_planner_queries_chromadb(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {"action": "generate", "excluded_dishes": []}

    meal_planner_node(state)

    mock_chroma.query_meals.assert_called_once()


def test_meal_planner_passes_exclusions(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {"action": "swap", "excluded_dishes": ["Oatmeal with fruit"]}

    meal_planner_node(state)

    call_args = mock_claude.call_json.call_args
    system_prompt = call_args[0][0]
    assert "Oatmeal with fruit" in system_prompt
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
pytest tests/test_meal_planner.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `backend/app/agents/meal_planner.py`**

```python
from app.agents.state import MealPlannerState, PlannedMeal
from app.prompts.meal_planner import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    EXCLUSION_CLAUSE,
    NO_EXCLUSION,
)
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service


def meal_planner_node(state: MealPlannerState) -> dict:
    history_results = chroma_service.query_meals(
        "popular meals favorites frequent dishes variety", n_results=20
    )

    history_context = "\n".join(
        f"- {r['document']} (day: {r['metadata'].get('day', 'N/A')})"
        for r in history_results
    )

    if not history_context:
        history_context = "No meal history available yet. Generate a balanced plan from scratch."

    excluded = state.get("excluded_dishes", [])
    if excluded:
        exclusion_clause = EXCLUSION_CLAUSE.format(excluded=", ".join(excluded))
    else:
        exclusion_clause = NO_EXCLUSION

    system = SYSTEM_PROMPT.format(exclusion_clause=exclusion_clause)
    user_msg = USER_TEMPLATE.format(history_context=history_context)

    raw_plan = claude_service.call_json(system, user_msg)

    if isinstance(raw_plan, dict):
        raw_plan = [raw_plan]

    meal_plan: list[PlannedMeal] = []
    for item in raw_plan:
        meal: PlannedMeal = {
            "day": item.get("day", ""),
            "meal_slot": item.get("meal_slot", ""),
            "dish": item.get("dish", ""),
            "prep_time_min": item.get("prep_time_min", 0),
            "reason": item.get("reason", "new for variety"),
            "ingredients": item.get("ingredients", []),
        }
        meal_plan.append(meal)

    return {"meal_plan": meal_plan, "retry_count": 0}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_meal_planner.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/prompts/meal_planner.py backend/app/agents/meal_planner.py backend/tests/test_meal_planner.py
git commit -m "feat: Meal Planner agent — RAG-driven weekly plan generation"
```

---

### Task 7: Validator Agent

**Files:**
- Create: `backend/app/prompts/validator.py`
- Create: `backend/app/agents/validator.py`
- Test: `backend/tests/test_validator.py`

**Interfaces:**
- Consumes: `ClaudeService.call_json()` from `app.services.claude_service`
- Consumes: `ChromaDBService.meal_exists()` from `app.services.chromadb_service`
- Consumes: `MealPlannerState` from `app.agents.state`
- Produces: `meal_validator_node(state: MealPlannerState) -> dict` — returns `{"validation_status": ..., "validation_errors": [...], "validation_warnings": [...], "retry_count": ...}`
- Produces: `shopping_validator_node(state: MealPlannerState) -> dict` — returns `{"shopping_validation_status": ..., "shopping_validation_errors": [...], "shopping_retry_count": ...}`

- [ ] **Step 1: Create `backend/app/prompts/validator.py`**

```python
MEAL_PLAN_SYSTEM_PROMPT = """You are a meal plan validator. Check the meal plan for issues:

1. Are there any duplicate dishes within the same week? List them.
2. Is there a reasonable balance of protein, carbs, and vegetables each day?
3. Are there any meals that seem implausible or nonsensical?

Return a JSON object:
{{
  "is_valid": true/false,
  "errors": ["list of critical issues that must be fixed"],
  "warnings": ["list of minor issues that are acceptable"]
}}

Be strict about duplicates — flag any dish that appears more than once.
Be lenient about nutrition — flag only if an entire day has no vegetables or no protein."""

MEAL_PLAN_USER_TEMPLATE = """Validate this 7-day meal plan:

{meal_plan_text}

Previously verified dishes in history: {verified_dishes}
Dishes NOT found in history (claimed as favorites but unverified): {unverified_dishes}"""

SHOPPING_LIST_SYSTEM_PROMPT = """You are a shopping list validator. Check the grocery list against the meal plan.

1. Does every ingredient trace back to at least one dish in the meal plan?
2. Are there any phantom ingredients not used by any meal?
3. Are quantities reasonable for a week of cooking for one household?
   Flag anything over 5kg for a single item.

Return a JSON object:
{{
  "is_valid": true/false,
  "errors": ["list of critical issues"],
  "warnings": ["list of minor issues"]
}}"""

SHOPPING_LIST_USER_TEMPLATE = """Validate this shopping list against the meal plan.

MEAL PLAN:
{meal_plan_text}

SHOPPING LIST:
{shopping_list_text}"""
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_validator.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.agents.validator import meal_validator_node, shopping_validator_node


@pytest.fixture
def valid_meal_plan():
    return [
        {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
         "prep_time_min": 30, "reason": "past favorite", "ingredients": ["meat", "flour"]},
        {"day": "Tuesday", "meal_slot": "lunch", "dish": "dal rice",
         "prep_time_min": 20, "reason": "past favorite", "ingredients": ["lentils", "rice"]},
    ]


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.validator.claude_service") as mock_claude,
        patch("app.agents.validator.chroma_service") as mock_chroma,
    ):
        mock_chroma.meal_exists.return_value = True
        yield mock_claude, mock_chroma


def test_meal_validator_passes_valid_plan(mock_services, valid_meal_plan):
    mock_claude, mock_chroma = mock_services
    mock_claude.call_json.return_value = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    state = {"meal_plan": valid_meal_plan, "retry_count": 0}

    result = meal_validator_node(state)

    assert result["validation_status"] == "passed"
    assert result["validation_errors"] == []


def test_meal_validator_fails_with_errors(mock_services, valid_meal_plan):
    mock_claude, mock_chroma = mock_services
    mock_claude.call_json.return_value = {
        "is_valid": False,
        "errors": ["Duplicate dish: keema paratha appears on Monday and Wednesday"],
        "warnings": [],
    }
    state = {"meal_plan": valid_meal_plan, "retry_count": 0}

    result = meal_validator_node(state)

    assert result["validation_status"] == "failed"
    assert len(result["validation_errors"]) == 1
    assert result["retry_count"] == 1


def test_meal_validator_flags_unverified_favorites(mock_services, valid_meal_plan):
    mock_claude, mock_chroma = mock_services
    mock_chroma.meal_exists.side_effect = lambda dish: dish == "keema paratha"
    mock_claude.call_json.return_value = {
        "is_valid": True,
        "errors": [],
        "warnings": ["dal rice claimed as favorite but not in history"],
    }
    state = {"meal_plan": valid_meal_plan, "retry_count": 0}

    result = meal_validator_node(state)

    assert result["validation_status"] == "passed_with_warnings"


def test_shopping_validator_passes(mock_services):
    mock_claude, _ = mock_services
    mock_claude.call_json.return_value = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    state = {
        "meal_plan": [{"day": "Monday", "meal_slot": "lunch", "dish": "dal",
                        "prep_time_min": 20, "reason": "past favorite", "ingredients": ["lentils"]}],
        "grocery_list": [{"name": "lentils", "quantity": "500g", "category": "grains_pantry",
                          "used_in": ["dal"]}],
        "shopping_retry_count": 0,
    }

    result = shopping_validator_node(state)

    assert result["shopping_validation_status"] == "passed"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
pytest tests/test_validator.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `backend/app/agents/validator.py`**

```python
from app.agents.state import MealPlannerState
from app.prompts.validator import (
    MEAL_PLAN_SYSTEM_PROMPT,
    MEAL_PLAN_USER_TEMPLATE,
    SHOPPING_LIST_SYSTEM_PROMPT,
    SHOPPING_LIST_USER_TEMPLATE,
)
from app.services.chromadb_service import chroma_service
from app.services.claude_service import claude_service


def meal_validator_node(state: MealPlannerState) -> dict:
    meal_plan = state.get("meal_plan", [])
    retry_count = state.get("retry_count", 0)

    verified = []
    unverified = []
    for meal in meal_plan:
        if meal.get("reason") == "past favorite":
            if chroma_service.meal_exists(meal["dish"]):
                verified.append(meal["dish"])
            else:
                unverified.append(meal["dish"])

    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} ({m['prep_time_min']}min) - {m['reason']}"
        for m in meal_plan
    )

    result = claude_service.call_json(
        MEAL_PLAN_SYSTEM_PROMPT,
        MEAL_PLAN_USER_TEMPLATE.format(
            meal_plan_text=meal_plan_text,
            verified_dishes=", ".join(verified) if verified else "none",
            unverified_dishes=", ".join(unverified) if unverified else "none",
        ),
    )

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if unverified:
        warnings.append(f"Dishes claimed as favorites but not in history: {', '.join(unverified)}")

    if errors:
        status = "failed"
        retry_count += 1
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"

    return {
        "validation_status": status,
        "validation_errors": errors,
        "validation_warnings": warnings,
        "retry_count": retry_count,
    }


def shopping_validator_node(state: MealPlannerState) -> dict:
    meal_plan = state.get("meal_plan", [])
    grocery_list = state.get("grocery_list", [])
    shopping_retry_count = state.get("shopping_retry_count", 0)

    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} - ingredients: {', '.join(m.get('ingredients', []))}"
        for m in meal_plan
    )
    shopping_list_text = "\n".join(
        f"{item['name']} ({item['quantity']}) [{item['category']}] - used in: {', '.join(item['used_in'])}"
        for item in grocery_list
    )

    result = claude_service.call_json(
        SHOPPING_LIST_SYSTEM_PROMPT,
        SHOPPING_LIST_USER_TEMPLATE.format(
            meal_plan_text=meal_plan_text,
            shopping_list_text=shopping_list_text,
        ),
    )

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if errors:
        status = "failed"
        shopping_retry_count += 1
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"

    return {
        "shopping_validation_status": status,
        "shopping_validation_errors": errors,
        "shopping_retry_count": shopping_retry_count,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_validator.py -v
```

Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/prompts/validator.py backend/app/agents/validator.py backend/tests/test_validator.py
git commit -m "feat: Validator agent — meal plan and shopping list validation"
```

---

### Task 8: Shopping Organiser Agent

**Files:**
- Create: `backend/app/prompts/shopping_organiser.py`
- Create: `backend/app/agents/shopping_organiser.py`
- Test: `backend/tests/test_shopping_organiser.py`

**Interfaces:**
- Consumes: `ClaudeService.call_json()` from `app.services.claude_service`
- Consumes: `MealPlannerState`, `GroceryItem` from `app.agents.state`
- Produces: `shopping_organiser_node(state: MealPlannerState) -> dict` — returns `{"grocery_list": [GroceryItem, ...], "shopping_retry_count": 0}`

- [ ] **Step 1: Create `backend/app/prompts/shopping_organiser.py`**

```python
SYSTEM_PROMPT = """You are a shopping list organiser. Given a 7-day meal plan, extract ALL raw ingredients needed, aggregate quantities for ingredients used in multiple dishes, and group them by grocery store section.

Categories:
- produce: fresh vegetables, fruits, herbs
- protein: meat, fish, eggs, tofu
- dairy: milk, cheese, yogurt, butter
- grains_pantry: rice, flour, pasta, canned goods, oils
- spices: spices, seasonings, condiments

For each ingredient, specify:
- name: ingredient name
- quantity: estimated amount for the week (e.g., "1 kg", "500g", "2 heads")
- category: one of the categories above
- used_in: list of dish names that use this ingredient

Combine duplicate ingredients across dishes. For example, if two dishes need onions, add up the quantities.

Return a JSON array:
[
  {{
    "name": "onions",
    "quantity": "2 kg",
    "category": "produce",
    "used_in": ["keema paratha", "dal"]
  }}
]"""

USER_TEMPLATE = """Extract and organize the shopping list for this meal plan:

{meal_plan_text}"""
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_shopping_organiser.py`:

```python
from unittest.mock import patch

import pytest

from app.agents.shopping_organiser import shopping_organiser_node


@pytest.fixture
def sample_state():
    return {
        "meal_plan": [
            {
                "day": "Monday",
                "meal_slot": "lunch",
                "dish": "keema paratha",
                "prep_time_min": 30,
                "reason": "past favorite",
                "ingredients": ["ground meat", "flour", "onion"],
            },
            {
                "day": "Tuesday",
                "meal_slot": "dinner",
                "dish": "dal rice",
                "prep_time_min": 25,
                "reason": "past favorite",
                "ingredients": ["lentils", "rice", "onion"],
            },
        ],
    }


@pytest.fixture
def mock_claude():
    with patch("app.agents.shopping_organiser.claude_service") as mock:
        mock.call_json.return_value = [
            {"name": "ground meat", "quantity": "1 kg", "category": "protein",
             "used_in": ["keema paratha"]},
            {"name": "onions", "quantity": "1 kg", "category": "produce",
             "used_in": ["keema paratha", "dal rice"]},
            {"name": "flour", "quantity": "500g", "category": "grains_pantry",
             "used_in": ["keema paratha"]},
            {"name": "lentils", "quantity": "500g", "category": "grains_pantry",
             "used_in": ["dal rice"]},
            {"name": "rice", "quantity": "1 kg", "category": "grains_pantry",
             "used_in": ["dal rice"]},
        ]
        yield mock


def test_shopping_organiser_extracts_ingredients(mock_claude, sample_state):
    result = shopping_organiser_node(sample_state)

    assert len(result["grocery_list"]) == 5
    assert result["shopping_retry_count"] == 0


def test_shopping_organiser_groups_by_category(mock_claude, sample_state):
    result = shopping_organiser_node(sample_state)

    categories = {item["category"] for item in result["grocery_list"]}
    assert "protein" in categories
    assert "produce" in categories
    assert "grains_pantry" in categories


def test_shopping_organiser_tracks_used_in(mock_claude, sample_state):
    result = shopping_organiser_node(sample_state)

    onions = next(item for item in result["grocery_list"] if item["name"] == "onions")
    assert "keema paratha" in onions["used_in"]
    assert "dal rice" in onions["used_in"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
pytest tests/test_shopping_organiser.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `backend/app/agents/shopping_organiser.py`**

```python
from app.agents.state import MealPlannerState, GroceryItem
from app.prompts.shopping_organiser import SYSTEM_PROMPT, USER_TEMPLATE
from app.services.claude_service import claude_service


def shopping_organiser_node(state: MealPlannerState) -> dict:
    meal_plan = state.get("meal_plan", [])

    meal_plan_text = "\n".join(
        f"{m['day']} {m['meal_slot']}: {m['dish']} - ingredients: {', '.join(m.get('ingredients', []))}"
        for m in meal_plan
    )

    raw_list = claude_service.call_json(
        SYSTEM_PROMPT,
        USER_TEMPLATE.format(meal_plan_text=meal_plan_text),
    )

    if isinstance(raw_list, dict):
        raw_list = [raw_list]

    grocery_list: list[GroceryItem] = []
    for item in raw_list:
        grocery: GroceryItem = {
            "name": item.get("name", ""),
            "quantity": item.get("quantity", ""),
            "category": item.get("category", ""),
            "used_in": item.get("used_in", []),
        }
        grocery_list.append(grocery)

    return {
        "grocery_list": grocery_list,
        "shopping_retry_count": 0,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_shopping_organiser.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/prompts/shopping_organiser.py backend/app/agents/shopping_organiser.py backend/tests/test_shopping_organiser.py
git commit -m "feat: Shopping Organiser agent — ingredient extraction and grouping"
```

---

### Task 9: LangGraph StateGraph Wiring

**Files:**
- Create: `backend/app/agents/graph.py`
- Test: `backend/tests/test_graph.py`

**Interfaces:**
- Consumes: `history_analyser_node` from `app.agents.history_analyser`
- Consumes: `meal_planner_node` from `app.agents.meal_planner`
- Consumes: `meal_validator_node`, `shopping_validator_node` from `app.agents.validator`
- Consumes: `shopping_organiser_node` from `app.agents.shopping_organiser`
- Consumes: `MealPlannerState` from `app.agents.state`
- Produces: `build_graph() -> CompiledGraph` — a compiled LangGraph that can be invoked with `graph.invoke(state)`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_graph.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_graph.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `backend/app/agents/graph.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_graph.py -v
```

Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/graph.py backend/tests/test_graph.py
git commit -m "feat: LangGraph StateGraph — conditional edges, routing, retry logic"
```

---

### Task 10: FastAPI API Routes

**Files:**
- Create: `backend/app/api/routes.py`
- Modify: `backend/app/main.py` — add router include
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `build_graph()` from `app.agents.graph`
- Consumes: `ChromaDBService` from `app.services.chromadb_service`
- Produces: REST endpoints as defined in spec:
  - `POST /api/upload-meals` — accepts file upload or text, returns parsed meals count
  - `POST /api/generate-plan` — triggers plan generation, returns meal plan + grocery list
  - `POST /api/swap-meal` — regenerates plan with exclusions, returns new plan + grocery list
  - `POST /api/approve-plan` — stores approved plan
  - `GET /api/meal-history` — returns all indexed meals
  - `GET /api/current-plan` — returns cached current plan
  - `GET /api/shopping-list` — returns cached shopping list

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routes.py`:

```python
from unittest.mock import patch, MagicMock, AsyncMock
import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_graph():
    with patch("app.api.routes.meal_graph") as mock:
        mock.invoke.return_value = {
            "parsed_meals": [
                {"day": "Saturday", "dishes": ["keema paratha"], "quantity": 5,
                 "prep_notes": "", "tags": ["indian"], "original_text": "Saturday 5 keema paratha"}
            ],
            "embedding_status": "complete",
            "meal_plan": [
                {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha",
                 "prep_time_min": 30, "reason": "past favorite", "ingredients": ["meat", "flour"]}
            ],
            "grocery_list": [
                {"name": "ground meat", "quantity": "1 kg", "category": "protein",
                 "used_in": ["keema paratha"]}
            ],
            "validation_status": "passed",
            "validation_errors": [],
            "validation_warnings": [],
            "shopping_validation_status": "passed",
            "shopping_validation_errors": [],
        }
        yield mock


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_meals_text(client, mock_graph):
    response = client.post(
        "/api/upload-meals",
        data={"text": "Saturday 5 keema paratha"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["meals_indexed"] > 0


def test_upload_meals_file(client, mock_graph):
    file_content = b"Saturday 5 keema paratha. Make cabbage"
    response = client.post(
        "/api/upload-meals",
        files={"file": ("meals.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"


def test_generate_plan(client, mock_graph):
    response = client.post("/api/generate-plan")
    assert response.status_code == 200
    data = response.json()
    assert "meal_plan" in data
    assert "grocery_list" in data
    assert "validation_status" in data


def test_swap_meal(client, mock_graph):
    response = client.post(
        "/api/swap-meal",
        json={"excluded_dishes": ["keema paratha"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "meal_plan" in data


def test_get_meal_history(client):
    with patch("app.api.routes.chroma_service") as mock_chroma:
        mock_chroma.get_all_meals.return_value = [
            {"id": "meal_1", "document": "keema paratha", "metadata": {"dish": "keema paratha"}}
        ]
        response = client.get("/api/meal-history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["meals"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_routes.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `backend/app/api/routes.py`**

```python
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
```

- [ ] **Step 4: Update `backend/app/main.py` to include the router**

Add after the health endpoint:

```python
from app.api.routes import router

app.include_router(router)
```

Full updated `backend/app/main.py`:

```python
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.chroma_db_path, exist_ok=True)
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(title="Meal Planner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


from app.api.routes import router

app.include_router(router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_routes.py -v
```

Expected: 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes.py backend/app/main.py backend/tests/test_routes.py
git commit -m "feat: FastAPI routes — upload, generate, swap, approve, history endpoints"
```

---

### Task 11: Frontend Foundation — Next.js, Tailwind, Types, API Client

**Files:**
- Create: `frontend/` — via `npx create-next-app@latest`
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Modify: `frontend/next.config.js` — add API proxy rewrites

**Interfaces:**
- Produces: TypeScript types `MealEntry`, `PlannedMeal`, `GroceryItem`, `MealPlanResponse`, `UploadResponse`, `AppState`
- Produces: `api` object with methods: `uploadMeals(formData)`, `generatePlan()`, `swapMeal(excludedDishes)`, `approvePlan()`, `getMealHistory()`, `getCurrentPlan()`, `getShoppingList()`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/tguha/claude-workspace/meal-planner-app
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-npm
```

Accept defaults when prompted.

- [ ] **Step 2: Install additional dependencies**

```bash
cd frontend
npm install axios react-dropzone lucide-react
```

- [ ] **Step 3: Configure API proxy in `frontend/next.config.js`**

Replace the contents of `frontend/next.config.ts` (or `next.config.js`):

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
```

- [ ] **Step 4: Create `frontend/src/lib/types.ts`**

```typescript
export interface MealEntry {
  day: string;
  dishes: string[];
  quantity: number;
  prep_notes: string;
  tags: string[];
  original_text: string;
}

export interface PlannedMeal {
  day: string;
  meal_slot: string;
  dish: string;
  prep_time_min: number;
  reason: string;
  ingredients: string[];
}

export interface GroceryItem {
  name: string;
  quantity: string;
  category: string;
  used_in: string[];
}

export interface UploadResponse {
  status: string;
  meals_indexed: number;
  parsed_meals: MealEntry[];
}

export interface MealPlanResponse {
  meal_plan: PlannedMeal[];
  grocery_list: GroceryItem[];
  validation_status: string;
  validation_warnings: string[];
  shopping_validation_status: string;
}

export interface MealHistoryResponse {
  meals: { id: string; document: string; metadata: Record<string, string> }[];
  total: number;
}

export type AppState =
  | "idle"
  | "uploading"
  | "ready"
  | "generating"
  | "plan_ready"
  | "swapping"
  | "approved"
  | "error";
```

- [ ] **Step 5: Create `frontend/src/lib/api.ts`**

```typescript
import axios from "axios";
import {
  UploadResponse,
  MealPlanResponse,
  MealHistoryResponse,
} from "./types";

const client = axios.create({ baseURL: "/api" });

export const api = {
  async uploadMeals(formData: FormData): Promise<UploadResponse> {
    const { data } = await client.post<UploadResponse>(
      "/upload-meals",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  async generatePlan(): Promise<MealPlanResponse> {
    const { data } = await client.post<MealPlanResponse>("/generate-plan");
    return data;
  },

  async swapMeal(excludedDishes: string[]): Promise<MealPlanResponse> {
    const { data } = await client.post<MealPlanResponse>("/swap-meal", {
      excluded_dishes: excludedDishes,
    });
    return data;
  },

  async approvePlan(
    mealPlan?: Record<string, unknown>[]
  ): Promise<{ status: string; meals_saved: number }> {
    const { data } = await client.post("/approve-plan", {
      meal_plan: mealPlan,
    });
    return data;
  },

  async getMealHistory(): Promise<MealHistoryResponse> {
    const { data } = await client.get<MealHistoryResponse>("/meal-history");
    return data;
  },

  async getCurrentPlan(): Promise<MealPlanResponse> {
    const { data } = await client.get<MealPlanResponse>("/current-plan");
    return data;
  },

  async getShoppingList(): Promise<{
    grocery_list: import("./types").GroceryItem[];
    shopping_validation_status: string;
  }> {
    const { data } = await client.get("/shopping-list");
    return data;
  },
};
```

- [ ] **Step 6: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: frontend foundation — Next.js, Tailwind, TypeScript types, API client"
```

---

### Task 12: Meal History Panel Components

**Files:**
- Create: `frontend/src/components/Header.tsx`
- Create: `frontend/src/components/ThemeToggle.tsx`
- Create: `frontend/src/components/FileDropZone.tsx`
- Create: `frontend/src/components/StatusIndicator.tsx`
- Create: `frontend/src/components/MealHistoryPanel.tsx`
- Create: `frontend/src/hooks/useMealHistory.ts`

**Interfaces:**
- Consumes: `api.uploadMeals()` from `src/lib/api`
- Consumes: `UploadResponse`, `AppState` from `src/lib/types`
- Produces: `<MealHistoryPanel onUploadComplete={(response) => void} />` — self-contained upload panel
- Produces: `<Header />` — app header with theme toggle
- Produces: `useMealHistory()` hook returning `{ uploadFile, uploadText, isUploading, uploadedFiles, totalMealsIndexed, error }`

- [ ] **Step 1: Create `frontend/src/components/ThemeToggle.tsx`**

```tsx
"use client";

import { useState, useEffect } from "react";
import { Moon, Sun } from "lucide-react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggle = () => {
    setDark((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle("dark", next);
      localStorage.setItem("theme", next ? "dark" : "light");
      return next;
    });
  };

  return (
    <button
      onClick={toggle}
      className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      aria-label="Toggle theme"
    >
      {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/Header.tsx`**

```tsx
import ThemeToggle from "./ThemeToggle";
import { UtensilsCrossed } from "lucide-react";

export default function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <div className="flex items-center gap-3">
        <UtensilsCrossed className="w-6 h-6 text-emerald-600" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">
          Meal Planner
        </h1>
      </div>
      <ThemeToggle />
    </header>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/StatusIndicator.tsx`**

```tsx
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface Props {
  status: "loading" | "success" | "error" | "idle";
  message?: string;
}

export default function StatusIndicator({ status, message }: Props) {
  if (status === "idle") return null;

  const icons = {
    loading: <Loader2 className="w-4 h-4 animate-spin text-blue-500" />,
    success: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
    error: <AlertCircle className="w-4 h-4 text-red-500" />,
  };

  const colors = {
    loading: "text-blue-600 dark:text-blue-400",
    success: "text-emerald-600 dark:text-emerald-400",
    error: "text-red-600 dark:text-red-400",
  };

  return (
    <div className={`flex items-center gap-2 text-sm ${colors[status]}`}>
      {icons[status]}
      {message && <span>{message}</span>}
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/FileDropZone.tsx`**

```tsx
"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload } from "lucide-react";

interface Props {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED = {
  "text/plain": [".txt"],
  "text/csv": [".csv"],
  "application/json": [".json"],
  "application/pdf": [".pdf"],
};

export default function FileDropZone({ onFileSelect, disabled }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFileSelect(accepted[0]);
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
        ${isDragActive ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" : "border-gray-300 dark:border-gray-600 hover:border-emerald-400"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} />
      <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {isDragActive
          ? "Drop file here..."
          : "Drop files here or click to upload"}
      </p>
      <p className="text-xs text-gray-400 mt-1">.txt .csv .json .pdf</p>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/src/hooks/useMealHistory.ts`**

```typescript
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { UploadResponse } from "@/lib/types";

interface UploadedFile {
  name: string;
  mealsIndexed: number;
}

export function useMealHistory() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [totalMealsIndexed, setTotalMealsIndexed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = async (file: File): Promise<UploadResponse | null> => {
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.uploadMeals(formData);
      setUploadedFiles((prev) => [
        ...prev,
        { name: file.name, mealsIndexed: response.meals_indexed },
      ]);
      setTotalMealsIndexed((prev) => prev + response.meals_indexed);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  const uploadText = async (text: string): Promise<UploadResponse | null> => {
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("text", text);
      const response = await api.uploadMeals(formData);
      setUploadedFiles((prev) => [
        ...prev,
        { name: "Pasted text", mealsIndexed: response.meals_indexed },
      ]);
      setTotalMealsIndexed((prev) => prev + response.meals_indexed);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  return { uploadFile, uploadText, isUploading, uploadedFiles, totalMealsIndexed, error };
}
```

- [ ] **Step 6: Create `frontend/src/components/MealHistoryPanel.tsx`**

```tsx
"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import FileDropZone from "./FileDropZone";
import StatusIndicator from "./StatusIndicator";
import { useMealHistory } from "@/hooks/useMealHistory";
import { UploadResponse } from "@/lib/types";

interface Props {
  onUploadComplete: (response: UploadResponse) => void;
}

export default function MealHistoryPanel({ onUploadComplete }: Props) {
  const [pasteText, setPasteText] = useState("");
  const { uploadFile, uploadText, isUploading, uploadedFiles, totalMealsIndexed, error } =
    useMealHistory();

  const handleFileSelect = async (file: File) => {
    const result = await uploadFile(file);
    if (result) onUploadComplete(result);
  };

  const handleSubmit = async () => {
    if (!pasteText.trim()) return;
    const result = await uploadText(pasteText);
    if (result) {
      setPasteText("");
      onUploadComplete(result);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Meal History Input
      </h2>

      <FileDropZone onFileSelect={handleFileSelect} disabled={isUploading} />

      <div className="mt-4">
        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder="Or paste your meal notes here..."
          rows={4}
          disabled={isUploading}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 text-sm resize-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:opacity-50"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={isUploading || !pasteText.trim()}
        className="mt-3 w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isUploading ? "Analysing..." : "Upload & Analyse"}
      </button>

      <StatusIndicator
        status={isUploading ? "loading" : error ? "error" : "idle"}
        message={isUploading ? "Processing meal notes..." : error || undefined}
      />

      {uploadedFiles.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            Uploaded History
          </h3>
          <ul className="space-y-1">
            {uploadedFiles.map((file, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <FileText className="w-4 h-4 text-emerald-500" />
                {file.name}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-gray-500">
            {totalMealsIndexed} meals indexed
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ frontend/src/hooks/useMealHistory.ts
git commit -m "feat: Meal History Panel — file drop zone, paste textarea, upload hook"
```

---

### Task 13: Meal Plan Panel + Action Buttons

**Files:**
- Create: `frontend/src/components/MealDayCard.tsx`
- Create: `frontend/src/components/ActionButtons.tsx`
- Create: `frontend/src/components/MealPlanPanel.tsx`
- Create: `frontend/src/hooks/useMealPlan.ts`

**Interfaces:**
- Consumes: `api.generatePlan()`, `api.swapMeal()`, `api.approvePlan()` from `src/lib/api`
- Consumes: `PlannedMeal`, `GroceryItem`, `MealPlanResponse`, `AppState` from `src/lib/types`
- Produces: `<MealPlanPanel mealPlan={PlannedMeal[]} appState={AppState} onGenerate onSwap onApprove />`
- Produces: `useMealPlan()` hook returning `{ mealPlan, groceryList, validationStatus, validationWarnings, generate, swap, approve, isLoading, error }`

- [ ] **Step 1: Create `frontend/src/hooks/useMealPlan.ts`**

```typescript
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { PlannedMeal, GroceryItem } from "@/lib/types";

export function useMealPlan() {
  const [mealPlan, setMealPlan] = useState<PlannedMeal[]>([]);
  const [groceryList, setGroceryList] = useState<GroceryItem[]>([]);
  const [validationStatus, setValidationStatus] = useState("");
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.generatePlan();
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      setValidationStatus(data.validation_status);
      setValidationWarnings(data.validation_warnings || []);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate plan");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const swap = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const excludedDishes = mealPlan.map((m) => m.dish);
      const data = await api.swapMeal(excludedDishes);
      setMealPlan(data.meal_plan);
      setGroceryList(data.grocery_list);
      setValidationStatus(data.validation_status);
      setValidationWarnings(data.validation_warnings || []);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to swap plan");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const approve = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.approvePlan();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve plan");
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    mealPlan,
    groceryList,
    validationStatus,
    validationWarnings,
    generate,
    swap,
    approve,
    isLoading,
    error,
  };
}
```

- [ ] **Step 2: Create `frontend/src/components/MealDayCard.tsx`**

```tsx
import { Star, Clock } from "lucide-react";
import { PlannedMeal } from "@/lib/types";

interface Props {
  day: string;
  meals: PlannedMeal[];
}

const SLOT_LABELS: Record<string, string> = {
  breakfast: "B",
  lunch: "L",
  dinner: "D",
};

export default function MealDayCard({ day, meals }: Props) {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
      <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-2">
        {day}
      </h3>
      <div className="space-y-1.5">
        {meals.map((meal, i) => (
          <div key={i} className="flex items-start gap-2 text-sm">
            <span className="font-mono text-xs text-gray-400 w-4 shrink-0 mt-0.5">
              {SLOT_LABELS[meal.meal_slot] || meal.meal_slot[0]?.toUpperCase()}
            </span>
            <span className="text-gray-700 dark:text-gray-300 flex-1">
              {meal.dish}
              {meal.reason === "past favorite" && (
                <Star className="inline w-3.5 h-3.5 ml-1 text-amber-400 fill-amber-400" />
              )}
            </span>
            <span className="flex items-center gap-0.5 text-xs text-gray-400 shrink-0">
              <Clock className="w-3 h-3" />
              {meal.prep_time_min}m
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/ActionButtons.tsx`**

```tsx
import { Check, RefreshCw } from "lucide-react";

interface Props {
  onApprove: () => void;
  onSwap: () => void;
  disabled?: boolean;
  approved?: boolean;
}

export default function ActionButtons({
  onApprove,
  onSwap,
  disabled,
  approved,
}: Props) {
  return (
    <div className="flex gap-3">
      <button
        onClick={onApprove}
        disabled={disabled || approved}
        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Check className="w-4 h-4" />
        {approved ? "Approved" : "Approve"}
      </button>
      <button
        onClick={onSwap}
        disabled={disabled || approved}
        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        Swap Meal Plan
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/MealPlanPanel.tsx`**

```tsx
"use client";

import { Loader2, Sparkles } from "lucide-react";
import MealDayCard from "./MealDayCard";
import ActionButtons from "./ActionButtons";
import StatusIndicator from "./StatusIndicator";
import { PlannedMeal, AppState } from "@/lib/types";

interface Props {
  mealPlan: PlannedMeal[];
  appState: AppState;
  validationWarnings?: string[];
  onGenerate: () => void;
  onSwap: () => void;
  onApprove: () => void;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function MealPlanPanel({
  mealPlan,
  appState,
  validationWarnings,
  onGenerate,
  onSwap,
  onApprove,
}: Props) {
  const groupedByDay = DAYS.map((day) => ({
    day,
    meals: mealPlan.filter((m) => m.day === day),
  })).filter((g) => g.meals.length > 0);

  const isLoadingState = appState === "generating" || appState === "swapping";

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Next Week Meal Plan
      </h2>

      {appState === "idle" && (
        <div className="text-center py-12 text-gray-500">
          <p>Upload your meal history to get started</p>
        </div>
      )}

      {appState === "ready" && (
        <div className="text-center py-12">
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Ready! Click Generate to create your meal plan
          </p>
          <button
            onClick={onGenerate}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Generate Meal Plan
          </button>
        </div>
      )}

      {isLoadingState && (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mx-auto mb-3" />
          <p className="text-gray-500">
            {appState === "swapping" ? "Regenerating plan..." : "Generating your meal plan..."}
          </p>
        </div>
      )}

      {(appState === "plan_ready" || appState === "approved") && groupedByDay.length > 0 && (
        <>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {groupedByDay.map(({ day, meals }) => (
              <MealDayCard key={day} day={day} meals={meals} />
            ))}
          </div>

          {validationWarnings && validationWarnings.length > 0 && (
            <div className="mt-3">
              {validationWarnings.map((w, i) => (
                <StatusIndicator key={i} status="error" message={w} />
              ))}
            </div>
          )}

          <div className="mt-4">
            <ActionButtons
              onApprove={onApprove}
              onSwap={onSwap}
              disabled={isLoadingState}
              approved={appState === "approved"}
            />
          </div>
        </>
      )}

      {appState === "error" && (
        <div className="text-center py-12">
          <StatusIndicator status="error" message="Something went wrong. Please try again." />
          <button
            onClick={onGenerate}
            className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/MealDayCard.tsx frontend/src/components/ActionButtons.tsx frontend/src/components/MealPlanPanel.tsx frontend/src/hooks/useMealPlan.ts
git commit -m "feat: Meal Plan Panel — 7-day display, approve/swap buttons, day cards"
```

---

### Task 14: Shopping List Panel

**Files:**
- Create: `frontend/src/components/GroceryCategory.tsx`
- Create: `frontend/src/components/ShoppingListPanel.tsx`

**Interfaces:**
- Consumes: `GroceryItem`, `AppState` from `src/lib/types`
- Produces: `<ShoppingListPanel groceryList={GroceryItem[]} appState={AppState} />`

- [ ] **Step 1: Create `frontend/src/components/GroceryCategory.tsx`**

```tsx
import { GroceryItem } from "@/lib/types";

interface Props {
  category: string;
  items: GroceryItem[];
}

const CATEGORY_LABELS: Record<string, string> = {
  produce: "Produce",
  protein: "Protein",
  dairy: "Dairy",
  grains_pantry: "Grains & Pantry",
  spices: "Spices",
};

const CATEGORY_COLORS: Record<string, string> = {
  produce: "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
  protein: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
  dairy: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
  grains_pantry: "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800",
  spices: "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800",
};

export default function GroceryCategory({ category, items }: Props) {
  return (
    <div className={`rounded-lg border p-3 ${CATEGORY_COLORS[category] || "bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-700"}`}>
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
        {CATEGORY_LABELS[category] || category}
      </h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-600 dark:text-gray-400">
            {item.name}{" "}
            <span className="text-gray-400 dark:text-gray-500">
              ({item.quantity})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/ShoppingListPanel.tsx`**

```tsx
"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import GroceryCategory from "./GroceryCategory";
import { GroceryItem, AppState } from "@/lib/types";

interface Props {
  groceryList: GroceryItem[];
  appState: AppState;
}

const CATEGORY_ORDER = ["produce", "protein", "dairy", "grains_pantry", "spices"];

export default function ShoppingListPanel({ groceryList, appState }: Props) {
  const [copied, setCopied] = useState(false);

  if (appState === "idle" || appState === "uploading" || appState === "ready") {
    return null;
  }

  const grouped = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    items: groceryList.filter((item) => item.category === cat),
  })).filter((g) => g.items.length > 0);

  const uncategorized = groceryList.filter(
    (item) => !CATEGORY_ORDER.includes(item.category)
  );
  if (uncategorized.length > 0) {
    grouped.push({ category: "other", items: uncategorized });
  }

  const copyToClipboard = async () => {
    const text = grouped
      .map((g) => {
        const header = g.category.charAt(0).toUpperCase() + g.category.slice(1);
        const items = g.items.map((item) => `  - ${item.name} (${item.quantity})`).join("\n");
        return `${header}:\n${items}`;
      })
      .join("\n\n");

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isTentative = appState !== "approved";

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 ${isTentative ? "opacity-75" : ""}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Shopping List
          {isTentative && (
            <span className="ml-2 text-xs font-normal text-gray-400">(tentative)</span>
          )}
        </h2>
        <button
          onClick={copyToClipboard}
          disabled={isTentative}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" /> Copy List
            </>
          )}
        </button>
      </div>

      {groceryList.length === 0 ? (
        <p className="text-center text-gray-500 py-6 text-sm">
          Shopping list will appear here after plan is generated
        </p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {grouped.map(({ category, items }) => (
            <GroceryCategory key={category} category={category} items={items} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/GroceryCategory.tsx frontend/src/components/ShoppingListPanel.tsx
git commit -m "feat: Shopping List Panel — categorized grocery list with copy button"
```

---

### Task 15: Dashboard Integration — Wire All Panels

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Consumes: `<Header />`, `<MealHistoryPanel />`, `<MealPlanPanel />`, `<ShoppingListPanel />`
- Consumes: `useMealPlan()` hook
- Produces: Complete working dashboard at `http://localhost:3000`

- [ ] **Step 1: Update `frontend/src/app/globals.css`**

Keep Tailwind directives, remove the default Next.js template styles. Replace entire file with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-white;
}
```

- [ ] **Step 2: Update `frontend/src/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meal Planner",
  description: "AI-powered meal planning with shopping lists",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Update `frontend/src/app/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import Header from "@/components/Header";
import MealHistoryPanel from "@/components/MealHistoryPanel";
import MealPlanPanel from "@/components/MealPlanPanel";
import ShoppingListPanel from "@/components/ShoppingListPanel";
import { useMealPlan } from "@/hooks/useMealPlan";
import { AppState } from "@/lib/types";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("idle");
  const {
    mealPlan,
    groceryList,
    validationWarnings,
    generate,
    swap,
    approve,
    isLoading,
  } = useMealPlan();

  const handleUploadComplete = () => {
    setAppState("ready");
  };

  const handleGenerate = async () => {
    setAppState("generating");
    const result = await generate();
    setAppState(result ? "plan_ready" : "error");
  };

  const handleSwap = async () => {
    setAppState("swapping");
    const result = await swap();
    setAppState(result ? "plan_ready" : "error");
  };

  const handleApprove = async () => {
    const success = await approve();
    if (success) setAppState("approved");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <MealHistoryPanel onUploadComplete={handleUploadComplete} />
          </div>
          <div className="lg:col-span-2">
            <MealPlanPanel
              mealPlan={mealPlan}
              appState={appState}
              validationWarnings={validationWarnings}
              onGenerate={handleGenerate}
              onSwap={handleSwap}
              onApprove={handleApprove}
            />
          </div>
        </div>
        <div className="mt-6">
          <ShoppingListPanel groceryList={groceryList} appState={appState} />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 5: Start both servers and verify in browser**

Terminal 1 (backend):
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` in a browser. Verify:
- Header displays with theme toggle
- Meal History Input panel shows with drop zone and textarea
- Meal Plan panel shows "Upload your meal history to get started"
- Shopping List panel is hidden
- Theme toggle switches between light and dark mode

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/
git commit -m "feat: dashboard integration — wire all panels into main page"
```

---

### Task 16: End-to-End Smoke Test

**Files:**
- Create: `backend/tests/test_integration.py`

**Interfaces:**
- Consumes: All backend components
- Produces: Verified working pipeline

- [ ] **Step 1: Write integration test**

Create `backend/tests/test_integration.py`:

```python
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_all_llm_calls():
    with patch("app.agents.history_analyser.claude_service") as mock_hist, \
         patch("app.agents.meal_planner.claude_service") as mock_plan, \
         patch("app.agents.validator.claude_service") as mock_val, \
         patch("app.agents.shopping_organiser.claude_service") as mock_shop, \
         patch("app.agents.history_analyser.chroma_service") as mock_chroma_hist, \
         patch("app.agents.meal_planner.chroma_service") as mock_chroma_plan, \
         patch("app.agents.validator.chroma_service") as mock_chroma_val:

        mock_hist.call_json.return_value = [
            {"day": "Saturday", "dishes": ["keema paratha"], "quantity": 5,
             "prep_notes": "", "tags": ["indian", "protein"]}
        ]

        mock_chroma_plan.query_meals.return_value = [
            {"id": "m1", "document": "keema paratha", "metadata": {"day": "Saturday", "dish": "keema paratha", "tags": "indian"}}
        ]

        mock_plan.call_json.return_value = [
            {"day": "Monday", "meal_slot": "breakfast", "dish": "Oatmeal", "prep_time_min": 10,
             "reason": "new for variety", "ingredients": ["oats", "milk"]},
            {"day": "Monday", "meal_slot": "lunch", "dish": "keema paratha", "prep_time_min": 30,
             "reason": "past favorite", "ingredients": ["meat", "flour"]},
            {"day": "Monday", "meal_slot": "dinner", "dish": "Grilled chicken", "prep_time_min": 25,
             "reason": "new for variety", "ingredients": ["chicken", "rice"]},
        ]

        mock_val.call_json.return_value = {"is_valid": True, "errors": [], "warnings": []}
        mock_chroma_val.meal_exists.return_value = True

        mock_shop.call_json.return_value = [
            {"name": "oats", "quantity": "500g", "category": "grains_pantry", "used_in": ["Oatmeal"]},
            {"name": "chicken", "quantity": "1 kg", "category": "protein", "used_in": ["Grilled chicken"]},
        ]

        yield


def test_full_flow_upload_then_generate(client, mock_all_llm_calls):
    upload_resp = client.post("/api/upload-meals", data={"text": "Saturday 5 keema paratha"})
    assert upload_resp.status_code == 200
    assert upload_resp.json()["status"] == "complete"

    gen_resp = client.post("/api/generate-plan")
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert len(data["meal_plan"]) == 3
    assert len(data["grocery_list"]) == 2
    assert data["validation_status"] == "passed"
```

- [ ] **Step 2: Run the integration test**

```bash
cd backend
pytest tests/test_integration.py -v
```

Expected: PASS

- [ ] **Step 3: Run all backend tests**

```bash
cd backend
pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_integration.py
git commit -m "test: end-to-end integration test — upload and generate flow"
```

---

### Task 17: Gitignore, Uploads Directory, Data Directory

**Files:**
- Create: `backend/uploads/.gitkeep`
- Create: `backend/data/.gitkeep`
- Modify: `.gitignore` (root level)

**Interfaces:**
- Produces: Clean repository structure with proper ignore patterns

- [ ] **Step 1: Create placeholder files for git-tracked empty dirs**

```bash
touch backend/uploads/.gitkeep
touch backend/data/.gitkeep
```

- [ ] **Step 2: Create root `.gitignore`**

```
# Python
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/

# ChromaDB data
backend/data/chroma_db/

# Uploads
backend/uploads/*
!backend/uploads/.gitkeep

# Node
node_modules/
.next/

# IDE
.vscode/
.idea/

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore backend/uploads/.gitkeep backend/data/.gitkeep
git commit -m "chore: gitignore, empty directory placeholders"
```
