# Meal Planner App — Design Specification

A multi-agent meal planning application that analyzes past meal history, generates weekly meal plans, and produces organized shopping lists. Built with Python (FastAPI + LangGraph) backend, Next.js frontend, ChromaDB for vector storage, and Claude API for agent reasoning.

---

## Section 1: System Architecture

### Overview

Four agents orchestrated via a LangGraph StateGraph with conditional edges. A Next.js frontend communicates with a FastAPI backend over REST. ChromaDB stores meal history embeddings for RAG retrieval.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                              │
│  ┌───────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ Upload/Paste  │  │  Meal Plan View  │  │  Shopping List View   │  │
│  │ Panel         │  │  + Approve/Swap  │  │  (validated)          │  │
│  └───────┬───────┘  └────────┬─────────┘  └───────────┬───────────┘  │
│          │                   │                        │              │
└──────────┼───────────────────┼────────────────────────┼──────────────┘
           │                   │                        │
           ▼                   ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                                │
│                                                                      │
│  POST /upload-meals      POST /generate-plan                         │
│  POST /swap-meal         GET  /shopping-list                         │
│  GET  /meal-history      GET  /current-plan                          │
│  POST /approve-plan                                                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  LangGraph StateGraph                          │  │
│  │                                                                │  │
│  │  ┌──────────────┐    ┌──────────────┐                          │  │
│  │  │   History    │    │    Meal      │                          │  │
│  │  │  Analyser    │───▶│   Planner    │                          │  │
│  │  │   Agent      │    │    Agent     │                          │  │
│  │  └──────┬───────┘    └──────┬───────┘                          │  │
│  │         │                   │                                  │  │
│  │         ▼                   ▼                                  │  │
│  │    ┌─────────┐        ┌──────────────┐                         │  │
│  │    │ChromaDB │        │  Validator   │                         │  │
│  │    │(Vector  │        │    Agent     │◀─── Swap Edge           │  │
│  │    │  DB)    │        └──────┬───────┘                          │  │
│  │    └─────────┘          pass │ fail                            │  │
│  │                          ▼   └──▶ back to Meal Planner         │  │
│  │                   ┌──────────────┐                             │  │
│  │                   │   Shopping   │                             │  │
│  │                   │  Organiser   │                             │  │
│  │                   │    Agent     │                             │  │
│  │                   └──────┬───────┘                             │  │
│  │                          │                                     │  │
│  │                          ▼                                     │  │
│  │                   ┌──────────────┐                             │  │
│  │                   │  Validator   │                             │  │
│  │                   │  (2nd pass)  │                             │  │
│  │                   └──────────────┘                             │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│              Claude API (claude-sonnet-4-20250514)                    │
└──────────────────────────────────────────────────────────────────────┘
```

### LangGraph Flow

```
                    ┌─────────────┐
                    │   Upload    │
                    │  Meal Logs  │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │  History    │──── embed + store ───▶ ChromaDB
                    │  Analyser   │
                    └──────┬──────┘
                           ▼
              ┌───▶┌─────────────┐
              │    │   Meal      │◀── RAG retrieval ◀── ChromaDB
              │    │  Planner    │
              │    └──────┬──────┘
              │           ▼
              │    ┌─────────────┐
   retry      │    │ Validator   │  checks: dishes in history?,
   (max 2)    │    │ (meal plan) │  no repeats?, balanced nutrition?
              │    └──────┬──────┘
              │      fail │ pass
              └───────────┘  │
                             ▼
                    ┌─────────────┐
                    │  Shopping   │
                    │  Organiser  │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ Validator   │  checks: ingredients match meals?,
                    │(shop list)  │  no phantoms?, sane quantities?
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │  Display    │──▶ User: Approve / Swap
                    └──────┬──────┘
                      swap │ approve
                      ▼    ▼
                 back to   store plan
                 Planner   in history
```

### Key Components

- **Next.js frontend** — 3-panel dashboard: upload area, meal plan display with approve/swap, shopping list
- **FastAPI backend** — REST API exposing agent actions
- **LangGraph StateGraph** — orchestrates the 4 agents with conditional edges
- **ChromaDB** — local vector store for meal history (with default `all-MiniLM-L6-v2` embeddings)
- **Claude API** — powers each agent's reasoning (parsing, planning, validation, ingredient extraction)

---

## Section 2: Agent Details

### Agent 1: History Analyser Agent

**Purpose:** Parse freeform meal notes and uploaded files, extract structured data, embed into ChromaDB for RAG retrieval.

**Supported inputs:**
- Paste text — directly in the dashboard textarea
- File upload — `.txt`, `.csv`, `.json`, `.pdf` files

**File processing pipeline:**

```
File Upload (.txt/.csv/.json/.pdf)
         │
         ▼
