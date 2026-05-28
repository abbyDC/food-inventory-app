from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import ai, items, meals

app = FastAPI(title="Food Inventory")

_BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

templates = Jinja2Templates(directory=str(_BASE / "templates"))

app.include_router(items.router)
app.include_router(meals.router)
app.include_router(ai.router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    today = date.today()
    today_str = today.strftime("%A, %B") + " " + str(today.day)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "today_str": today_str,
        },
    )
