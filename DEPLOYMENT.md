# Deployment Guide - Restaurant Recommendation System

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Groq API key (for LLM features)

### 1. Install Backend Dependencies

```bash
cd milestone1
python -m pip install -e ".[dev]"
```

### 2. Configure Environment

Create `.env` file in project root:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama3-8b-8192
```

Get your API key from: https://console.groq.com

### 3. Ingest Data (One-time)

```bash
python -m restaurant_rec ingest
```

This downloads and normalizes the Zomato dataset (~12,000 restaurants).

### 4. Start Backend

```bash
# Terminal 1 - Start FastAPI
python -m uvicorn restaurant_rec.phase4.app:create_app --factory --host 127.0.0.1 --port 8003
```

Verify it's running:
```bash
curl http://127.0.0.1:8003/health
```

### 5. Start Frontend

```bash
# Terminal 2 - Start Next.js
cd frontend
npm install  # First time only
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8003"
npm run dev
```

### 6. Access the Application

- **Web UI:** http://localhost:3000
- **API Docs:** http://localhost:8003/docs
- **API Base:** http://127.0.0.1:8003

---

## Production Deployment

### Recommended: Streamlit Cloud + Vercel

This is the recommended deployment architecture for production.

#### Backend (Streamlit Cloud)

**Why Streamlit Cloud:**
- Zero-config Python deployment
- Built-in authentication
- Easy LLM integration
- Free tier available

**Steps:**

1. **Install Streamlit:**
```bash
pip install streamlit
```

2. **Create `streamlit_app.py` in project root:**
```python
import streamlit as st
from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.store_parquet import ParquetRestaurantStore
from restaurant_rec.phase2.recommendation import RecommendationService
from restaurant_rec.phase3.llm_recommendation import LLMRecommendationService
from restaurant_rec.phase1.text_normalize import canonicalize_location
from restaurant_rec.phase1.models import UserPreferences

st.set_page_config(page_title="RestaurantRec API", page_icon="🍽️")

st.title("🍽️ Restaurant Recommendation API")
st.markdown("AI-powered restaurant recommendations powered by Groq LLM")

# Initialize
@st.cache_resource
def get_store():
    cfg = AppConfig.from_env({})
    return ParquetRestaurantStore(cfg.restaurants_parquet_path)

store = get_store()
cfg = AppConfig.from_env({})

# Sidebar - Preferences
st.sidebar.header("Search Preferences")

location = st.sidebar.text_input("City/Area", "Bangalore")
locality = st.sidebar.text_input("Neighborhood (optional)", "")
budget = st.sidebar.number_input("Budget Max (INR)", min_value=1, value=1500, step=100)
cuisines = st.sidebar.text_input("Cuisines (comma-separated)", "Italian, Chinese")
rating = st.sidebar.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.5)
top_n = st.sidebar.slider("Number of Results", 1, 50, 10)
use_llm = st.sidebar.checkbox("Use AI-powered recommendations", value=False)

if st.sidebar.button("🔍 Get Recommendations"):
    with st.spinner("Finding restaurants..."):
        prefs = UserPreferences(
            location=canonicalize_location(location),
            locality=locality.strip() if locality else None,
            budget_max_inr=budget,
            cuisines=[c.strip() for c in cuisines.split(",") if c.strip()],
            min_rating=rating,
        )
        
        if use_llm:
            llm_service = LLMRecommendationService()
            baseline_recs, debug = RecommendationService(store=store, cfg=cfg).recommend(
                prefs, top_n=50
            )
            
            if baseline_recs:
                candidate_restaurants = [store.get_by_id(rec.restaurant_id) for rec in baseline_recs if store.get_by_id(rec.restaurant_id)]
                llm_result = llm_service.rank_candidates(prefs, candidate_restaurants, top_n=top_n)
                recs = llm_result.recommendations
                
                st.success(f"✨ AI-powered recommendations generated!")
                if llm_result.used_fallback:
                    st.info("Using deterministic ranking (LLM fallback)")
            else:
                recs = []
        else:
            recs, debug = RecommendationService(store=store, cfg=cfg).recommend(prefs, top_n=top_n)
        
        st.subheader(f"Found {len(recs)} restaurants")
        
        for rec in recs:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{rec.rank}. {rec.restaurant_name}**")
                    st.caption(f"Cuisine: {rec.cuisine} | Cost: ₹{rec.estimated_cost or 'N/A'} | Rating: {rec.rating or 'N/A'}")
                    st.markdown(f"_{rec.explanation}_")
                st.divider()

