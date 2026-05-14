from datetime import date, datetime, time, timedelta

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Item, Meal
from app.routers import ai, items, meals

Base.metadata.create_all(bind=engine)

# Inline migration: add track_inventory if it doesn't exist yet
with engine.connect() as _conn:
    try:
        _conn.execute(text("ALTER TABLE items ADD COLUMN track_inventory BOOLEAN NOT NULL DEFAULT 1"))
        _conn.commit()
    except Exception:
        pass

app = FastAPI(title="Food Inventory")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(items.router)
app.include_router(meals.router)
app.include_router(ai.router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()

    expiring_soon = (
        db.query(Item)
        .filter(
            Item.track_inventory == True,
            Item.expires_at.isnot(None),
            Item.expires_at <= datetime.combine(today + timedelta(days=7), time.max),
        )
        .order_by(Item.expires_at.asc())
        .all()
    )

    low_stock = (
        db.query(Item)
        .filter(
            Item.track_inventory == True,
            Item.low_stock_at.isnot(None),
            Item.quantity <= Item.low_stock_at,
        )
        .order_by(Item.name.asc())
        .all()
    )

    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)
    todays_meals = (
        db.query(Meal)
        .filter(Meal.logged_at >= start, Meal.logged_at <= end)
        .order_by(Meal.logged_at.asc())
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "expiring_soon": expiring_soon,
            "low_stock": low_stock,
            "todays_meals": todays_meals,
            "today": today,
        },
    )