┌─────────────────┐
│  File Parser     │  ← part of History Analyser Agent
│                  │
│  .txt  → read as raw text
│  .csv  → pandas parse → extract meal columns
│  .json → parse structured records directly
│  .pdf  → extract text via PyPDF2
└────────┬────────┘
         │
         ▼
   Normalized raw text
         │
         ▼
   Claude extracts structured MealEntry records
         │
         ▼
   Embed + store in ChromaDB
```

**Input example:** `"Saturday 5 keema paratha. Make cabbage"`

**Claude extracts structured records:**

```json
{
  "day": "Saturday",
  "dishes": ["keema paratha", "cabbage"],
  "quantity": 5,
  "prep_notes": "Make cabbage",
  "tags": ["indian", "paratha", "protein", "vegetable"]
}
```

**Processing steps:**
1. If file upload: parse file to raw text via File Parser
2. Send raw text to Claude to extract structured `MealEntry` records
3. Each dish gets embedded via ChromaDB's default embedder (`all-MiniLM-L6-v2`)
4. Stored with metadata: day of week, frequency count, tags, original text
5. On repeated uploads, frequency counts increment — building a preference profile

**RAG retrieval interface:** Other agents query ChromaDB with natural language (e.g., "high-protein Indian dishes eaten on weekends") and get back ranked results with metadata.

### Agent 2: Meal Planner Agent

**Purpose:** Generate a 7-day meal plan using RAG context from history + Claude reasoning.

**Process:**
1. Retrieve top-k relevant meals from ChromaDB (favorites, frequent dishes, tag variety)
2. Build a prompt with: retrieved history, nutritional balance rules, no-repeat constraint, day-of-week patterns from past logs
3. Claude generates a 7-day plan (breakfast/lunch/dinner or however many meals per day the history suggests)
4. Each meal includes: dish name, which meal slot, estimated prep time, why it was chosen (past favorite vs. new suggestion for variety)

**Nutritional balance rules:**
- General healthy balance: mix of protein, carbs, and vegetables
- No dish repeats within the same week
- Variety across cuisine types and cooking methods

**Swap behavior:** When user clicks "Swap" on the plan:
- The rejected meals are added to an exclusion list in the graph state
- Meal Planner re-runs with the exclusion list, generating alternatives
- Flows through Validator again before display

### Agent 3: Shopping Organiser Agent

**Purpose:** Extract raw ingredients from the validated meal plan, deduplicate, and organize into a grocery list.

**Process:**
1. Takes the validated meal plan as input
2. Claude extracts ingredients per dish with estimated quantities
3. Deduplicates and aggregates (e.g., two dishes needing onions → combined quantity)
4. Groups by grocery store section: Produce, Protein, Dairy, Grains/Pantry, Spices

**Output format:**

```
Produce:      cabbage (1 head), onions (2 kg), tomatoes (500g)
Protein:      ground meat (1 kg), chicken breast (1 kg)
Dairy:        yogurt (500ml), butter (200g)
Grains/Pantry: flour (1 kg), rice (2 kg), oats (500g)
Spices:       cumin, turmeric, red chili, garam masala
```

### Agent 4: Validator Agent

**Purpose:** Ground-truth checking at two points in the pipeline to prevent hallucination and ensure accuracy.

**Validation pass 1 — Meal Plan:**
- Query ChromaDB to verify "past favorites" actually exist in history
- Check no dish appears twice in the same week
- Check protein/carb/veggie balance across the week (at least 1 veggie dish per day, protein in every plan)
- If fail: return specific feedback to Meal Planner ("replace dish X, not found in history"). Max 2 retries, then pass with warning flags.

**Validation pass 2 — Shopping List:**
- Cross-reference every ingredient against the meal plan dishes
- Flag any ingredient that doesn't map to a meal
- Sanity-check quantities (basic heuristics — flag anything over 5kg for a single item, etc.)
- If fail: return to Shopping Organiser with corrections. Max 2 retries.

**State fields:**

```python
validation_status: "passed" | "failed" | "passed_with_warnings"
validation_errors: list[str]
retry_count: int
```

---

## Section 3: LangGraph State Schema & Data Flow

### Shared State (TypedDict)

The single state object that flows through the entire LangGraph graph. Every node reads from and writes to it.

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
    meal_slot: str  # "breakfast", "lunch", "dinner"
    dish: str
    prep_time_min: int
    reason: str  # "past favorite" | "new for variety"
    ingredients: list[str]

class GroceryItem(TypedDict):
    name: str
    quantity: str
    category: str  # "produce", "protein", "dairy", "grains_pantry", "spices"
    used_in: list[str]  # which dishes need this

class MealPlannerState(TypedDict):
    # Input
    raw_text: str
    uploaded_file_path: str | None
    input_source: Literal["paste", "file_upload"]
    file_type: str | None  # "txt", "csv", "json", "pdf"
    action: Literal["upload", "generate", "swap", "approve"]

    # History Analyser output
    parsed_meals: list[MealEntry]
    embedding_status: str

    # Meal Planner output
    meal_plan: list[PlannedMeal]
    excluded_dishes: list[str]  # from swap rejections

    # Validator output (meal plan)
    validation_status: Literal["passed", "failed", "passed_with_warnings"]
    validation_errors: list[str]
    validation_warnings: list[str]
    retry_count: int

    # Shopping Organiser output
    grocery_list: list[GroceryItem]

    # Validator output (shopping list)
    shopping_validation_status: Literal["passed", "failed", "passed_with_warnings"]
    shopping_validation_errors: list[str]
    shopping_retry_count: int
```