# Health check
if st.sidebar.checkbox("Show system status"):
    try:
        count = store.count()
        st.sidebar.success(f"✅ System OK - {count:,} restaurants loaded")
    except Exception as e:
        st.sidebar.error(f"❌ Error: {e}")
```

3. **Deploy to Streamlit Cloud:**
   - Push code to GitHub
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Set secrets in dashboard:
     ```toml
     GROQ_API_KEY = "your_key_here"
     GROQ_MODEL = "llama3-8b-8192"
     ```
   - Deploy!

**URL:** `https://your-app-name.streamlit.app`

---

### Alternative: FastAPI Backend

#### Option 1: Uvicorn with Gunicorn

```bash
pip install gunicorn

gunicorn restaurant_rec.phase4.app:create_app \
  --factory \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

#### Option 2: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -e ".[dev]"

# Download dataset during build or at runtime
RUN python -m restaurant_rec ingest || echo "Will ingest at runtime"

EXPOSE 8000

CMD ["uvicorn", "restaurant_rec.phase4.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t restaurant-rec .
docker run -p 8000:8000 --env-file .env restaurant-rec
```

#### Option 3: Cloud Platforms

**Railway/Render/Heroku:**
1. Push code to GitHub
2. Connect repository to platform
3. Set environment variables (GROQ_API_KEY)
4. Deploy

**AWS/GCP/Azure:**
- Use containerized deployment
- Store `.env` in secrets manager
- Use managed database for parquet storage

### Frontend (Next.js) - Vercel Deployment

The frontend is designed to be deployed on **Vercel** as part of the Streamlit+Vercel architecture.

#### Why Vercel?

- **Global CDN** for fast loading worldwide
- **Automatic HTTPS** and custom domains
- **Zero-config deployment** from GitHub
- **Preview deployments** for every PR
- **Serverless functions** support
- **Perfect for Next.js** applications

#### Deployment Steps

1. **Prepare for deployment:**
```bash
cd frontend
npm install  # Ensure all dependencies installed
```

2. **Configure environment variables:**

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=https://your-app-name.streamlit.app
```

3. **Deploy to Vercel:**

**Option A: Vercel CLI**
```bash
cd frontend
npm i -g vercel
vercel --prod
```

**Option B: GitHub Integration (Recommended)**
- Push your code to GitHub
- Go to [vercel.com](https://vercel.com)
- Import your GitHub repository
- Set environment variable:
  - `NEXT_PUBLIC_API_BASE_URL` = `https://your-app-name.streamlit.app`
- Deploy!

**Option C: Static Export**
```bash
cd frontend
npm run build
# Copy the `out/` folder to any static host
```

#### Connect Frontend to Streamlit Backend

**Important:** The frontend needs to know where your Streamlit backend is running.

1. Deploy Streamlit backend first (get the URL)
2. Set `NEXT_PUBLIC_API_BASE_URL` to your Streamlit URL
3. Redeploy frontend

**Example:**
```
Streamlit URL: https://restaurant-rec-api.streamlit.app
Vercel Env Var: NEXT_PUBLIC_API_BASE_URL=https://restaurant-rec-api.streamlit.app
```

#### Additional Deploy Options
```bash
npm i -g vercel
vercel --prod
```

**Static Export:**
```bash
cd frontend
npm run build
# Copy out/ folder to any static host
```

**Environment Variables for Frontend:**
```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
```

---

## Testing & Verification

