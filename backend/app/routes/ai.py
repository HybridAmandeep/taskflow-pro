"""AI-powered dependency suggestion routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Task, Dependency
from app.schemas import AISuggestRequest, AISuggestResponse
from app.ai_service import suggest_dependencies

router = APIRouter(prefix="/api/ai", tags=["AI Suggestions"])


@router.post("/suggest-dependencies", response_model=AISuggestResponse)
async def get_ai_suggestions(
    data: AISuggestRequest, session: AsyncSession = Depends(get_db)
):
    """
    Get AI-suggested dependencies for a task.
    Suggestions include confidence scores and reasoning.
    All suggestions require explicit human approval before being added.
    """
    # Fetch target task
    result = await session.execute(select(Task).where(Task.id == data.task_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, f"Task {data.task_id} not found")

    # Fetch all tasks
    all_result = await session.execute(select(Task))
    all_tasks = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description or "",
            "column": t.column.value if t.column else "backlog",
        }
        for t in all_result.scalars().all()
    ]

    # Fetch existing dependencies
    dep_result = await session.execute(select(Dependency))
    existing_deps = [
        {
            "upstream_task_id": d.upstream_task_id,
            "downstream_task_id": d.downstream_task_id,
        }
        for d in dep_result.scalars().all()
    ]

    # Get AI suggestions
    result = await suggest_dependencies(
        target_task={
            "id": target.id,
            "title": target.title,
            "description": target.description or "",
        },
        all_tasks=all_tasks,
        existing_deps=existing_deps,
    )

    return result
