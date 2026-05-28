# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository

## Running the app

**Always activate the virtual environment first:**
```bash
source ~/venvs/food-inventory-env/bin/activate
```

**Start the dev server (localhost only):**
```bash
uvicorn app.main:app --reload --port 8000
```

**Start with local network access (accessible from phone/tablet on same WiFi):**
```bash
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

Find your machine's local IP with `ipconfig getifaddr en0`, then open `http://<ip>:8000` on any device on the same network.

The app is available at http://localhost:8000. There are no tests or linting configured yet.

## Architecture

**Stack:** FastAPI + Jinja2 + HTMX + Tailwind CSS (CDN) + browser `localStorage`. No database — all item and meal data is stored client-side in the browser's localStorage. No JavaScript framework — interactivity is handled by HTMX (for loading form partials and AI requests) and vanilla JS (for all data operations and list rendering).

**Data layer:** `app/static/store.js` exports `window.Store` — a localStorage CRUD module. `app/static/render.js` exports `window.Render` — client-side HTML rendering functions. Both are loaded globally via `base.html`.

**Entry point:** `app/main.py` — mounts routers and static files. No database setup or migrations.

**Routing pattern:** Routers serve only two kinds of responses:
1. **Full-page routes** — serve HTML shells with no data (data is rendered client-side from localStorage on DOMContentLoaded)
2. **Form partial routes** — serve blank form HTML loaded into the bottom sheet via HTMX GET (no DB dependency)
3. **AI endpoints** — accept pre-aggregated localStorage data from the client via POST form fields, call the LLM, return an HTML partial

**Template pattern:** `base.html` defines the mobile layout and bottom nav, and loads `store.js` / `render.js`. All pages `{% extends "base.html" %}` and pass `active_page`. List containers (`#item-list`, `#meal-list`, dashboard strips) start empty; JS fills them on load.

**Bottom sheet pattern:** Inventory and Meals pages use a slide-up sheet (`#sheet`, `#overlay`, `#sheet-content`) with `openSheet()` / `closeSheet()` JS helpers. Sheet content is loaded via HTMX GET into `#sheet-content`. Forms inside the sheet submit via JS (not HTMX POST): the submit handler calls `Store.createItem()` / `Store.createMeal()`, then `Render.itemList()` / `Render.mealList()`, then `closeSheet()`.

**Edit item flow:** The Edit button in `Render.itemList()` sets `window._editItem` to the item object, then calls `htmx.ajax('GET', '/items/form', ...)` to load the blank form shell. The form's inline script reads `window._editItem` on load and populates fields. `closeSheet()` clears `window._editItem`.

**Item picker in meal form:** `meal_form.html` serialises all selected items into a single hidden `items_json` field as a JSON array before submission (`syncJson()` is called on every change and on submit). Each entry is `{id, name, unit, quantity, track_inventory}`. Items from inventory have a UUID string `id`; freetext items have `id: null`.

- Inventory item search uses `mousedown` + `e.preventDefault()` on the suggestions box to prevent blur from hiding suggestions before the click registers.
- When a freetext item is added, the row shows a toggle: **One-time only** (default, `track_inventory: false`) vs **+ Add to inventory** (`track_inventory: true`).

## Data model (localStorage)

Data is stored in two localStorage keys as JSON arrays:

**`food_inventory_items`** — array of item objects:
```json
{"id":"uuid","name":"Eggs","category":"Dairy","quantity":6,"unit":"units",
 "bought_at":"2026-05-01","expires_at":"2026-06-01","low_stock_at":2,
 "track_inventory":true,"created_at":"...","updated_at":"..."}
```

**`food_inventory_meals`** — array of meal objects (denormalized — item name/unit embedded at log time):
```json
{"id":"uuid","meal_type":"BREAKFAST","logged_at":"2026-05-28T08:30:00",
 "notes":"...","created_at":"...",
 "meal_items":[{"item_id":"uuid-or-null","item_name":"Eggs","item_unit":"units","quantity_used":2}]}
```

