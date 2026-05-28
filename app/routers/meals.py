from datetime import date as date_cls, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def week_days():
    today = date_cls.today()
    return [today - timedelta(days=i) for i in range(6, -1, -1)]


@router.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request):
    today = date_cls.today()
    return templates.TemplateResponse(
        "meals.html",
        {
            "request": request,
            "days": week_days(),
            "today": today,
            "active_page": "meals",
        },
    )


@router.get("/meals/form", response_class=HTMLResponse)
async def meal_form(request: Request, date: str = ""):
    selected_date = date or date_cls.today().isoformat()
    return templates.TemplateResponse(
        "partials/meal_form.html",
        {"request": request, "selected_date": selected_date},
    )