### Run All Tests

```bash
# Unit tests
python -m unittest src.restaurant_rec.phase5.tests.test_simple -v

# Integration tests
python -m unittest src.restaurant_rec.phase5.tests.test_integration -v

# Edge case tests
python test_edge_cases.py
```

### Performance Benchmark

```bash
python benchmark.py
```

Expected results:
- Health check: ~15ms
- Locations: ~17ms
- Recommendations: ~20-30ms

### API Smoke Test

```bash
curl -X POST http://127.0.0.1:8003/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bangalore",
    "budget_max_inr": 1000,
    "cuisines": ["Italian"],
    "top_n": 3
  }'
```

---

## Monitoring & Observability

### Logs

Logs are written to `logs/` directory:
- `recommendations.jsonl` - Recommendation requests
- API console output

View logs:
```bash
tail -f logs/recommendations.jsonl
```

### Metrics

Response time header included in all API responses:
```
X-Response-Time-Ms: 23
```

### Health Checks

```bash
curl http://127.0.0.1:8003/health
```

Response:
```json
{
  "ok": true,
  "restaurant_count": 12119
}
```

---

## Troubleshooting

### Issue: "No module named 'restaurant_rec'"

**Solution:** Install in editable mode
```bash
pip install -e ".[dev]"
```

### Issue: "Parquet file not found"

**Solution:** Run ingestion
```bash
python -m restaurant_rec ingest
```

### Issue: "Groq API key not found"

**Solution:** Create `.env` file with valid API key
```bash
echo "GROQ_API_KEY=your_key_here" > .env
```

### Issue: Frontend can't connect to backend

**Solution:** Check CORS and API URL
```bash
# Verify backend is running
curl http://127.0.0.1:8003/health

# Check frontend env var
echo $env:NEXT_PUBLIC_API_BASE_URL
```

### Issue: LLM not working

**Solution:** Check API key and smoke test
```bash
python -m restaurant_rec.phase3.smoke
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Groq API key for LLM |
| `GROQ_MODEL` | No | llama3-8b-8192 | LLM model to use |
| `DATA_CACHE_DIR` | No | ./data | Dataset storage location |
| `NEXT_PUBLIC_API_BASE_URL` | Yes (frontend) | http://127.0.0.1:8001 | API base URL |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/locations` | GET | List available locations |
| `/localities` | GET | List localities for location |
| `/recommendations` | POST | Get restaurant recommendations |

### Request/Response Format

**POST /recommendations**

Request:
```json
{
  "location": "Bangalore",
  "locality": "Koramangala",
  "budget_max_inr": 1500,
  "cuisines": ["Italian", "Chinese"],
  "min_rating": 3.5,
  "additional_preferences": "family-friendly",
  "top_n": 10,
  "use_llm": false
}
```

Response:
```json
{
  "recommendations": [
    {
      "restaurant_id": "abc123",
      "restaurant_name": "Pasta Paradise",
      "cuisine": "Italian",
      "rating": 4.2,
      "estimated_cost_inr": 1200,
      "explanation": "Great Italian cuisine within budget",
      "rank": 1,
      "match_reasons": ["Italian cuisine match", "Within budget"]
    }
  ],
  "relaxations_applied": ["min_rating dropped"]
}
```

---

## Performance Targets

- Health check: < 50ms
- Locations: < 100ms
- Recommendations: < 500ms
- Concurrent users: 100+

Current benchmarks:
- Health: ~16ms ✅
- Locations: ~17ms ✅
- Recommendations: ~24ms ✅

---

## Security Considerations

1. **API Keys:** Never commit `.env` files
2. **CORS:** Configure for production domains only
3. **Rate Limiting:** Implement for production use
4. **Input Validation:** All inputs validated via Pydantic
5. **SQL Injection:** Not applicable (Parquet storage)

---

## Support

For issues or questions:
1. Check `docs/runbook.md`
2. Review `PROJECT_STATUS.md`
3. Run test suite: `python -m unittest discover`