### Graph Definition

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(MealPlannerState)

# Nodes
graph.add_node("history_analyser", history_analyser_node)
graph.add_node("meal_planner", meal_planner_node)
graph.add_node("meal_validator", meal_validator_node)
graph.add_node("shopping_organiser", shopping_organiser_node)
graph.add_node("shopping_validator", shopping_validator_node)

# Entry routing based on action
graph.set_conditional_entry_point(route_by_action)
# "upload"   → history_analyser
# "generate" → meal_planner
# "swap"     → meal_planner (with excluded_dishes populated)
# "approve"  → END (store to history)

# Edges
graph.add_edge("history_analyser", END)

graph.add_edge("meal_planner", "meal_validator")

graph.add_conditional_edges("meal_validator", route_after_meal_validation)
# "passed" / "passed_with_warnings" → shopping_organiser
# "failed" + retry_count < 2        → meal_planner (retry)
# "failed" + retry_count >= 2       → shopping_organiser (pass with warnings)

graph.add_edge("shopping_organiser", "shopping_validator")

graph.add_conditional_edges("shopping_validator", route_after_shopping_validation)
# "passed" / "passed_with_warnings" → END
# "failed" + retry_count < 2        → shopping_organiser (retry)
# "failed" + retry_count >= 2       → END (pass with warnings)
```

### Data Flow

```
USER ACTION          STATE MUTATION                    SIDE EFFECTS
───────────          ──────────────                    ────────────

Upload text  ──▶  raw_text = "Sat 5 keema..."
 or file          action = "upload"
                  input_source = "paste" | "file_upload"
                       │
                       ▼
              history_analyser_node
                  parsed_meals = [{day, dishes...}]    ChromaDB.add(embeddings)
                  embedding_status = "complete"
                       │
                       ▼ END

Generate     ──▶  action = "generate"
                  excluded_dishes = []
                       │
                       ▼
              meal_planner_node                        ChromaDB.query(preferences)
                  meal_plan = [7 days x meals]
                       │
                       ▼
              meal_validator_node                      ChromaDB.get(verify dishes)
                  validation_status = "passed"
                       │
                       ▼
              shopping_organiser_node
                  grocery_list = [{name, qty, cat}]
                       │
                       ▼
              shopping_validator_node
                  shopping_validation_status = "passed"
                       │
                       ▼ END → return to frontend

Swap         ──▶  action = "swap"
                  excluded_dishes += [rejected dishes]
                       │
                       ▼
              meal_planner_node (re-run, avoids excluded)
                       │
                       ▼  ... same validation → shopping flow

Approve      ──▶  action = "approve"                   ChromaDB.add(approved plan)
                       │
                       ▼ END
