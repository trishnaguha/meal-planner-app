# Meal Planner App — Architecture

## Overview

A multi-agent meal planning application that analyzes past meal history via RAG, generates validated weekly meal plans, and produces organized grocery shopping lists.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router) + Tailwind CSS |
| Backend | Python FastAPI |
| Agent Orchestration | LangGraph StateGraph |
| LLM | Claude API (Sonnet) via Anthropic SDK / Vertex AI |
| Vector Database | ChromaDB (local, persistent) |
| Embeddings | ChromaDB default (all-MiniLM-L6-v2) |

## Agent Architecture

Four agents orchestrated via LangGraph with conditional edges:

```
┌──────────────────┐
│ History Analyser │──── embed + store ───▶ ChromaDB
│ Agent            │
└────────┬─────────┘
         │ (on generate/swap)
         ▼
┌──────────────────┐
│ Meal Planner     │◀── RAG retrieval ◀── ChromaDB
│ Agent            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Validator Agent  │──── fail ──▶ back to Meal Planner (max 2 retries)
│ (meal plan)      │
└────────┬─────────┘
         │ pass
         ▼
┌──────────────────┐
│ Shopping         │
│ Organiser Agent  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Validator Agent  │──── fail ──▶ back to Shopping Organiser (max 2 retries)
│ (shopping list)  │
└────────┬─────────┘
         │ pass
         ▼
      Display
  (Approve / Swap)
```

### Agent 1: History Analyser

Parses freeform meal notes (text paste or file upload: .txt, .csv, .json, .pdf) into structured records. Extracts dish names, day-of-week patterns, quantities, prep notes, and tags. Embeds into ChromaDB for RAG retrieval.

### Agent 2: Meal Planner

Retrieves the user's full meal history from ChromaDB. Generates a 7-day meal plan (lunch and dinner only — 14 meals total) with:
- Weekday meals (Mon–Fri) drawn from the user's uploaded meal history
- Weekend meals (Sat–Sun) may introduce new dishes for variety
- A dish may appear at most twice in the week
- Protein / carb / vegetable balance across each day

### Agent 3: Validator

Runs at two points in the pipeline:
1. After Meal Planner: verifies dishes exist in history, flags dishes appearing 3+ times, validates nutritional balance
2. After Shopping Organiser: verifies ingredients map to meals, checks for phantom items, validates quantities

Max 2 retries per validation point. After 2 failures, passes with warning flags.

### Agent 4: Shopping Organiser

Extracts ingredients from the validated meal plan. Deduplicates and aggregates quantities. Groups by grocery section: Produce, Protein, Dairy, Grains/Pantry, Spices.

## LangGraph State Flow

```
action = "upload"    → History Analyser → END
action = "generate"  → Meal Planner → Validator → Shopping Organiser → Validator → END
action = "swap"      → Meal Planner (with exclusion list) → Validator → Shopping → Validator → END
action = "approve"   → Store approved plan in ChromaDB → END
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /upload-meals | Upload file or paste text for history analysis |
| POST | /generate-plan | Generate a new 7-day meal plan |
| POST | /swap-meal | Regenerate plan excluding rejected dishes |
| POST | /approve-plan | Approve and store the finalized plan |
| GET | /meal-history | Query indexed meal history |
| GET | /current-plan | Get the current meal plan |
| GET | /shopping-list | Get the current shopping list |

## Frontend Dashboard

Glassmorphism design with frosted glass panels, saffron/amber accent gradients, and staggered entrance animations.

Three-panel layout:
1. **Meal History Input** — drag-and-drop file upload (.txt, .csv, .json, .pdf) + paste textarea
2. **Meal Plan View** — 7-day lunch and dinner plan with Approve / Swap buttons, spice-strip day cards. History dishes are marked with a star.
3. **Shopping List** — color-coded grocery categories with Copy button

On page load, the frontend queries `/api/meal-history` to check for existing data in ChromaDB. If meals are already indexed, it skips the upload step and shows the Generate button immediately.

## Data Storage

ChromaDB persists to disk at `backend/data/chroma_db/`. Data survives server restarts — no re-upload needed.

- `meal_history` collection — embedded past meal records with metadata (day, frequency, tags)
- Approved plans are added back to history to improve future recommendations
- Large meal logs are chunked (30 lines per chunk) for reliable Claude API parsing

## Project Structure

```
meal-planner-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # configuration
│   │   ├── api/routes.py        # REST endpoints
│   │   ├── agents/              # LangGraph nodes
│   │   │   ├── state.py         # shared state schema
│   │   │   ├── graph.py         # StateGraph definition
│   │   │   ├── history_analyser.py
│   │   │   ├── meal_planner.py
│   │   │   ├── validator.py
│   │   │   └── shopping_organiser.py
│   │   ├── services/            # ChromaDB, Claude, file parser
│   │   └── prompts/             # prompt templates per agent
│   ├── data/chroma_db/          # persistent vector storage
│   └── uploads/                 # temporary file uploads
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   ├── hooks/               # custom hooks for API calls
│   │   └── lib/                 # API client + types
│   └── ...
│
└── docs/
    └── architecture.md          # this file
```
