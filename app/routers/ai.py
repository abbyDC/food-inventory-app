import json
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.ai_service import get_ai_response

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```\s*$", "", raw.strip(), flags=re.MULTILINE)
    return json.loads(raw.strip())


@router.get("/ai", response_class=HTMLResponse)
async def ai_page(request: Request):
    return templates.TemplateResponse("ai.html", {"request": request, "active_page": "ai"})


@router.post("/ai/suggest-meal", response_class=HTMLResponse)
async def suggest_meal(
    request: Request,
    meal_type: str = Form(""),
    history_json: str = Form("[]"),
    expiry_json: str = Form("[]"),
):
    try:
        history = json.loads(history_json)
    except Exception:
        history = []
    try:
        expiring = json.loads(expiry_json)
    except Exception:
        expiring = []

    history_lines = [
        f"- {e['name']}: used {round(float(e.get('quantity_used', 0)), 1)} times"
        for e in history if e.get("name")
    ]
    expiry_lines = []
    for e in expiring:
        if not e.get("name") or not e.get("expires_at"):
            continue
        from datetime import date
        today = date.today()
        try:
            exp_date = date.fromisoformat(e["expires_at"])
            days = (exp_date - today).days
        except Exception:
            days = None
        if days is not None:
            label = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        else:
            label = "soon"
        expiry_lines.append(
            f"- {e['name']}: expires {label}, {round(float(e.get('quantity', 0)), 1)} {e.get('unit', 'units')} left"
        )

    meal_label = meal_type.capitalize() if meal_type else "any meal"
    parts = [
        f"I need a {meal_label} suggestion.",
        ("Recent {label} history (14 days):\n" + "\n".join(history_lines)).format(
            label=meal_label.lower()
        )
        if history_lines
        else f"No recent {meal_label.lower()} history.",
        ("Expiring soon:\n" + "\n".join(expiry_lines)) if expiry_lines else "Nothing expiring soon.",
        'Return JSON only: {"suggestion":"...","reasoning":"...","use_these_items":["item"]}',
    ]
    prompt = "\n\n".join(parts)
    system = "You are a helpful kitchen assistant. Respond only with valid JSON, no markdown fences."

    data = error = None
    try:
        data = _parse_json(get_ai_response(prompt, system))
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse(
        "partials/ai_suggestion.html",
        {"request": request, "data": data, "error": error, "meal_type": meal_type},
    )


@router.post("/ai/replenish", response_class=HTMLResponse)
async def replenish(
    request: Request,
    consumption_json: str = Form("[]"),
    low_stock_json: str = Form("[]"),
    expiry_json: str = Form("[]"),
):
    try:
        consumption = json.loads(consumption_json)
    except Exception:
        consumption = []
    try:
        low_stock = json.loads(low_stock_json)
    except Exception:
        low_stock = []
    try:
        expiring = json.loads(expiry_json)
    except Exception:
        expiring = []

    consumption_lines = []
    for e in consumption:
        if not e.get("name"):
            continue
        total = float(e.get("quantity_used_30d", 0))
        current = float(e.get("current_quantity", 0))
        unit = e.get("unit", "units")
        avg = round(total / 30, 3)
        days_left = round(current / avg, 1) if avg > 0 else None
        suffix = f" (~{days_left} days left at this rate)" if days_left is not None else ""
        consumption_lines.append(
            f"- {e['name']}: used {round(total, 1)} {unit} in 30 days "
            f"(avg {avg}/day), currently {round(current, 1)} {unit} in stock{suffix}"
        )

    low_stock_lines = [
        f"- {e['name']}: {round(float(e.get('quantity', 0)), 1)} {e.get('unit', 'units')} left "
        f"(low-stock threshold: {e.get('low_stock_at')} {e.get('unit', 'units')})"
        for e in low_stock if e.get("name")
    ]

    expiry_lines = []
    for e in expiring:
        if not e.get("name") or not e.get("expires_at"):
            continue
        from datetime import date
        today = date.today()
        try:
            exp_date = date.fromisoformat(e["expires_at"])
            days = (exp_date - today).days
        except Exception:
            days = None
        if days is not None:
            label = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        else:
            label = "soon"
        expiry_lines.append(
            f"- {e['name']}: expires {label}, {round(float(e.get('quantity', 0)), 1)} {e.get('unit', 'units')} remaining"
        )

    sections = []
    if consumption_lines:
        sections.append("Consumption (last 30 days):\n" + "\n".join(consumption_lines))
    if low_stock_lines:
        sections.append("Below low-stock threshold:\n" + "\n".join(low_stock_lines))
    if expiry_lines:
        sections.append("Expiring within 14 days:\n" + "\n".join(expiry_lines))

    data = error = None
    if sections:
        prompt = (
            "\n\n".join(sections)
            + "\n\nBased on all of the above, give me a restock recommendation. "
            "Return JSON only:\n"
            '{"summary":"3-5 sentence friendly overview prioritising urgent items",'
            '"shopping_list":[{"item":"...","reason":"...","urgency":"high|medium|low"}]}'
        )
        system = "You are a helpful kitchen assistant. Respond only with valid JSON, no markdown fences."
        try:
            data = _parse_json(get_ai_response(prompt, system))
        except Exception as e:
            error = str(e)

    return templates.TemplateResponse(
        "partials/ai_replenish.html",
        {"request": request, "data": data, "error": error},
    )
