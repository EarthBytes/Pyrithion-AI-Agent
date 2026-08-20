from pathlib import Path

import asyncio

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import TypeAdapter, ValidationError
from pydantic.networks import EmailStr

from app.routes.tasks import _run_in_background
from app.utils.id_generator import generate_task_id

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
email_adapter = TypeAdapter(EmailStr)


@router.get("/", response_class=HTMLResponse)
async def ask_form(request: Request):
    return templates.TemplateResponse(
        request,
        "ask.html",
        {"request": request, "submitted": False, "error": None},
    )


@router.post("/ask", response_class=HTMLResponse)
async def submit_ask(
    request: Request,
    goal: str = Form(...),
    email: str = Form(...),
):
    try:
        validated_email = email_adapter.validate_python(email)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "ask.html",
            {
                "request": request,
                "submitted": False,
                "error": "Please enter a valid email address.",
                "goal": goal,
                "email": email,
            },
            status_code=400,
        )

    task_id = generate_task_id()
    orchestrator = router.orchestrator
    task_store = router.task_store

    await task_store.persist_create(task_id, goal.strip(), str(validated_email))
    asyncio.create_task(
        _run_in_background(
            task_id,
            goal.strip(),
            str(validated_email),
            orchestrator,
            task_store,
        )
    )

    return templates.TemplateResponse(
        request,
        "ask.html",
        {
            "request": request,
            "submitted": True,
            "error": None,
            "goal": goal,
            "email": email,
            "task_id": task_id,
        },
    )
