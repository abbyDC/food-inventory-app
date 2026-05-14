import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item, Meal, MealItem

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def get_meals_for_date(db: Session, target_date: date):
    start = datetime.combine(target_date, time.min)
    end = datetime.combine(target_date, time.max)
    return (
        db.query(Meal)
        .filter(Meal.logged_at >= start, Meal.logged_at <= end)
        .order_by(Meal.logged_at.asc())
        .all()
    )


def meal_list_response(request: Request, db: Session, target_date: date):
    meals = get_meals_for_date(db, target_date)
    return templates.TemplateResponse(
        "partials/meal_list.html",
        {"request": request, "meals": meals, "selected_date": target_date},
    )


def week_days():
    today = date.today()
    return [today - timedelta(days=i) for i in range(6, -1, -1)]


# --- Pages ---

@router.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    meals = get_meals_for_date(db, today)
    return templates.TemplateResponse(
        "meals.html",
        {
            "request": request,
            "meals": meals,
            "days": week_days(),
            "today": today,
            "selected_date": today,
            "active_page": "meals",
        },
    )


# --- Partials ---

@router.get("/meals/list", response_class=HTMLResponse)
async def meal_list_partial(request: Request, date: str = "", db: Session = Depends(get_db)):
    target = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.today().date()
    return meal_list_response(request, db, target)


@router.get("/meals/form", response_class=HTMLResponse)
async def meal_form(request: Request, date: str = "", db: Session = Depends(get_db)):
    items = db.query(Item).filter(Item.quantity > 0).order_by(Item.name).all()
    inventory_json = json.dumps(
        [{"id": i.id, "name": i.name, "quantity": i.quantity, "unit": i.unit} for i in items]
    )
    selected_date = date or datetime.today().date().isoformat()
    return templates.TemplateResponse(
        "partials/meal_form.html",
        {"request": request, "inventory_json": inventory_json, "selected_date": selected_date},
    )


# --- CRUD ---

@router.post("/meals", response_class=HTMLResponse)
async def create_meal(
    request: Request,
    db: Session = Depends(get_db),
    meal_type: str = Form(...),
    meal_date: str = Form(...),
    notes: str = Form(""),
    items_json: str = Form("[]"),
):
    entries = json.loads(items_json)
    now = datetime.now()
    logged_at = datetime.strptime(meal_date, "%Y-%m-%d").replace(
        hour=now.hour, minute=now.minute
    )
    try:
        meal = Meal(meal_type=meal_type, logged_at=logged_at, notes=notes.strip() or None)
        db.add(meal)
        db.flush()

        for entry in entries:
            qty = max(0.1, float(entry.get("quantity", 1)))
            item_id = entry.get("id")

            if item_id:
                # Existing inventory item
                item = db.query(Item).filter(Item.id == item_id).first()
                if item:
                    db.add(MealItem(meal_id=meal.id, item_id=item.id, quantity_used=qty))
                    item.quantity = max(0, round(item.quantity - qty, 2))
                    item.updated_at = now
            else:
                # Not in inventory — create Item record so AI can learn consumption patterns
                name = entry.get("name", "").strip()
                unit = entry.get("unit", "units")
                track = entry.get("track_inventory", False)
                if name:
                    new_item = Item(
                        name=name,
                        unit=unit,
                        quantity=0,
                        bought_at=now,
                        track_inventory=track,
                    )
                    db.add(new_item)
                    db.flush()
                    db.add(MealItem(meal_id=meal.id, item_id=new_item.id, quantity_used=qty))

        db.commit()
    except Exception:
        db.rollback()
        raise

    target = datetime.strptime(meal_date, "%Y-%m-%d").date()
    return meal_list_response(request, db, target)


@router.delete("/meals/{meal_id}", response_class=HTMLResponse)
async def delete_meal(meal_id: int, request: Request, db: Session = Depends(get_db)):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    target = date.today()
    if meal:
        target = meal.logged_at.date()
        for mi in meal.meal_items:
            item = db.query(Item).filter(Item.id == mi.item_id).first()
            if item:
                item.quantity = round(item.quantity + mi.quantity_used, 2)
        db.delete(meal)
        db.commit()
    return meal_list_response(request, db, target)
