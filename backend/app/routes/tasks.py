"""Task CRUD and movement routes."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Task, Dependency, TaskColumn
from app.schemas import TaskCreate, TaskUpdate, TaskMove, TaskResponse
from app.dag_helpers import build_dag_from_db

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def _task_column_from_str(col: str) -> TaskColumn:
    try:
        return TaskColumn(col)
    except ValueError:
        raise HTTPException(400, f"Invalid column: {col}. Must be one of: backlog, in_progress, review, done")


async def _build_task_response(task: Task, session: AsyncSession) -> dict:
    """Build a task response dict with computed status and blocked_by info."""
    dag = await build_dag_from_db(session)
    status = dag.compute_status(task.id)

    blocked_by = []
    if status == "blocked":
        upstreams = dag.reverse_adj.get(task.id, set())
        for uid in upstreams:
            ud = dag.task_data.get(uid, {})
            if ud.get("column") != "done":
                blocked_by.append(ud.get("title", uid))

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "column": task.column.value if task.column else "backlog",
        "sort_order": task.sort_order if task.sort_order is not None else 0,
        "start_date": task.start_date,
        "end_date": task.end_date,
        "duration_days": task.duration_days or 1,
        "status": status,
        "blocked_by": blocked_by,
        "created_at": str(task.created_at) if task.created_at else None,
        "updated_at": str(task.updated_at) if task.updated_at else None,
    }


@router.get("", response_model=list[TaskResponse])
async def list_tasks(session: AsyncSession = Depends(get_db)):
    """Get all tasks ordered by sort_order with computed dependency status."""
    result = await session.execute(
        select(Task).order_by(Task.column, Task.sort_order, Task.created_at)
    )
    tasks = result.scalars().all()
    dag = await build_dag_from_db(session)

    response = []
    for task in tasks:
        status = dag.compute_status(task.id)
        blocked_by = []
        if status == "blocked":
            for uid in dag.reverse_adj.get(task.id, set()):
                ud = dag.task_data.get(uid, {})
                if ud.get("column") != "done":
                    blocked_by.append(ud.get("title", uid))

        response.append({
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "column": task.column.value if task.column else "backlog",
            "sort_order": task.sort_order if task.sort_order is not None else 0,
            "start_date": task.start_date,
            "end_date": task.end_date,
            "duration_days": task.duration_days or 1,
            "status": status,
            "blocked_by": blocked_by,
            "created_at": str(task.created_at) if task.created_at else None,
            "updated_at": str(task.updated_at) if task.updated_at else None,
        })

    return response


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, session: AsyncSession = Depends(get_db)):
    """Create a new task placed cleanly at the end of the column."""
    col = _task_column_from_str(data.column)

    # Determine sort_order: place at end of target column if default 0 passed
    res_count = await session.execute(
        select(func.count(Task.id)).where(Task.column == col)
    )
    col_count = res_count.scalar() or 0
    sort_order = col_count if data.sort_order == 0 else data.sort_order

    task = Task(
        title=data.title,
        description=data.description,
        column=col,
        sort_order=sort_order,
        start_date=data.start_date,
        end_date=data.end_date,
        duration_days=data.duration_days,
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)
    return await _build_task_response(task, session)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, session: AsyncSession = Depends(get_db)):
    """Get a single task by ID."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return await _build_task_response(task, session)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str, data: TaskUpdate, session: AsyncSession = Depends(get_db)
):
    """Update task details. Triggers schedule propagation if dates change."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")

    old_end_date = task.end_date
    old_start_date = task.start_date

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.start_date is not None:
        task.start_date = data.start_date
    if data.end_date is not None:
        task.end_date = data.end_date
    if data.duration_days is not None:
        task.duration_days = data.duration_days

    # Calculate schedule shift delta without compounding
    delta_days = 0
    if data.end_date is not None and old_end_date and data.end_date != old_end_date:
        delta_days = (data.end_date - old_end_date).days
    elif data.start_date is not None and old_start_date and data.start_date != old_start_date:
        delta_days = (data.start_date - old_start_date).days
        if data.end_date is None and task.end_date:
            task.end_date += timedelta(days=delta_days)

    if delta_days != 0:
        dag = await build_dag_from_db(session)
        affected = dag.propagate_schedule_change(task_id, delta_days)

        # Apply shifts to downstream tasks in DB
        for affected_id, shift in affected.items():
            r = await session.execute(
                select(Task).where(Task.id == affected_id)
            )
            affected_task = r.scalar_one_or_none()
            if affected_task:
                if affected_task.start_date:
                    affected_task.start_date += timedelta(days=shift)
                if affected_task.end_date:
                    affected_task.end_date += timedelta(days=shift)

    await session.flush()
    await session.refresh(task)
    return await _build_task_response(task, session)


@router.patch("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: str, data: TaskMove, session: AsyncSession = Depends(get_db)
):
    """
    Move a task to a different column or reorder within column.
    Ensures board positions persist reliably across browser refreshes by
    strictly re-indexing sort_order for all affected tasks.
    Also re-evaluates downstream dependency states on regression.
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")

    new_col = _task_column_from_str(data.column)
    old_col = task.column

    # Fetch other tasks in the target column
    res_new = await session.execute(
        select(Task).where(Task.column == new_col, Task.id != task_id).order_by(Task.sort_order, Task.id)
    )
    dest_tasks = list(res_new.scalars().all())

    # Insert task at the requested sort_order position
    target_idx = max(0, min(data.sort_order, len(dest_tasks)))
    dest_tasks.insert(target_idx, task)

    task.column = new_col

    # Re-index all tasks in target column
    for idx, t in enumerate(dest_tasks):
        t.sort_order = idx

    # If moving across columns, re-index tasks in source column as well
    if old_col != new_col:
        res_old = await session.execute(
            select(Task).where(Task.column == old_col, Task.id != task_id).order_by(Task.sort_order, Task.id)
        )
        old_tasks = list(res_old.scalars().all())
        for idx, t in enumerate(old_tasks):
            t.sort_order = idx

    await session.flush()
    await session.refresh(task)

    return await _build_task_response(task, session)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, session: AsyncSession = Depends(get_db)):
    """Delete a task and all its dependency edges, re-indexing remaining tasks."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")

    col = task.column
    await session.delete(task)
    await session.flush()

    # Re-index remaining tasks in this column
    res_rem = await session.execute(
        select(Task).where(Task.column == col).order_by(Task.sort_order, Task.id)
    )
    for idx, t in enumerate(res_rem.scalars().all()):
        t.sort_order = idx
