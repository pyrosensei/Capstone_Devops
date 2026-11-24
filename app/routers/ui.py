from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import Settings, get_settings

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, settings: Settings = Depends(get_settings)):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"demo_mode": settings.demo_mode}
    )