Key behaviour:
- IDs are generated client-side via `crypto.randomUUID()` — UUID strings, not integers.
- Dates/times are stored as local-time ISO strings (no `Z` suffix) so `logged_at.startsWith("YYYY-MM-DD")` works for date filtering.
- `track_inventory=false` items are not stored in the items array. One-time meal items appear only in `meal_items` with `item_id: null`.
- Creating a meal decrements inventory quantities; deleting a meal re-increments them. Both happen in `Store.createMeal()` / `Store.deleteMeal()` in `store.js`.
- Inventory list is sorted client-side by `(expires_at is null, expires_at)` — nulls last, soonest expiry first.

## store.js API

Key methods on `window.Store`:
- `getItems()` / `getMeals()` — raw arrays from localStorage
- `createItem(data)` / `updateItem(id, data)` / `deleteItem(id)` / `useItem(id)` — item CRUD
- `createMeal(data)` / `deleteMeal(id)` — meal CRUD (handles quantity side-effects)
- `getMealsForDate(dateStr)` — filters meals by date prefix
- `getExpiringItems(days)` / `getLowStockItems()` — filtered queries
- `getRecentMealItemsJson(days, mealType)` / `getExpiringItemsJson(days)` / `getConsumptionJson()` / `getLowStockJson()` — return JSON strings for AI endpoints

## Environment

`.env` at the project root is loaded via `pydantic-settings`. Required keys:
```
AI_PROVIDER=groq            # groq | gemini | huggingface (groq is default)
GROQ_API_KEY=...            # if AI_PROVIDER=groq
GEMINI_API_KEY=...          # if AI_PROVIDER=gemini
HUGGINGFACE_API_KEY=...     # if AI_PROVIDER=huggingface
```

No `DATABASE_URL` needed. The `DATABASE_URL` key in `.env` is silently ignored (Settings uses `extra = "ignore"`).

## AI features

**Service layer:** `app/services/ai_service.py` — `get_ai_response(prompt, system)` dispatches to the configured provider. Groq (`llama-3.1-8b-instant`) is the default. JSON responses are parsed defensively via `_parse_json()` which strips markdown fences before parsing.

**Provider options:**

| Provider | Package | Model | Free tier |
|---|---|---|---|
| Groq | `groq` | `llama-3.1-8b-instant` | ~14,400 req/day |
| Gemini | `google-generativeai` | `gemini-1.5-flash` | ~1M tokens/day |
| HuggingFace | `huggingface_hub` | `mistralai/Mistral-7B-Instruct-v0.3` | Rate-limited, less reliable |

**"What should I eat?"** (`POST /ai/suggest-meal`)
- Four meal-type buttons post via HTMX with `hx-vals='js:{...}'`, which reads from `Store` to include `history_json` and `expiry_json` in the request body.
- Server receives pre-aggregated data (no DB query), builds the prompt, calls LLM.
- Returns `{ suggestion, reasoning, use_these_items[] }` rendered in `partials/ai_suggestion.html`.

**"What should I restock?"** (`POST /ai/replenish`)
- Button posts `consumption_json`, `low_stock_json`, `expiry_json` — all pre-computed from localStorage by `Store.*Json()` helpers.
- Server builds prompt from submitted data, calls LLM.
- Returns `{ summary, shopping_list: [{ item, reason, urgency: high|medium|low }] }` rendered in `partials/ai_replenish.html`.

## Deployment

**Vercel** — `vercel.json` is present at the project root. The app runs as a serverless Python function.

To deploy:
1. Push to GitHub
2. Connect the repo in the Vercel dashboard
3. Set environment variables: `AI_PROVIDER` + the relevant API key

Data lives in each visitor's browser independently — no shared database. Each device (phone, laptop) has its own data that persists across browser sessions.

**iOS Safari note:** localStorage may be cleared after 7 days of inactivity due to Apple's ITP policy. Advise users to save the app to their Home Screen to prevent this.

---

### Phase 6 — Polish (not yet built)

- Loading states on AI Generate buttons (disable + spinner while HTMX request is in flight)
- Zero-quantity guard in meal logging — warn if an item being added is already at 0
- Recently used items quick-add in the meal log sheet (read last 7 days of meals from localStorage, surface as one-tap suggestions)
- Item name autocomplete in the Add Item form (read distinct names from `food_inventory_items`)
- Mobile testing pass — fix any tap target or scroll issues found on an actual device
- Export/import data as JSON (so users can back up or transfer their localStorage data between devices)
