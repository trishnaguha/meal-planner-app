# Meal Planner App

AI-powered meal planning application that analyzes your past meal history, generates balanced weekly meal plans, and produces organized grocery shopping lists.

Built with a multi-agent architecture using LangGraph, ChromaDB for vector storage with RAG retrieval, Claude API for reasoning, and a Next.js dashboard.

## Architecture

Four agents orchestrated via a LangGraph StateGraph with conditional edges:

```
Upload Meal Logs
       |
       v
 History Analyser ──── embed + store ───> ChromaDB
       |
       v
  Meal Planner <──── RAG retrieval <──── ChromaDB
       |
       v
   Validator ──── fail ──> back to Meal Planner (max 2 retries)
       | pass
       v
Shopping Organiser
       |
       v
   Validator ──── fail ──> back to Shopping Organiser (max 2 retries)
       | pass
       v
    Display ──> User: Approve / Swap
```

| Agent | Purpose |
|---|---|
| **History Analyser** | Parses freeform meal notes (text or file upload), extracts structured records, embeds into ChromaDB |
| **Meal Planner** | Retrieves full meal history, generates a 7-day lunch and dinner plan prioritizing the user's own dishes |
| **Validator** | Ground-truth checks at two points — verifies dishes exist in history, allows up to 2 repeats per week, balanced nutrition, valid ingredients |
| **Shopping Organiser** | Extracts ingredients from the plan, deduplicates, groups by grocery section |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend | Python, FastAPI |
| Agent Orchestration | LangGraph StateGraph |
| LLM | Claude API (Sonnet) via Anthropic SDK / Vertex AI |
| Vector Database | ChromaDB (local, persistent) |
| Embeddings | ChromaDB default (all-MiniLM-L6-v2) |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/) or Google Cloud project with Vertex AI access

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY, or set USE_VERTEX=true with VERTEX_PROJECT_ID

uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

1. **Upload meal history** — Paste text notes (e.g., `Saturday 5 keema paratha. Make cabbage`) or upload a file (.txt, .csv, .json, .pdf) in the left panel. Large files are automatically chunked for reliable parsing.
2. **Generate meal plan** — Click "Generate Meal Plan" to create a balanced 7-day lunch and dinner plan based on your history. Weekday meals (Mon–Fri) are drawn from your uploaded history; weekend meals (Sat–Sun) may include new dishes for variety.
3. **Review** — The plan shows lunch and dinner for each day. Dishes from your history are marked with a star.
4. **Swap or Approve** — Click "Swap Meal Plan" to regenerate with different dishes, or "Approve" to finalize
5. **Shopping list** — A categorized grocery list appears automatically, grouped by Produce, Protein, Dairy, Grains & Pantry, and Spices. Copy it with one click

Your meal history is persisted in ChromaDB on disk (`backend/data/chroma_db/`). After the first upload, you don't need to re-upload — the app detects existing data on page load and shows the Generate button immediately.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload-meals` | Upload file or paste text for history analysis |
| POST | `/api/generate-plan` | Generate a new 7-day meal plan |
| POST | `/api/swap-meal` | Regenerate plan excluding rejected dishes |
| POST | `/api/approve-plan` | Approve and store the finalized plan |
| GET | `/api/meal-history` | Query indexed meal history |
| GET | `/api/current-plan` | Get the current meal plan |
| GET | `/api/shopping-list` | Get the current shopping list |

## Project Structure

```
meal-planner-app/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app
│   │   ├── config.py                  # Settings
│   │   ├── api/routes.py              # REST endpoints
│   │   ├── agents/
│   │   │   ├── state.py               # Shared state schema
│   │   │   ├── graph.py               # LangGraph StateGraph
│   │   │   ├── history_analyser.py    # Parse + embed meals
│   │   │   ├── meal_planner.py        # RAG-driven planning
│   │   │   ├── validator.py           # Ground-truth checks
│   │   │   └── shopping_organiser.py  # Ingredient extraction
│   │   ├── services/
│   │   │   ├── chromadb_service.py    # Vector DB operations
│   │   │   ├── claude_service.py      # Anthropic SDK wrapper
│   │   │   └── file_parser.py         # File format parsing
│   │   └── prompts/                   # Prompt templates per agent
│   └── tests/                         # 47 tests
├── frontend/
│   └── src/
│       ├── app/                       # Next.js pages
│       ├── components/                # React components
│       ├── hooks/                     # Custom hooks
│       └── lib/                       # API client + types
└── docs/
    ├── architecture.md
    └── superpowers/
        ├── specs/                     # Design specification
        └── plans/                     # Implementation plan
```

## Running Tests

```bash
cd backend
python3 -m pytest tests/ -v
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (not needed if using Vertex AI) | `""` |
| `USE_VERTEX` | Use Google Cloud Vertex AI instead of direct API | `false` |
| `VERTEX_PROJECT_ID` | Google Cloud project ID (when using Vertex AI) | `""` |
| `VERTEX_REGION` | Vertex AI region | `us-east5` |
| `CHROMA_DB_PATH` | Path for ChromaDB persistent storage | `./data/chroma_db` |
| `CHROMA_COLLECTION_NAME` | ChromaDB collection name | `meal_history` |
| `UPLOAD_DIR` | Directory for uploaded files | `./uploads` |
| `CLAUDE_MODEL` | Claude model to use | `claude-sonnet-4-20250514` |