```

### API to Graph Mapping

| API Endpoint | Graph Action | Entry Node |
|---|---|---|
| `POST /upload-meals` | `action="upload"` | history_analyser |
| `POST /generate-plan` | `action="generate"` | meal_planner |
| `POST /swap-meal` | `action="swap"` | meal_planner |
| `POST /approve-plan` | `action="approve"` | END (store) |
| `GET /meal-history` | Direct ChromaDB query | N/A |
| `GET /current-plan` | Return cached state | N/A |
| `GET /shopping-list` | Return cached state | N/A |

---

## Section 4: Frontend Dashboard Design

### Layout: Three-Panel Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│  Meal Planner                                       [Dark/Light]     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────┐  ┌──────────────────────────────────┐  │
│  │   MEAL HISTORY INPUT    │  │      NEXT WEEK MEAL PLAN         │  │
│  │                         │  │                                  │  │
│  │  ┌───────────────────┐  │  │  ┌────────────────────────────┐  │  │
│  │  │  Drop files here  │  │  │  │ Monday                     │  │  │
│  │  │  or click to      │  │  │  │  B: Oatmeal + fruit        │  │  │
│  │  │  upload            │  │  │  │  L: Keema paratha (fav)   │  │  │
│  │  │  .txt .csv .json  │  │  │  │  D: Grilled chicken + rice │  │  │
│  │  │  .pdf             │  │  │  ├────────────────────────────┤  │  │
│  │  └───────────────────┘  │  │  │ Tuesday                    │  │  │
│  │                         │  │  │  B: Paratha + yogurt        │  │  │
│  │  ┌───────────────────┐  │  │  │  L: Dal + rice              │  │  │
│  │  │ Or paste your     │  │  │  │  D: Cabbage stir-fry       │  │  │
│  │  │ meal notes here   │  │  │  ├────────────────────────────┤  │  │
│  │  │                   │  │  │  │ Wednesday                  │  │  │
│  │  │                   │  │  │  │  ...                        │  │  │
│  │  │                   │  │  │  │                             │  │  │
│  │  └───────────────────┘  │  │  │  (scrollable 7 days)       │  │  │
│  │                         │  │  │                             │  │  │
│  │  [Upload & Analyse]     │  │  └────────────────────────────┘  │  │
│  │                         │  │                                  │  │
│  │  ── Uploaded History ── │  │  ┌────────┐  ┌────────────────┐  │  │
│  │  meal-log-aug.txt       │  │  │Approve │  │ Swap Meal Plan │  │  │
│  │  meal-log-jul.txt       │  │  └────────┘  └────────────────┘  │  │
│  │  12 meals indexed       │  │                                  │  │
│  │                         │  │                                  │  │
│  └─────────────────────────┘  └──────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                     SHOPPING LIST                              │  │
│  │                                                                │  │
│  │  Produce          Protein          Dairy         Grains        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌───────────┐  ┌──────────┐  │  │
│  │  │ Cabbage 1  │  │ Ground     │  │ Yogurt    │  │ Rice 2kg │  │  │
│  │  │ Onions 2kg │  │ meat 1kg   │  │ 500ml     │  │ Flour    │  │  │
│  │  │ Tomatoes   │  │ Chicken    │  │ Butter    │  │ 1kg      │  │  │
│  │  │ 500g       │  │ breast 1kg │  │ 200g      │  │ Oats     │  │  │
│  │  └────────────┘  └────────────┘  └───────────┘  └──────────┘  │  │
│  │                                                                │  │
│  │  Spices: cumin, turmeric, red chili, garam masala             │  │
│  │                                                    [Copy List] │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Description |
|---|---|
| **Header** | App title, dark/light theme toggle |
| **Meal History Input Panel** | Drag-and-drop file zone (.txt, .csv, .json, .pdf) + paste textarea + "Upload & Analyse" button. Shows list of previously uploaded files and total meals indexed in ChromaDB. |
| **Meal Plan Panel** | Displays 7-day plan with meal slots (Breakfast/Lunch/Dinner). Past favorites marked. Scrollable. |
| **Approve / Swap Buttons** | Two action buttons below the meal plan. "Approve" stores the plan and finalizes the shopping list. "Swap" sends excluded dishes back to the Meal Planner for regeneration via the LangGraph swap edge. |
| **Shopping List Panel** | Grouped by grocery section (Produce, Protein, Dairy, Grains/Pantry, Spices). Each item shows quantity and which dishes use it. "Copy List" button for clipboard export. Only appears after a plan is generated. |

### User Interaction Flow

```
1. First visit (empty state)
   -> Meal Plan panel shows: "Upload your meal history to get started"
   -> Shopping List panel hidden

2. User uploads/pastes meal logs -> clicks "Upload & Analyse"
   -> Loading spinner on input panel
   -> History panel updates: "filename, X meals indexed"
   -> Meal Plan panel shows: "Ready! Click Generate to create your meal plan"
   -> [Generate Meal Plan] button appears

3. User clicks "Generate Meal Plan"
   -> Loading state on meal plan panel
   -> Plan appears with 7 days x meals
   -> Approve / Swap buttons appear
   -> Shopping list panel appears (tentative, grayed)

4. User clicks "Swap"
   -> Current plan grays out with "Regenerating..." overlay
   -> New plan replaces it (validated by Validator Agent)
   -> Shopping list updates

5. User clicks "Approve"
   -> Plan locks (no more swap)
   -> Shopping list becomes final with full styling
   -> "Copy List" button activates
   -> Success toast: "Meal plan approved and saved!"
