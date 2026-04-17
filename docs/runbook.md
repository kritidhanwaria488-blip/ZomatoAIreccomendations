# Restaurant Recommendation System - Runbook

## Quick Start

### Prerequisites
- Python 3.10+
- Groq API key (for LLM features)

### Installation
```bash
# Clone the repository
cd milestone1

# Install dependencies
python -m pip install -e .
```

### Environment Setup
1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Groq API key:
```env
GROQ_API_KEY=your_actual_api_key_here
GROQ_MODEL=mixtral-8x7b-32768
```

## Running the System

### Phase 1-2: CLI Mode
```bash
# Ingest data
python -m restaurant_rec ingest

# Get recommendations (deterministic)
python -m restaurant_rec recommend --location Bangalore --budget-max-inr 1500 --cuisines "Italian,Chinese" --min-rating 3.5

# Get recommendations with LLM ranking
python -m restaurant_rec recommend --location Bangalore --budget-max-inr 1500 --cuisines "Italian,Chinese" --min-rating 3.5 --use-llm
```

### Phase 4: Web API Mode
```bash
# Start the FastAPI server
uvicorn restaurant_rec.phase4.app:create_app --factory --host 0.0.0.0 --port 8000

# Test the API
# Health check
curl http://localhost:8000/health

# Get recommendations
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bangalore",
    "budget_max_inr": 1500,
    "cuisines": ["Italian", "Chinese"],
    "min_rating": 3.5,
    "top_n": 5
  }'

# Get recommendations with LLM
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bangalore", 
    "budget_max_inr": 1500,
    "cuisines": ["Italian", "Chinese"],
    "min_rating": 3.5,
    "top_n": 5,
    "use_llm": true
  }'
```

## Testing

### Run Unit Tests
```bash
cd src/restaurant_rec/phase5/tests
python -m unittest test_recommendation
```

### Run Smoke Tests
```bash
# Test Groq LLM connectivity
python -m restaurant_rec.phase3.smoke
```

## Common Issues and Fixes

### Issue: "Python was not found"
**Fix:**
1. Install Python 3.10+ from python.org
2. Check "Add python.exe to PATH" during installation
3. Disable Microsoft Store aliases:
   - Settings → Apps → Advanced app settings → App execution aliases
   - Turn off `python.exe` and `python3.exe`

### Issue: "Missing GROQ_API_KEY"
**Fix:**
1. Create `.env` file in project root
2. Add: `GROQ_API_KEY=your_key_here`
3. Get API key from: https://console.groq.com

### Issue: "No matches found"
**Fix:**
- The system will automatically relax constraints (lower rating, widen budget, drop cuisine)
- Check that your location spelling matches the dataset (try "Bangalore" instead of "Bengaluru")
- Use the `/locations` API endpoint to see available cities

### Issue: "Port already in use"
**Fix:**
```bash
# Use a different port
uvicorn restaurant_rec.phase4.app:create_app --factory --host 0.0.0.0 --port 8001
```

## Dataset Management

### Refresh Dataset Cache
```bash
# Delete cached data and re-ingest
rm data/restaurants.parquet
rm -rf data/hf_cache
python -m restaurant_rec ingest
```

### View Dataset Statistics
The ingestion command shows:
- Total rows from source
- Cleaned rows after normalization
- Skipped rows with reasons
- Top cuisines
- City coverage

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check system health and restaurant count |
| `/locations` | GET | List available cities |
| `/localities` | GET | List localities for a city |
| `/recommendations` | POST | Get restaurant recommendations |

## Architecture Overview

**Phase 1:** Data ingestion from Hugging Face → Parquet storage
**Phase 2:** Deterministic filtering (location, budget, cuisine, rating)
**Phase 3:** LLM ranking with Groq API + fallback to deterministic
**Phase 4:** FastAPI backend + web UI
**Phase 5:** Caching, logging, testing, runbook (this document)

## Performance Notes

- Dataset ingestion: ~30 seconds for 50K+ rows
- Recommendation latency: <100ms (deterministic), 1-3s (with LLM)
- LLM fallback: Automatic on API errors or invalid responses
- Cache: File-based, optional TTL

## Cost Considerations

- Groq API: Free tier available, monitor usage
- Candidate capping: Limited to 50 candidates per LLM call
- LLM only used when explicitly requested (`--use-llm` or `use_llm: true`)
