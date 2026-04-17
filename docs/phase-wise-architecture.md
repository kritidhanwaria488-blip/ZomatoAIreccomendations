# Practical 5-Phase Architecture: AI-Powered Restaurant Recommendation System

This document replaces the previous phase plan with a **practical 5-phase architecture** designed for incremental delivery.

## Shared principles (all phases)
- **Pipeline shape**: Ingest → Normalize → Store → Collect Preferences → Retrieve Candidates → (Optional) LLM Rank/Explain → Present
- **Reliability**: Always keep a deterministic baseline so results are available if the LLM fails.
- **No hallucinations**: The LLM must **choose only from provided candidates** (IDs enforced).
- **Cost control**: Cap candidate set before any LLM call; send compact structured fields only.

## Canonical domain schema (internal contracts)

### Restaurant
Minimum standardized fields:
- `id` (stable identifier)
- `name`
- `location` (city)
- `area` (optional)
- `cuisines: List[str]`
- `average_cost_for_two_inr: float | None`
- `rating: float | None`
- `votes: int | None` (optional)
- `raw: dict | None` (optional)

### UserPreferences
- `location` (required)
- `budget_max_inr` (required)
- `cuisines` (required; list)
- `min_rating` (optional, default 3.5)
- `additional_preferences` (optional free text)

### Recommendation
- `restaurant_id`
- `restaurant_name`
- `cuisine`
- `rating`
- `estimated_cost_inr`
- `rank`
- `explanation` (LLM-generated in Phase 3, rule-based in Phase 2)
- `match_reasons` (structured list; useful for debugging/UI)

---

## Phase 1 — Data ingest + normalize (Hugging Face Zomato)

### Goal
Load the Zomato dataset from Hugging Face, clean it, and standardize it into the `Restaurant` schema.

### Deliverables
- Hugging Face ingestion with caching
- Normalization + cleaning:
  - rating: string → float (safe parsing)
  - cost: string → float (strip currency/commas)
  - cuisines: split and canonicalize
  - drop/skip malformed rows (count + reasons)
  - de-duplicate by `(name, area, location)`
- Persist normalized restaurants to a cache file (recommended: `restaurants.parquet`)
- Summary report:
  - total rows
  - cleaned rows
  - skipped rows
  - top cuisines
  - city coverage

---

## Phase 2 — Deterministic filtering (location, budget_max_inr, cuisine, rating)

### Goal
Implement a reliable, debuggable recommender that works without an LLM.

### Inputs
- `location`
- `budget_max_inr` (numeric max budget; not buckets)
- `cuisines` (one or many)
- `min_rating` (optional)

### Behavior
- Query/filter candidates by:
  - location match
  - cuisine intersection
  - rating >= min_rating
  - cost <= budget_max_inr
- Baseline ranking (explainable):
  - cuisine match strength
  - rating signal
  - budget fit
  - optional popularity (votes)
- If zero matches: progressively relax constraints (documented):
  - lower min_rating
  - widen budget
  - drop cuisine constraint (last resort)

---

## Phase 3 — Groq LLM ranking + explanations

### Goal
Use **Grok LLM** to improve ranking and generate natural-language explanations **without inventing restaurants**.

### Components
- Candidate cap: take top M baseline candidates (e.g., 20–50) before LLM.
- Prompt template:
  - strict rules: choose only from provided candidate IDs
  - output format: JSON only
  - include preferences + candidate list (compact fields)
- Grok client adapter:
  - provider-agnostic interface, Grok implementation behind it
- Response parsing + validation:
  - ensure all IDs exist in provided candidates
  - ensure ranks are unique and contiguous
  - retry once on invalid JSON; fallback to Phase 2 baseline if still invalid

### Secrets / configuration
- The **API key will be stored locally in a `.env` file** (not committed).
- See `.env.example` for required variables (e.g., `GROQ_API_KEY`, `GROQ_MODEL`).

---

## Phase 4 — FastAPI backend + web UI

### Goal
Expose recommendations via an API and a simple web UI.

### Backend (FastAPI)
- `GET /health`: indicates dataset/store readiness
- `POST /recommendations`:
  - request: `location`, `budget_max_inr`, `cuisines`, `min_rating`, `additional_preferences`
  - response: ranked list of `Recommendation`

### Web UI
- Form inputs for preferences + results display
- Loading / empty-state UX
- Show explanation text and key attributes

