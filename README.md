# Food Inventory

A personal food tracker for your phone. Log what's in your fridge, track expiry dates, record meals, and get AI suggestions on what to cook or restock.

Data is stored in your browser's **localStorage** — each device has its own independent data store. No account or sign-up needed.

## Features

- **Inventory** — track items with quantity, unit, expiry date, and low-stock threshold
- **Meals** — log daily meals and see a 7-day history; logging a meal automatically decrements inventory quantities
- **Dashboard** — at-a-glance view of expiring items, low-stock alerts, and today's meals
- **AI assistant** — "What should I eat?" and "What should I restock?" powered by an LLM

## Stack

- **Backend:** FastAPI + Jinja2 (serves HTML shells and AI endpoints)
- **Frontend:** HTMX + vanilla JS + Tailwind CSS (CDN)
- **Storage:** Browser `localStorage` — no database
- **AI:** Groq (default), Gemini, or HuggingFace

## Running locally

```bash
# Create and activate a virtual environment (once)
python -m venv ~/venvs/food-inventory-env
source ~/venvs/food-inventory-env/bin/activate
pip install -r requirements.txt

# Copy and fill in your AI API key
cp .env.example .env   # or create .env manually (see below)

# Start the server
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000.

**Access from your phone** (same WiFi):
```bash
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```
Find your local IP with `ipconfig getifaddr en0`, then open `http://<ip>:8000` on your phone.

## Environment variables

Create a `.env` file at the project root:

```
AI_PROVIDER=groq            # groq | gemini | huggingface
GROQ_API_KEY=...            # get a free key at console.groq.com
```

| Provider | Model | Free tier |
|---|---|---|
| Groq (default) | llama-3.1-8b-instant | ~14,400 req/day |
| Gemini | gemini-1.5-flash | ~1M tokens/day |
| HuggingFace | Mistral-7B-Instruct | Rate-limited |

## Deploying to Vercel

1. Push this repo to GitHub
2. Import it in the [Vercel dashboard](https://vercel.com/new)
3. Add environment variables: `AI_PROVIDER` and your API key
4. Deploy

`vercel.json` is already configured. No other setup needed.

> **Note on data:** each browser/device gets its own localStorage. Your phone's data and your laptop's data are separate. On iOS Safari, localStorage may be cleared after 7 days of inactivity — save the app to your Home Screen to prevent this.

## Project structure

```
app/
  main.py              # FastAPI app, mounts routers + static files
  config.py            # Settings (AI provider, API keys)
  routers/
    items.py           # GET /inventory, GET /items/form
    meals.py           # GET /meals, GET /meals/form
    ai.py              # POST /ai/suggest-meal, POST /ai/replenish
  services/
    ai_service.py      # LLM provider abstraction
  static/
    store.js           # window.Store — localStorage CRUD
    render.js          # window.Render — client-side HTML rendering
  templates/
    base.html          # Layout + bottom nav + loads store.js/render.js
    dashboard.html
    inventory.html
    meals.html
    ai.html
    partials/          # HTMX-loaded form fragments + AI result partials
vercel.json            # Vercel serverless config
```
