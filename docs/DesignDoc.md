# Design Document: AI-Powered Restaurant Recommendation System

This document describes the implemented design for the **Practical 5-Phase Architecture** in `docs/phase-wise-architecture.md`, including current implementation status and interfaces for end-to-end testing.

## Goals
- Provide an end-to-end demo: **dataset → recommendations → API → UI**.
- Keep Phase 2 deterministic recommendations as a reliable baseline.
- Make Phase 3 LLM integration testable and provider-isolated.
- Keep the codebase organized by phases under `src/restaurant_rec/phase1..phase5/`.

## Non-goals (for now)
- Production-grade auth, rate limiting, multi-tenant hosting.
- Full-featured frontend framework beyond a basic Next.js app.
- Persistent user profiles/history.

---

## Repository structure

- `src/restaurant_rec/phase1/`
  - `hf_dataset_source.py`: Hugging Face dataset loader (cached).
  - `normalize.py`: normalization + cleaning + de-duplication.
  - `store_parquet.py`: Parquet-backed store with query primitives.
  - `ingestion.py`: ingestion orchestration + summary report.
  - `models.py`, `ports.py`, `config.py`, `text_normalize.py`: contracts + config + utilities.
- `src/restaurant_rec/phase2/`
  - `recommendation.py`: deterministic filtering + baseline ranking + relaxations.
  - `filter.py`, `preferences.py`: convenience modules for Phase 2.
  - `cli.py`: CLI for `ingest` and `recommend`.
- `src/restaurant_rec/phase3/`
  - `groq.py`: Groq client + robust `.env` loading.
  - `prompting.py`: prompt builder.
  - `smoke.py`: 3 smoke tests to validate LLM connectivity and JSON behavior.
- `src/restaurant_rec/phase4/`
  - `app.py`: FastAPI backend + basic UI served at `/`.
- `src/restaurant_rec/phase5/`
  - `tests/`: unit tests (Phase 4 API tests included).

---

## Data model (canonical internal schema)

### Restaurant
- `id: str`
- `name: str`
- `location: str` (city)
- `area: str | None` (locality)
- `cuisines: list[str]`
- `average_cost_for_two: float | None`
- `rating: float | None`
- `reviews_count: int | None`
- `tags: list[str]`
- `raw: dict | None`

### UserPreferences
- `location: str`
- `locality: str | None` (optional)
- `budget_max_inr: float`
- `cuisines: list[str]`
- `min_rating: float`
- `additional_preferences: str | None`

### Recommendation (output)
- `restaurant_id`
- `restaurant_name`
- `cuisine`
- `rating`
- `estimated_cost_inr`
- `rank`
- `explanation`
- `match_reasons`

---

## Phase 1: ingestion + normalization

### Responsibilities
- Load raw dataset from Hugging Face with caching.
- Normalize fields, coerce types, and drop malformed rows.
- De-duplicate by `(name, area, location)`.
- Persist normalized restaurants to `data/restaurants.parquet`.
- Emit a summary report including `skipped_by_reason`.

### Key implementation details
- Location canonicalization happens during normalization using `phase1/text_normalize.py`:
  - Example: `Bengaluru` / `South Bangalore` → `Bangalore`
- Parquet store `upsert_many()` is treated as a **full refresh** to avoid stale rows after normalization changes.

---

## Phase 2: deterministic recommendations

### Inputs
- `location`, optional `locality`
- `budget_max_inr`
- `cuisines`
- `min_rating`

### Candidate retrieval
Store query filters:
- `location` exact match (case-insensitive)
- optional `locality` exact match against `area`
- `cuisines` intersection
- `rating >= min_rating` (if present)
- `average_cost_for_two <= budget_max_inr` (unknown cost allowed by config)

### Baseline ranking
Scoring components (explainable):
- cuisine match strength
- rating signal (if present)
- budget fit (<= max)
- optional popularity bump (`reviews_count`)

### Fallback / relaxations
When zero results, apply:
- lower `min_rating`
- drop `min_rating` if needed
- widen budget (+20%)
- drop cuisine constraint (last resort)

The system returns `relaxations_applied` for transparency (shown in UI).

---

## Phase 3: LLM ranking + explanations (Groq)

### Configuration
- API key and model are loaded from `.env` (or environment variables).
- Robust `.env` loading:
  - searches current directory + parents for `.env`
  - falls back to `~/.env`

### Smoke tests (3)
`python -m restaurant_rec.phase3.smoke`:
- connectivity
- JSON-only response parsing
- “choose only from candidates” enforcement

---

## Phase 4: FastAPI backend + basic UI

### Endpoints
- `GET /`
  - Basic HTML UI that calls the API via `fetch`.
- `GET /health`
  - Response: `{ ok: true, restaurant_count: number }`
- `GET /locations`
  - Returns distinct `location` values from the parquet store.
- `GET /localities?location=<location>`
  - Returns distinct `area` values for the chosen location.
- `POST /recommendations`
  - Request JSON:
    - `location`, optional `locality`
    - `budget_max_inr`, `cuisines`, `min_rating`, `additional_preferences`, `top_n`
  - Response JSON:
    - `recommendations: [...]`
    - `relaxations_applied: [...]`

### UI behavior
- Location dropdown uses `GET /locations`.
- Locality dropdown uses `GET /localities` after location selection.
- Renders ranked recommendation cards and shows relaxations.

### Next.js UI direction (reference design)
We will build a Next.js frontend (Phase 4) inspired by the provided mock:

- **Layout**
  - Landing page with a prominent hero panel (“Find your perfect meal…”) and a compact preference form.
  - Results view with:
    - a left “AI reasoning / filters applied” panel (shows relaxations and query summary)
    - a grid of recommendation cards (image placeholder, name, cuisine tags, rating, cost, CTA).
- **Components**
  - Location selector (searchable dropdown) backed by `GET /locations`.
  - Locality selector (searchable dropdown) backed by `GET /localities?location=...`.
  - Cuisine input (comma-separated or multi-select in later iteration).
  - Results cards with consistent “pill” tags (cuisine, rating, cost).
- **Data flow**
  - User submits preferences → Next.js calls `POST /recommendations` → renders cards + relaxations.
  - API base URL configured via environment variable (e.g., `NEXT_PUBLIC_API_BASE_URL`).
- **Backend support**
  - Enable CORS for `http://localhost:3000` during local development.

---

## Phase 5: testing

### Current tests
- `phase5/tests/test_phase4_api.py`
  - `/` loads
  - `/health` returns correct schema
  - `/recommendations` returns results and respects budget filtering
  - `/locations` returns expected values (in-memory test store)

---

## Runbook (local)

### 1) Install deps

```bash
python -m pip install -e .
```

### 2) Ingest dataset (Phase 1)

```bash
python -m restaurant_rec ingest
```

### 3) Start API + UI (Phase 4)

```bash
python -m uvicorn restaurant_rec.phase4.app:create_app --factory --host 127.0.0.1 --port 8001
```

Open:
- UI: `http://127.0.0.1:8001/`
- Health: `http://127.0.0.1:8001/health`

### 3b) Start Next.js frontend (Phase 4)

```bash
cd frontend
cp .env.local.example .env.local
npm run dev
```

Open:
- Next.js UI: `http://localhost:3000`

The frontend calls the backend using `NEXT_PUBLIC_API_BASE_URL` (default example: `http://127.0.0.1:8001`).

### 4) LLM smoke tests (Phase 3)

```bash
python -m restaurant_rec.phase3.smoke
```

