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

**Stack:** FastAPI + Jinja2 + HTMX + Tailwind CSS (CDN) + SQLite via SQLAlchemy. No JavaScript framework — all interactivity is handled by HTMX with small vanilla JS scripts embedded in templates.

**Entry point:** `app/main.py` — mounts routers, runs `Base.metadata.create_all`, and runs inline SQLite migrations (ALTER TABLE) for schema changes that need to be applied to existing DBs. Any new column added to a model must also have a corresponding `ALTER TABLE ... ADD COLUMN` migration block here.

**Routing pattern:** Each router (`routers/items.py`, `routers/meals.py`, `routers/ai.py`) handles both full-page routes and HTMX partial routes. Full-page routes return a complete Jinja2 template; partial routes return a fragment from `app/templates/partials/` that HTMX swaps into the page without a reload.

**Template pattern:** `base.html` defines the mobile layout and bottom nav. All pages `{% extends "base.html" %}` and pass `active_page` to highlight the correct nav item. Partials in `templates/partials/` are returned by HTMX endpoints and also `{% include %}`d on initial page load so both paths render the same HTML.

**Bottom sheet pattern:** Inventory and Meals pages use a slide-up sheet (`#sheet`, `#overlay`, `#sheet-content`) with `openSheet()` / `closeSheet()` JS helpers defined in the page template. Sheet content is loaded via `hx-get` into `#sheet-content`. Forms inside the sheet target `#item-list` or `#meal-list` and close the sheet via `hx-on::after-request`.

**Item picker in meal form:** `meal_form.html` serialises all selected items into a single hidden `items_json` field as a JSON array before submission (`syncJson()` is called on every change and on `submit`). Each entry is `{id, name, unit, quantity, track_inventory}`. Items from inventory have a numeric `id`; freetext items have `id: null`.

- Inventory item search uses `mousedown` + `e.preventDefault()` on the suggestions box to prevent the input blur from hiding suggestions before the click registers.
- When a freetext item is added, the row shows a toggle: **One-time only** (default, `track_inventory: false`) vs **+ Add to inventory** (`track_inventory: true`).

## Key data model notes

- `Item.track_inventory` — `False` items are hidden from the Inventory page, dashboard expiry/low-stock strips, and the `sorted_items()` query in `routers/items.py`, but are still stored so the AI can see consumption patterns. Set when a user logs a freetext meal item and chooses "One-time only". Added via inline migration in `main.py`.
- `MealItem` is the join table between `Meal` and `Item`. Creating a meal decrements `Item.quantity`; deleting a meal re-increments it. Both happen inside a `db.flush()` + `db.commit()` block with a rollback on failure.
- Inventory list is sorted in Python (not SQL) by `(expires_at is None, expires_at)` — nulls last, soonest expiry first.
- The meal form's `/meals/form` endpoint surfaces all items with `quantity > 0` (both tracked and untracked) for the item search. Freetext items not in inventory are auto-created as `Item` records on meal save, with `quantity=0` and `track_inventory` set by the user's toggle choice.

## Environment

`.env` at the project root is loaded via `pydantic-settings`. Required keys:
```
DATABASE_URL=sqlite:///./food_inventory.db
AI_PROVIDER=groq            # groq | gemini | huggingface (groq is default)
GROQ_API_KEY=...            # if AI_PROVIDER=groq
GEMINI_API_KEY=...          # if AI_PROVIDER=gemini
HUGGINGFACE_API_KEY=...     # if AI_PROVIDER=huggingface
```

The database file is stored at the project root: `food_inventory.db`.

## Phase 5 — AI features (complete)

**Service layer:** `app/services/ai_service.py` — `get_ai_response(prompt, system)` dispatches to the configured provider. Groq (`llama-3.1-8b-instant`) is the default. JSON responses are parsed defensively in each router endpoint via `_parse_json()` which strips markdown fences before parsing.

**Provider options:**

| Provider | Package | Model | Free tier |
|---|---|---|---|
| Groq | `groq` | `llama-3.1-8b-instant` | ~14,400 req/day |
| Gemini | `google-generativeai` | `gemini-1.5-flash` | ~1M tokens/day |
| HuggingFace | `huggingface_hub` | `mistralai/Mistral-7B-Instruct-v0.3` | Rate-limited, less reliable |

**"What should I eat?"** (`POST /ai/suggest-meal`)
- Four meal-type buttons on the `/ai` page (Breakfast, Lunch, Dinner, Snack) each post with `hx-vals` — no separate Generate step.
- Filters 14-day `MealItem` history to the selected meal type, fetches items expiring within 7 days.
- Returns `{ suggestion, reasoning, use_these_items[] }` as JSON; rendered in `partials/ai_suggestion.html` with a meal-type badge.
- `meal_type` is passed to the partial so it can display the correct color-coded badge.

**"What should I restock?"** (`POST /ai/replenish`)
- Gathers three signals: 30-day consumption rate (tracked items only), items below their `low_stock_at` threshold, and items expiring within 14 days.
- `track_inventory=False` items are excluded from all three signals.
- Returns `{ summary, shopping_list: [{ item, reason, urgency: high|medium|low }] }` as JSON.
- Rendered in `partials/ai_replenish.html` as a conversational summary paragraph followed by urgency-badged item cards.

---

### Phase 6 — Polish (not yet built)

- Loading states on AI Generate buttons (disable + spinner while HTMX request is in flight)
- Zero-quantity guard in meal logging — warn if an item being added is already at 0
- Recently used items quick-add in the meal log sheet (query last 7 days of `MealItem`, surface as one-tap suggestions before the search box)
- Item name autocomplete in the Add Item form (query distinct names from `Item` table)
- Mobile testing pass — fix any tap target or scroll issues found on an actual device

---

### Phase 7 — Deployment (not yet built)

Fly.io deployment using the `Dockerfile` and `fly.toml` already present in the repo. See the Deployment files section below for details.

## Deployment files

`Dockerfile`, `.dockerignore`, and `fly.toml` are present for future Fly.io deployment. The `fly.toml` sets `DATABASE_URL=sqlite:////data/food_inventory.db` (pointing to a mounted persistent volume) which overrides the `.env` default. Deployment is not yet set up — these files are ready but the app has not been deployed.
