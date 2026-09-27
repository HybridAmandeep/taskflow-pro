"""Dependency management and DAG analysis routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Task, Dependency
from app.schemas import (
    DependencyCreate, DependencyResponse,
    WhatIfRequest, WhatIfResult,
    CriticalPathResponse, HealthMetrics,
)
from app.dag_helpers import build_dag_from_db

router = APIRouter(prefix="/api", tags=["Dependencies & DAG"])


# ── Dependency CRUD ─────────────────────────────────────────────────

@router.get("/dependencies", response_model=list[DependencyResponse])
async def list_dependencies(session: AsyncSession = Depends(get_db)):
    """List all dependency edges with task titles."""
    result = await session.execute(select(Dependency))
    deps = result.scalars().all()

    response = []
    for dep in deps:
        # Fetch titles
        up_result = await session.execute(
            select(Task.title).where(Task.id == dep.upstream_task_id)
        )
        down_result = await session.execute(
            select(Task.title).where(Task.id == dep.downstream_task_id)
        )
        up_title = up_result.scalar() or ""
        down_title = down_result.scalar() or ""

        response.append({
            "id": dep.id,
            "upstream_task_id": dep.upstream_task_id,
            "downstream_task_id": dep.downstream_task_id,
            "upstream_title": up_title,
            "downstream_title": down_title,
            "source": dep.source.value if dep.source else "manual",
            "created_at": str(dep.created_at) if dep.created_at else None,
        })

    return response


@router.post("/dependencies", response_model=DependencyResponse, status_code=201)
async def create_dependency(
    data: DependencyCreate, session: AsyncSession = Depends(get_db)
):
    """
    Add a dependency edge. Rejects with 409 if it would create a cycle.
    The existing valid graph remains unchanged on rejection.
    """
    # Validate both tasks exist
    for tid, label in [
        (data.upstream_task_id, "Upstream"),
        (data.downstream_task_id, "Downstream"),
    ]:
        r = await session.execute(select(Task).where(Task.id == tid))
        if not r.scalar_one_or_none():
            raise HTTPException(404, f"{label} task {tid} not found")

    # Check for duplicate
    r = await session.execute(
        select(Dependency).where(
            Dependency.upstream_task_id == data.upstream_task_id,
            Dependency.downstream_task_id == data.downstream_task_id,
        )
    )
    if r.scalar_one_or_none():
        raise HTTPException(409, "This dependency already exists")

    # Build DAG and check for cycle
    dag = await build_dag_from_db(session)
    cycle_path = dag.get_cycle_path(data.upstream_task_id, data.downstream_task_id)
    if cycle_path:
        path_titles = [dag.task_data.get(tid, {}).get("title") or tid for tid in cycle_path]
        cycle_str = " → ".join(path_titles)
        up_title = dag.task_data.get(data.upstream_task_id, {}).get("title") or data.upstream_task_id
        down_title = dag.task_data.get(data.downstream_task_id, {}).get("title") or data.downstream_task_id

        raise HTTPException(
            409,
            f"Cannot add dependency: '{up_title}' → '{down_title}' would create a circular relationship "
            f"({cycle_str}). The invalid dependency was rejected and the existing graph remains unchanged."
        )

    # Safe to add
    dep = Dependency(
        upstream_task_id=data.upstream_task_id,
        downstream_task_id=data.downstream_task_id,
        source=data.source,
    )
    session.add(dep)
    await session.flush()
    await session.refresh(dep)

    # Fetch titles for response
    up_r = await session.execute(
        select(Task.title).where(Task.id == dep.upstream_task_id)
    )
    down_r = await session.execute(
        select(Task.title).where(Task.id == dep.downstream_task_id)
    )

    return {
        "id": dep.id,
        "upstream_task_id": dep.upstream_task_id,
        "downstream_task_id": dep.downstream_task_id,
        "upstream_title": up_r.scalar() or "",
        "downstream_title": down_r.scalar() or "",
        "source": dep.source.value if dep.source else "manual",
        "created_at": str(dep.created_at) if dep.created_at else None,
    }


@router.delete("/dependencies/{dep_id}", status_code=204)
async def delete_dependency(dep_id: str, session: AsyncSession = Depends(get_db)):
    """Remove a dependency edge."""
    r = await session.execute(select(Dependency).where(Dependency.id == dep_id))
    dep = r.scalar_one_or_none()
    if not dep:
        raise HTTPException(404, f"Dependency {dep_id} not found")
    await session.delete(dep)


# ── DAG Analysis ────────────────────────────────────────────────────

@router.post("/dag/what-if", response_model=list[WhatIfResult])
async def what_if_simulation(
    data: WhatIfRequest, session: AsyncSession = Depends(get_db)
):
    """
    Simulate a date change WITHOUT applying it.
    Returns a preview of which tasks would shift and by how many days.
    """
    # Verify task exists
    r = await session.execute(select(Task).where(Task.id == data.task_id))
    task = r.scalar_one_or_none()
    if not task:
        raise HTTPException(404, f"Task {data.task_id} not found")

    dag = await build_dag_from_db(session)

    new_start = data.new_start_date or task.start_date
    new_end = data.new_end_date or task.end_date

    if not new_end:
        return []

    results = dag.simulate_date_change(data.task_id, new_start, new_end)
    return results


@router.get("/dag/critical-path", response_model=CriticalPathResponse)
async def get_critical_path(session: AsyncSession = Depends(get_db)):
    """Get the critical path — the longest dependency chain."""
    dag = await build_dag_from_db(session)
    path_ids, total_duration = dag.compute_critical_path()

    path = []
    for tid in path_ids:
        td = dag.task_data.get(tid, {})
        path.append({
            "task_id": tid,
            "title": td.get("title", ""),
            "duration_days": td.get("duration_days", 1),
            "column": td.get("column", ""),
        })

    return {"path": path, "total_duration_days": total_duration}


@router.get("/dag/health", response_model=HealthMetrics)
async def get_health_metrics(session: AsyncSession = Depends(get_db)):
    """Get dependency health dashboard metrics."""
    dag = await build_dag_from_db(session)
    return dag.get_health_metrics()
