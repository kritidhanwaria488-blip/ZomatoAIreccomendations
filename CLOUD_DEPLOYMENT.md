# Cloud Deployment Guide

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Vercel        │ ──────> │  Railway/Render  │ ──────> │   Groq      │
│  (Frontend)     │   CORS  │  (FastAPI)       │   API   │   (LLM)     │
│  Next.js        │         │  Python          │         │             │
└─────────────────┘         └──────────────────┘         └─────────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │  Dataset    │
                              │  (Parquet)  │
                              └─────────────┘
```

## Step 1: Deploy Backend (Railway)

### Option A: Railway (Recommended - Free Tier)

1. **Go to https://railway.app**
2. **Sign up with GitHub**
3. **Click "New Project" → "Deploy from GitHub repo"**
4. **Select your repo:** `kritidhanwaria488-blip/ZomatoAIreccomendations`
5. **Railway will auto-detect configuration from `railway.json`**

### Configure Environment Variables:

Go to your project → **Variables** tab, add:

| Variable | Value | Required |
|----------|-------|----------|
| `GROQ_API_KEY` | `gsk_...your_key...` | ✅ Yes |
| `FRONTEND_URL` | `https://your-frontend.vercel.app` | Optional |

### Dataset:

The dataset will be automatically downloaded on first run (12,119 restaurants).

### Get Your Backend URL:

After deployment, Railway gives you a URL like:
```
https://restaurant-rec-api.up.railway.app
```

**Copy this URL - you'll need it for the frontend!**

---

## Step 2: Deploy Backend (Render - Alternative)

If Railway doesn't work, use Render:

1. **Go to https://render.com**
2. **Sign up with GitHub**
3. **Click "New +" → "Web Service"**
4. **Select your GitHub repo**
5. **Configuration:**
   - **Name:** `restaurant-rec-api`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -e .`
   - **Start Command:** `uvicorn restaurant_rec.phase4.app:create_app --factory --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`

6. **Add Environment Variable:**
   - `GROQ_API_KEY` = your key

7. **Click "Create Web Service"**

---

## Step 3: Deploy Frontend (Vercel)

1. **Go to https://vercel.com**
2. **Sign up with GitHub**
3. **Click "Add New Project"**
4. **Import your GitHub repo**
5. **Configure:**
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`
   - **Build Command:** `next build`
   - **Output Directory:** `dist`

6. **Add Environment Variable:**
   - **Key:** `NEXT_PUBLIC_API_BASE_URL`
   - **Value:** Your Railway/Render URL (e.g., `https://restaurant-rec-api.up.railway.app`)
   - **No trailing slash!**

7. **Click "Deploy"**

---

## Verification Checklist

### Backend Health Check:
```bash
curl https://your-backend-url.health
```
Should return:
```json
{
  "status": "healthy",
  "total_restaurants": 12119
}
```

### API Test:
```bash
curl -X POST https://your-backend-url/recommendations \
  -H "Content-Type: application/json" \
  -d '{"location":"Bangalore","budget_max_inr":1500,"cuisines":["Italian"],"top_n":3}'
```

### Frontend Test:
Open your Vercel URL and search for restaurants.

---

## Troubleshooting

### CORS Errors:
- Check `FRONTEND_URL` env var is set in backend
- Backend automatically allows `*.vercel.app`
- For custom domains, add to `FRONTEND_URL`

### 500 Errors:
- Check Railway/Render logs
- Verify `GROQ_API_KEY` is set
- Check dataset downloaded (see `/health` endpoint)

### Frontend Not Connecting:
- Verify `NEXT_PUBLIC_API_BASE_URL` points to backend
- No trailing slash in URL
- Check browser console for errors

---

## URLs Summary

| Component | Local | Production |
|-----------|-------|------------|
| Frontend | http://localhost:3000 | https://*.vercel.app |
| Backend | http://127.0.0.1:8003 | https://*.railway.app |
| API Docs | http://localhost:8003/docs | https://*.railway.app/docs |

---

## Support

- Railway Docs: https://docs.railway.app
- Render Docs: https://render.com/docs
- Vercel Docs: https://vercel.com/docs
