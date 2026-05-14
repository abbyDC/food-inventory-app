from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def sorted_items(db: Session, query: str = ""):
    q = db.query(Item).filter(Item.track_inventory == True)
    if query:
        q = q.filter(Item.name.ilike(f"%{query}%"))
    items = q.all()
    items.sort(key=lambda x: (x.expires_at is None, x.expires_at or datetime.max))
    return items


def item_list_response(request: Request, db: Session, query: str = ""):
    items = sorted_items(db, query)
    return templates.TemplateResponse(
        "partials/item_list.html",
        {"request": request, "items": items, "today": date.today()},
    )


# --- Pages ---

@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    items = sorted_items(db)
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "items": items, "today": date.today(), "active_page": "inventory"},
    )


# --- Form partials (loaded into bottom sheet via HTMX) ---

@router.get("/items/form", response_class=HTMLResponse)
async def item_form_new(request: Request):
    return templates.TemplateResponse(
        "partials/item_form.html",
        {"request": request, "item": None, "today_str": date.today().isoformat()},
    )


@router.get("/items/{item_id}/form", response_class=HTMLResponse)
async def item_form_edit(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    return templates.TemplateResponse(
        "partials/item_form.html",
        {"request": request, "item": item, "today_str": date.today().isoformat()},
    )


# --- Search ---

@router.get("/items/search", response_class=HTMLResponse)
async def search_items(request: Request, q: str = "", db: Session = Depends(get_db)):
    return item_list_response(request, db, query=q)


# --- CRUD ---

@router.post("/items", response_class=HTMLResponse)
async def create_item(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    category: str = Form(""),
    quantity: float = Form(1.0),
    unit: str = Form("units"),
    bought_at: str = Form(""),
    expires_at: str = Form(""),
    low_stock_at: str = Form(""),
):
    item = Item(
        name=name.strip(),
        category=category.strip() or None,
        quantity=quantity,
        unit=unit.strip() or "units",
        bought_at=datetime.strptime(bought_at, "%Y-%m-%d") if bought_at else datetime.utcnow(),
        expires_at=datetime.strptime(expires_at, "%Y-%m-%d") if expires_at else None,
        low_stock_at=float(low_stock_at) if low_stock_at else None,
    )
    db.add(item)
    db.commit()
    return item_list_response(request, db)


@router.patch("/items/{item_id}", response_class=HTMLResponse)
async def update_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    category: str = Form(""),
    quantity: float = Form(1.0),
    unit: str = Form("units"),
    bought_at: str = Form(""),
    expires_at: str = Form(""),
    low_stock_at: str = Form(""),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        item.name = name.strip()
        item.category = category.strip() or None
        item.quantity = quantity
        item.unit = unit.strip() or "units"
        item.bought_at = datetime.strptime(bought_at, "%Y-%m-%d") if bought_at else item.bought_at
        item.expires_at = datetime.strptime(expires_at, "%Y-%m-%d") if expires_at else None
        item.low_stock_at = float(low_stock_at) if low_stock_at else None
        item.updated_at = datetime.utcnow()
        db.commit()
    return item_list_response(request, db)


@router.delete("/items/{item_id}", response_class=HTMLResponse)
async def delete_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return item_list_response(request, db)


@router.patch("/items/{item_id}/use", response_class=HTMLResponse)
async def use_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item and item.quantity > 0:
        item.quantity = round(item.quantity - 1, 2)
        item.updated_at = datetime.utcnow()
        db.commit()
    return item_list_response(request, db)