**Note**: We implement backend + a basic UI for end-to-end testing. The frontend is now a **Next.js** app (for easier enhancement), and the backend enables CORS for local dev.

### Practical improvements (implemented)
- The backend **canonicalizes location input** (e.g., `Bengaluru` / `South Bangalore` → `Bangalore`) so users don’t get zero results due to spelling/region variants.
- The UI supports selecting **location + locality** from backend-provided lists:
  - `GET /locations`
  - `GET /localities?location=...`

---

## Phase 5 — Caching, logging, testing, runbook

### Goal
Make the system consistent, observable, and easy to operate.

### Deliverables
- **Caching**
  - dataset cache (HF)
  - normalized store cache (`restaurants.parquet`)
  - optional recommendation cache keyed by normalized preferences
- **Logging**
  - structured logs: filter counts, relaxations, latency, LLM parse success/fail
- **Testing**
  - unit tests for normalization, filtering, scoring, prompt+parser validation
  - scenario suite: saved preference cases + constraint assertions
- **Runbook**
  - how to install/run locally
  - common failures and fixes
  - how to refresh dataset cache

---

## Deployment Architecture

### Overview
The system is designed for cloud deployment with clear separation between backend services and frontend presentation.

### Backend Deployment (Streamlit Cloud)

**Platform:** Streamlit Cloud (share.streamlit.io)  
**Purpose:** Interactive Python-based web interface for direct API access  
**Implementation:**
- Streamlit app wraps the recommendation service
- Direct access to Parquet dataset
- Real-time LLM-powered recommendations
- Simple deployment from GitHub repository

**Deployment Steps:**
1. Create `app.py` in project root (Streamlit entry point)
2. Connect GitHub repo to Streamlit Cloud
3. Configure secrets (GROQ_API_KEY) in Streamlit Cloud dashboard
4. Deploy with one click

**URL:** `https://restaurant-rec-backend.streamlit.app`

### Frontend Deployment (Vercel)

**Platform:** Vercel (vercel.com)  
**Purpose:** Next.js web application for user-facing interface  
**Implementation:**
- Next.js 16+ with App Router
- Static export for fast global CDN distribution
- API calls to Streamlit backend
- Responsive design with Tailwind CSS

**Deployment Steps:**
1. Push frontend code to GitHub
2. Import repository in Vercel dashboard
3. Configure environment variable:
   - `NEXT_PUBLIC_API_BASE_URL=https://restaurant-rec-backend.streamlit.app`
4. Deploy with automatic CI/CD

**URL:** `https://restaurant-rec-frontend.vercel.app`

### Architecture Diagram

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│                 │      │                  │      │                 │
│  User Browser   │─────▶│  Vercel Frontend │─────▶│ Streamlit Backend│
│                 │      │  (Next.js App)   │      │  (Python API)    │
└─────────────────┘      └──────────────────┘      └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Parquet Store  │
                                                 │  (12K+ restaurants)
                                                 └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Groq LLM API   │
                                                 │  (Optional)     │
                                                 └─────────────────┘
```

### Environment Variables

**Backend (Streamlit Secrets):**
```toml
GROQ_API_KEY = "your_groq_api_key"
GROQ_MODEL = "llama3-8b-8192"
```

**Frontend (Vercel Environment):**
```
NEXT_PUBLIC_API_BASE_URL=https://restaurant-rec-backend.streamlit.app
```

### Benefits

1. **Streamlit Backend:**
   - Zero-config Python deployment
   - Automatic HTTPS
   - Built-in authentication options
   - Easy LLM integration

2. **Vercel Frontend:**
   - Global CDN for fast loading
   - Automatic preview deployments
   - Serverless functions support
   - Perfect Lighthouse scores

3. **Separation of Concerns:**
   - Frontend can be updated independently
   - Backend scales based on usage
   - Clear API contract between layers

---

## Required source layout

Update the codebase to use this structure:

- `src/restaurant_rec/phase1/` (ingest + normalize + store cache)
- `src/restaurant_rec/phase2/` (deterministic filtering + scoring + relaxations)
- `src/restaurant_rec/phase3/` (Groq LLM prompting, client, parsing/validation)
- `src/restaurant_rec/phase4/` (FastAPI + web UI)
- `src/restaurant_rec/phase5/` (caching/logging/testing/runbook utilities)

All new code should be added under these phase folders, with imports updated accordingly.
