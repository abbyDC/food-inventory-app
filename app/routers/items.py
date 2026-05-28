from datetime import date
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
router = APIRouter()


@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "active_page": "inventory"},
    )


@router.get("/items/form", response_class=HTMLResponse)
async def item_form(request: Request):
    return templates.TemplateResponse(
        "partials/item_form.html",
        {"request": request, "today_str": date.today().isoformat()},
    )
