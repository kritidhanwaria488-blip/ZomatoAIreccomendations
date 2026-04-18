from __future__ import annotations

"""
Phase 4 FastAPI backend.
"""


# Load environment variables from .env
import dotenv; dotenv.load_dotenv()
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.models import Recommendation, UserPreferences
from restaurant_rec.phase1.store_parquet import ParquetRestaurantStore
from restaurant_rec.phase1.text_normalize import canonicalize_location
from restaurant_rec.phase2.recommendation import RecommendationService
from restaurant_rec.phase3.llm_recommendation import LLMRecommendationService


_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>RestaurantRec</title>
    <style>
      :root { color-scheme: light; }
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b1220; color: #e6e8ee; }
      .wrap { max-width: 960px; margin: 0 auto; padding: 28px 18px 60px; }
      h1 { margin: 0 0 6px; font-size: 28px; }
      p.sub { margin: 0 0 18px; color: #aab2c5; }
      .card { background: #111a2e; border: 1px solid #223055; border-radius: 14px; padding: 16px; }
      form { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: end; }
      label { display: grid; gap: 6px; font-size: 13px; color: #c6cbe0; }
      input, textarea { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #2a3a66; background: #0c1426; color: #e6e8ee; }
      textarea { min-height: 40px; resize: vertical; }
      .row { grid-column: 1 / -1; }
      button { padding: 10px 14px; border-radius: 12px; border: 1px solid #2a3a66; background: #2b5cff; color: white; cursor: pointer; font-weight: 600; }
      button[disabled] { opacity: 0.6; cursor: not-allowed; }
      .meta { margin-top: 10px; color: #aab2c5; font-size: 13px; }
      .results { margin-top: 14px; display: grid; gap: 10px; }
      .rec { background: #0c1426; border: 1px solid #223055; border-radius: 12px; padding: 12px; }
      .rec h3 { margin: 0 0 6px; font-size: 16px; }
      .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #2a3a66; color: #c6cbe0; margin-right: 6px; }
      .err { color: #ffb4b4; white-space: pre-wrap; }
      footer { margin-top: 16px; color: #8f97ac; font-size: 12px; }
      a { color: #9bb5ff; }
      @media (max-width: 720px) { form { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>RestaurantRec</h1>
      <p class="sub">Phase 4 basic UI (FastAPI). Uses deterministic recommendations (Phase 2).</p>
      <div class="card">
        <form id="f">
          <label>
            Location (city)
            <input name="location" id="location" list="locations" value="Bangalore" placeholder="Select or type..." required />
            <datalist id="locations"></datalist>
          </label>
          <label>
            Locality (optional)
            <input name="locality" id="locality" list="localities" placeholder="Select after choosing location" />
            <datalist id="localities"></datalist>
          </label>
          <label>
            Budget max (INR)
            <input name="budget_max_inr" value="1500" type="number" min="1" step="1" required />
          </label>
          <label>
            Cuisines (comma-separated)
            <input name="cuisines" value="Italian,Chinese" placeholder="e.g. Italian,Chinese" required />
          </label>
          <label>
            Min rating
            <input name="min_rating" value="3.5" type="number" min="0" max="5" step="0.1" />
          </label>
          <label>
            Top N
            <input name="top_n" value="10" type="number" min="1" max="50" step="1" />
          </label>
          <label class="row">
            Additional preferences (optional)
            <textarea name="additional_preferences" placeholder="e.g. family-friendly, quick service"></textarea>
          </label>
          <div class="row">
            <button id="btn" type="submit">Get recommendations</button>
            <div id="meta" class="meta"></div>
          </div>
        </form>
        <div id="out" class="results"></div>
        <div id="err" class="err"></div>
      </div>
      <footer>
        API: <a href="/health" target="_blank" rel="noreferrer">/health</a> and <code>/recommendations</code>
      </footer>
    </div>
    <script>
      const f = document.getElementById('f');
      const out = document.getElementById('out');
      const err = document.getElementById('err');
      const meta = document.getElementById('meta');
      const btn = document.getElementById('btn');
      const locInput = document.getElementById('location');
      const locList = document.getElementById('locations');
      const localInput = document.getElementById('locality');
      const localList = document.getElementById('localities');

      function esc(s) {
        return String(s ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
      }

      async function loadLocations() {
        try {
          const r = await fetch('/locations');
          const data = await r.json();
          locList.innerHTML = (data || []).map(x => `<option value="${esc(x)}"></option>`).join('');
        } catch { /* ignore */ }
      }

      async function loadLocalities(location) {
        localList.innerHTML = '';
        if (!location) return;
        try {
          const r = await fetch('/localities?location=' + encodeURIComponent(location));
          const data = await r.json();
          localList.innerHTML = (data || []).map(x => `<option value="${esc(x)}"></option>`).join('');
        } catch { /* ignore */ }
      }

      loadLocations();
      locInput.addEventListener('change', () => {
        localInput.value = '';
        loadLocalities(locInput.value.trim());
      });

      f.addEventListener('submit', async (e) => {
        e.preventDefault();
        err.textContent = '';
        out.innerHTML = '';
        meta.textContent = 'Loading...';
        btn.disabled = true;

        const fd = new FormData(f);
        const cuisines = String(fd.get('cuisines') || '')
          .split(',')
          .map(s => s.trim())
          .filter(Boolean);

        const payload = {
          location: String(fd.get('location') || '').trim(),
          locality: String(fd.get('locality') || '').trim() || null,
          budget_max_inr: Number(fd.get('budget_max_inr') || 0),
          cuisines,
          min_rating: Number(fd.get('min_rating') || 3.5),
          additional_preferences: String(fd.get('additional_preferences') || '').trim() || null,
          top_n: Number(fd.get('top_n') || 10),
        };

        try {
          const r = await fetch('/recommendations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await r.json();
          if (!r.ok) throw new Error(JSON.stringify(data, null, 2));

          const relax = (data.relaxations_applied || []);
          meta.textContent = relax.length ? ('Relaxations applied: ' + relax.join(', ')) : 'Exact match.';

          const recs = data.recommendations || [];
          if (!recs.length) {
            out.innerHTML = '<div class="meta">No matches found.</div>';
            return;
          }

          out.innerHTML = recs.map(rec => `
            <div class="rec">
              <h3>${esc(rec.rank)}. ${esc(rec.restaurant_name)}</h3>
              <div>
                <span class="pill">${esc(rec.cuisine || 'Cuisine')}</span>
                <span class="pill">Rating: ${esc(rec.rating ?? 'N/A')}</span>
                <span class="pill">Cost: ${esc(rec.estimated_cost_inr ?? 'N/A')}</span>
              </div>
              <div class="meta">${esc(rec.explanation || '')}</div>
            </div>
          `).join('');
        } catch (e2) {
          meta.textContent = '';
          err.textContent = String(e2);
        } finally {
          btn.disabled = false;
        }
      });
    </script>
  </body>
</html>
"""

class HealthResponse(BaseModel):
    ok: bool
    restaurant_count: int


class RecommendationsRequest(BaseModel):
    location: str = Field(..., min_length=1, description="City or area name (e.g., Bangalore, Whitefield)")
    locality: str | None = Field(None, description="Optional neighborhood within the location")
    budget_max_inr: float = Field(..., gt=0, description="Maximum budget in INR (must be > 0)")
    cuisines: list[str] = Field(default_factory=list, description="List of preferred cuisines (optional)")
    min_rating: float = Field(0, ge=0, le=5, description="Minimum rating (0 = no filter)")
    additional_preferences: str | None = Field(None, description="Optional additional preferences text")
    top_n: int = Field(10, ge=1, le=50, description="Number of results to return (1-50)")
    use_llm: bool = Field(False, description="Enable AI-powered LLM ranking and explanations")


class RecommendationResponse(BaseModel):
    recommendations: list[dict[str, Any]]
    relaxations_applied: list[str] = []


def _rec_to_dict(r: Recommendation) -> dict[str, Any]:
    return {
        "restaurant_id": r.restaurant_id,
        "restaurant_name": r.restaurant_name,
        "cuisine": r.cuisine,
        "rating": r.rating,
        "estimated_cost_inr": r.estimated_cost,
        "rank": r.rank,
        "explanation": r.explanation,
        "match_reasons": r.match_reasons,
    }


def create_app(
    *,
    cfg: AppConfig | None = None,
    store: ParquetRestaurantStore | None = None,
) -> FastAPI:
    import os
    cfg = cfg or AppConfig.from_env(dict(os.environ))
    print(f"[DEBUG] Using restaurants_parquet_path: {cfg.restaurants_parquet_path.resolve()}")
    print(f"[DEBUG] Current working directory: {os.getcwd()}")
    print(f"[DEBUG] Parquet file exists: {cfg.restaurants_parquet_path.resolve().exists()}")
    store = store or ParquetRestaurantStore(cfg.restaurants_parquet_path)

    app = FastAPI(title="RestaurantRec API", version="0.1.0")

    # Allow Next.js dev server and production Vercel domains.
    import os
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
    ]
    # Add custom production origin from env var
    if os.getenv("FRONTEND_URL"):
        origins.append(os.getenv("FRONTEND_URL"))
    # Allow all Vercel subdomains (for preview deployments)
    origins.append("https://*.vercel.app")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request/Response logging middleware (Phase 5)
    import time
    from fastapi import Request
    from restaurant_rec.phase5.logging import RecommendationLogger
    
    logger = RecommendationLogger()
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        method = request.method
        url = str(request.url)
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = int((time.time() - start) * 1000)
        
        # Log the request (for recommendations endpoint)
        if "/recommendations" in url and method == "POST":
            try:
                body = await request.body()
                if body:
                    import json
                    payload = json.loads(body)
                    logger.log_request(
                        preferences=payload,
                        result_count=None,  # Will be updated after response
                        relaxations_applied=[],
                        latency_ms=latency_ms,
                        llm_used=payload.get("use_llm", False),
                        error=None,
                    )
            except Exception:
                pass  # Silently skip logging errors
        
        # Add latency header
        response.headers["X-Response-Time-Ms"] = str(latency_ms)
        
        return response

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(_INDEX_HTML)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        try:
            count = store.count()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e))
        return HealthResponse(ok=True, restaurant_count=count)

    @app.get("/locations")
    def locations() -> list[str]:
        if hasattr(store, "list_locations"):
            return store.list_locations()  # type: ignore[attr-defined]
        # fallback (shouldn't happen in prod): empty list
        return []

    @app.get("/localities")
    def localities(location: str) -> list[str]:
        loc = canonicalize_location(location)
        if hasattr(store, "list_localities"):
            return store.list_localities(location=loc)  # type: ignore[attr-defined]
        return []

    @app.post("/recommendations", response_model=RecommendationResponse)
    def recommendations(req: RecommendationsRequest) -> RecommendationResponse:
        prefs = UserPreferences(
            location=canonicalize_location(req.location),
            locality=(req.locality.strip() if req.locality else None),
            budget_max_inr=req.budget_max_inr,
            cuisines=req.cuisines,
            min_rating=req.min_rating,
            additional_preferences=req.additional_preferences,
        )

        try:
            if req.use_llm:
                # Phase 3: LLM-powered recommendations
                llm_service = LLMRecommendationService()
                
                # Get baseline candidates first
                baseline_recs, debug = RecommendationService(store=store, cfg=cfg).recommend(
                    prefs, top_n=50  # Get more candidates for LLM
                )
                
                if not baseline_recs:
                    return RecommendationResponse(
                        recommendations=[],
                        relaxations_applied=debug.relaxations_applied,
                    )
                
                # Convert baseline recommendations back to restaurants for LLM
                candidate_restaurants = []
                for rec in baseline_recs:
                    restaurant = store.get_by_id(rec.restaurant_id)
                    if restaurant:
                        candidate_restaurants.append(restaurant)
                
                # Use LLM to rank candidates
                llm_result = llm_service.rank_candidates(prefs, candidate_restaurants, top_n=req.top_n)
                
                return RecommendationResponse(
                    recommendations=[_rec_to_dict(r) for r in llm_result.recommendations],
                    relaxations_applied=debug.relaxations_applied + (["llm_fallback"] if llm_result.used_fallback else ["llm_ranked"]),
                )
            else:
                # Phase 2: Deterministic recommendations
                recs, debug = RecommendationService(store=store, cfg=cfg).recommend(
                    prefs, top_n=req.top_n
                )

                return RecommendationResponse(
                    recommendations=[_rec_to_dict(r) for r in recs],
                    relaxations_applied=debug.relaxations_applied,
                )
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e))

    return app



# Expose only the app factory for uvicorn
__all__ = ["create_app"]