```

### Frontend States

```
idle          -> no history uploaded yet
uploading     -> file/text being processed by History Analyser
ready         -> history indexed, waiting for user to generate
generating    -> Meal Planner + Validator + Shopping Organiser running
plan_ready    -> plan displayed, awaiting approve/swap
swapping      -> regenerating after swap click
approved      -> plan finalized, shopping list locked
error         -> any agent failure, with retry option
```

---

## Section 5: Project Structure & Tech Stack

### Directory Layout

```
meal-planner-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, CORS, lifespan
│   │   ├── config.py                # env vars, API keys, ChromaDB path
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py            # all REST endpoints
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── state.py             # MealPlannerState TypedDict
│   │   │   ├── graph.py             # LangGraph StateGraph definition
│   │   │   ├── history_analyser.py  # node: parse + embed meals
│   │   │   ├── meal_planner.py      # node: RAG retrieval + plan generation
│   │   │   ├── validator.py         # node: ground-truth checks
│   │   │   └── shopping_organiser.py # node: ingredient extraction + grouping
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── chromadb_service.py  # ChromaDB client, collection management
│   │   │   ├── claude_service.py    # Anthropic SDK wrapper
│   │   │   └── file_parser.py       # .txt/.csv/.json/.pdf -> raw text
│   │   │
│   │   └── prompts/
│   │       ├── history_analyser.py  # prompt templates for meal parsing
│   │       ├── meal_planner.py      # prompt templates for plan generation
│   │       ├── validator.py         # prompt templates for validation checks
│   │       └── shopping_organiser.py # prompt templates for ingredient extraction
│   │
│   ├── data/
│   │   └── chroma_db/              # ChromaDB persistent storage
│   │
│   ├── uploads/                    # temporary uploaded files
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # root layout, theme provider
│   │   │   ├── page.tsx            # dashboard page
│   │   │   └── globals.css
│   │   │
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── MealHistoryPanel.tsx    # upload + paste + file list
│   │   │   ├── FileDropZone.tsx        # drag-and-drop upload
│   │   │   ├── MealPlanPanel.tsx       # 7-day plan display
│   │   │   ├── MealDayCard.tsx         # single day's meals
│   │   │   ├── ActionButtons.tsx       # approve / swap buttons
│   │   │   ├── ShoppingListPanel.tsx   # grouped grocery list
│   │   │   ├── GroceryCategory.tsx     # single category card
│   │   │   ├── StatusIndicator.tsx     # loading / success / error states
│   │   │   └── ThemeToggle.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useMealHistory.ts      # upload + history API calls
│   │   │   ├── useMealPlan.ts         # generate + swap + approve
│   │   │   └── useShoppingList.ts     # fetch shopping list
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # axios/fetch wrapper for backend
│   │   │   └── types.ts              # TypeScript types matching backend
│   │   │
│   │   └── styles/
│   │       └── theme.ts              # dark/light theme config
│   │
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── tailwind.config.js
│
├── docs/
│   └── architecture.md              # architecture overview
│
├── .gitignore
└── README.md
```

### Tech Stack & Dependencies

**Backend (requirements.txt):**

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ^0.115 | REST API framework |
| `uvicorn` | ^0.30 | ASGI server |
| `anthropic` | ^0.52 | Claude API SDK |
| `langgraph` | ^0.4 | Agent orchestration graph |
| `langchain-anthropic` | ^0.3 | LangChain Claude integration for LangGraph |
| `chromadb` | ^0.5 | Vector DB with built-in embeddings |
| `python-multipart` | ^0.0.9 | File upload handling in FastAPI |
| `pypdf2` | ^3.0 | PDF text extraction |
| `pandas` | ^2.2 | CSV parsing |
| `pydantic` | ^2.9 | Request/response validation |
| `python-dotenv` | ^1.0 | Environment variable loading |

**Frontend (package.json):**

| Package | Purpose |
|---|---|
| `next` | React framework (App Router) |
| `react` / `react-dom` | UI library |
| `tailwindcss` | Utility-first CSS |
| `axios` | HTTP client for API calls |
| `react-dropzone` | Drag-and-drop file upload |
| `lucide-react` | Icon library |

### Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...
CHROMA_DB_PATH=./data/chroma_db
CHROMA_COLLECTION_NAME=meal_history
UPLOAD_DIR=./uploads
CLAUDE_MODEL=claude-sonnet-4-20250514
```

### Running the App

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # -> http://localhost:3000
```

Frontend proxies API calls to `http://localhost:8000` via Next.js `rewrites` in `next.config.js`.
