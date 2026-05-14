import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item, Meal, MealItem
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
    db: Session = Depends(get_db),
    meal_type: str = Form(""),
):
    cutoff = datetime.utcnow() - timedelta(days=14)
    recent_q = (
        db.query(MealItem, Meal)
        .join(Meal, MealItem.meal_id == Meal.id)
        .filter(Meal.logged_at >= cutoff)
    )
    if meal_type:
        recent_q = recent_q.filter(Meal.meal_type == meal_type.upper())
    recent = recent_q.all()

    by_item: dict = defaultdict(float)
    for mi, meal in recent:
        if mi.item:
            by_item[mi.item.name] += mi.quantity_used

    expiry_cutoff = datetime.utcnow() + timedelta(days=7)
    expiring = (
        db.query(Item)
        .filter(
            Item.track_inventory == True,
            Item.expires_at.isnot(None),
            Item.expires_at <= expiry_cutoff,
            Item.quantity > 0,
        )
        .order_by(Item.expires_at.asc())
        .all()
    )

    history_lines = [
        f"- {name}: used {round(qty, 1)} times" for name, qty in by_item.items()
    ]
    expiry_lines = []
    for item in expiring:
        days = (item.expires_at.date() - datetime.utcnow().date()).days
        label = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        expiry_lines.append(
            f"- {item.name}: expires {label}, {round(item.quantity, 1)} {item.unit} left"
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
async def replenish(request: Request, db: Session = Depends(get_db)):
    now = datetime.utcnow()

    # Consumption over last 30 days (tracked items only)
    cutoff = now - timedelta(days=30)
    rows = (
        db.query(MealItem.item_id, func.sum(MealItem.quantity_used).label("total"))
        .join(Meal, MealItem.meal_id == Meal.id)
        .filter(Meal.logged_at >= cutoff)
        .group_by(MealItem.item_id)
        .all()
    )
    consumption_lines = []
    for item_id, total in rows:
        item = db.query(Item).filter(Item.id == item_id, Item.track_inventory == True).first()
        if not item:
            continue
        avg = round(total / 30, 3)
        days_left = round(item.quantity / avg, 1) if avg > 0 else None
        suffix = f" (~{days_left} days left at this rate)" if days_left is not None else ""
        consumption_lines.append(
            f"- {item.name}: used {round(total, 1)} {item.unit} in 30 days "
            f"(avg {avg}/day), currently {round(item.quantity, 1)} {item.unit} in stock{suffix}"
        )

    # Items below their low-stock threshold
    low_stock = (
        db.query(Item)
        .filter(
            Item.track_inventory == True,
            Item.low_stock_at.isnot(None),
            Item.quantity <= Item.low_stock_at,
        )
        .order_by(Item.name)
        .all()
    )
    low_stock_lines = [
        f"- {item.name}: {round(item.quantity, 1)} {item.unit} left "
        f"(low-stock threshold: {item.low_stock_at} {item.unit})"
        for item in low_stock
    ]

    # Tracked items expiring within 14 days
    expiry_cutoff = now + timedelta(days=14)
    expiring = (
        db.query(Item)
        .filter(
            Item.track_inventory == True,
            Item.expires_at.isnot(None),
            Item.expires_at <= expiry_cutoff,
            Item.quantity > 0,
        )
        .order_by(Item.expires_at.asc())
        .all()
    )
    expiry_lines = []
    for item in expiring:
        days = (item.expires_at.date() - now.date()).days
        label = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        expiry_lines.append(
            f"- {item.name}: expires {label}, {round(item.quantity, 1)} {item.unit} remaining"
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
