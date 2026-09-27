"""
Helper module to build DAGEngine from database state.
Centralizes the logic so routes don't duplicate it.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Task, Dependency
from app.dag_engine import DAGEngine


async def build_dag_from_db(session: AsyncSession) -> DAGEngine:
    """Load all tasks and dependencies into a DAGEngine instance."""
    engine = DAGEngine()

    # Load all tasks
    result = await session.execute(select(Task))
    tasks = result.scalars().all()
    for task in tasks:
        engine.add_node(task.id, {
            "title": task.title,
            "description": task.description,
            "column": task.column.value if task.column else "backlog",
            "start_date": task.start_date,
            "end_date": task.end_date,
            "duration_days": task.duration_days or 1,
        })

    # Load all dependencies
    result = await session.execute(select(Dependency))
    deps = result.scalars().all()
    for dep in deps:
        # Directly set edges (skip cycle check since DB data is already valid)
        engine.adjacency[dep.upstream_task_id].add(dep.downstream_task_id)
        engine.reverse_adj[dep.downstream_task_id].add(dep.upstream_task_id)

    return engine
