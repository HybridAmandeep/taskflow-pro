"""
Seed 10 realistic tasks with dependencies for a software project workflow.
Run on first startup if the database is empty.
"""

from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Task, Dependency, TaskColumn


SEED_TASKS = [
    {
        "id": "task-001",
        "title": "Define Product Requirements",
        "description": "Gather stakeholder inputs, define user stories, acceptance criteria, and MVP scope. Create the PRD document for team alignment.",
        "column": TaskColumn.DONE,
        "sort_order": 0,
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 9, 3),
        "duration_days": 3,
    },
    {
        "id": "task-002",
        "title": "Design Database Schema",
        "description": "Design the relational schema — tables for users, tasks, dependencies, and snapshots. Define indexes, constraints, and migration strategy.",
        "column": TaskColumn.DONE,
        "sort_order": 1,
        "start_date": date(2026, 9, 4),
        "end_date": date(2026, 9, 6),
        "duration_days": 3,
    },
    {
        "id": "task-003",
        "title": "Set Up CI/CD Pipeline",
        "description": "Configure GitHub Actions for lint, test, build, and deploy. Set up staging and production environments with automated deployments.",
        "column": TaskColumn.IN_PROGRESS,
        "sort_order": 0,
        "start_date": date(2026, 9, 4),
        "end_date": date(2026, 9, 7),
        "duration_days": 4,
    },
    {
        "id": "task-004",
        "title": "Implement User Authentication API",
        "description": "Build JWT-based auth endpoints — signup, login, token refresh, password reset. Include rate limiting and input validation.",
        "column": TaskColumn.IN_PROGRESS,
        "sort_order": 1,
        "start_date": date(2026, 9, 7),
        "end_date": date(2026, 9, 11),
        "duration_days": 5,
    },
    {
        "id": "task-005",
        "title": "Build REST API Endpoints",
        "description": "Implement CRUD endpoints for tasks and dependencies. Include pagination, filtering, error handling, and OpenAPI documentation.",
        "column": TaskColumn.IN_PROGRESS,
        "sort_order": 2,
        "start_date": date(2026, 9, 7),
        "end_date": date(2026, 9, 12),
        "duration_days": 6,
    },
    {
        "id": "task-006",
        "title": "Create Frontend Component Library",
        "description": "Build reusable UI components — buttons, modals, cards, inputs, dropdowns. Establish the design system with colors, typography, and spacing.",
        "column": TaskColumn.REVIEW,
        "sort_order": 0,
        "start_date": date(2026, 9, 4),
        "end_date": date(2026, 9, 8),
        "duration_days": 5,
    },
    {
        "id": "task-007",
        "title": "Integrate Auth with Frontend",
        "description": "Connect the login/signup UI to the auth API. Implement token storage, protected routes, and session management on the client side.",
        "column": TaskColumn.BACKLOG,
        "sort_order": 0,
        "start_date": date(2026, 9, 12),
        "end_date": date(2026, 9, 15),
        "duration_days": 4,
    },
    {
        "id": "task-008",
        "title": "Write Integration Tests",
        "description": "Write end-to-end tests covering auth flows, task CRUD, dependency management, and schedule propagation. Target 80% coverage.",
        "column": TaskColumn.BACKLOG,
        "sort_order": 1,
        "start_date": date(2026, 9, 13),
        "end_date": date(2026, 9, 17),
        "duration_days": 5,
    },
    {
        "id": "task-009",
        "title": "Perform Security Audit",
        "description": "Review authentication, authorization, input validation, SQL injection prevention, XSS protection, and CORS configuration. Fix identified vulnerabilities.",
        "column": TaskColumn.BACKLOG,
        "sort_order": 2,
        "start_date": date(2026, 9, 18),
        "end_date": date(2026, 9, 20),
        "duration_days": 3,
    },
    {
        "id": "task-010",
        "title": "Deploy to Production",
        "description": "Final deployment — run migrations, configure environment variables, set up monitoring/alerting, verify health checks, and do a smoke test.",
        "column": TaskColumn.BACKLOG,
        "sort_order": 3,
        "start_date": date(2026, 9, 21),
        "end_date": date(2026, 9, 23),
        "duration_days": 3,
    },
]

# Dependencies: (upstream_id, downstream_id)
SEED_DEPENDENCIES = [
    ("task-001", "task-002"),  # Requirements → DB Schema
    ("task-001", "task-003"),  # Requirements → CI/CD
    ("task-001", "task-006"),  # Requirements → Component Library
    ("task-002", "task-004"),  # DB Schema → Auth API
    ("task-002", "task-005"),  # DB Schema → REST API
    ("task-004", "task-007"),  # Auth API → Auth Frontend Integration
    ("task-006", "task-007"),  # Component Library → Auth Frontend Integration (diamond)
    ("task-004", "task-008"),  # Auth API → Integration Tests
    ("task-005", "task-008"),  # REST API → Integration Tests
    ("task-007", "task-009"),  # Auth Frontend → Security Audit
    ("task-008", "task-009"),  # Integration Tests → Security Audit (diamond)
    ("task-003", "task-010"),  # CI/CD → Deploy
    ("task-009", "task-010"),  # Security Audit → Deploy (convergence)
]


async def seed_database(session: AsyncSession):
    """Insert seed data if the tasks table is empty, or normalize existing sort orders."""
    result = await session.execute(select(func.count()).select_from(Task))
    count = result.scalar()

    if count > 0:
        # Normalize sort orders in existing DB to ensure reliable board positions
        for col in TaskColumn:
            res = await session.execute(
                select(Task).where(Task.column == col).order_by(Task.sort_order, Task.created_at, Task.id)
            )
            col_tasks = list(res.scalars().all())
            for idx, t in enumerate(col_tasks):
                t.sort_order = idx
        await session.commit()
        return

    # Insert tasks
    for task_data in SEED_TASKS:
        task = Task(**task_data)
        session.add(task)

    await session.flush()

    # Insert dependencies
    for upstream_id, downstream_id in SEED_DEPENDENCIES:
        dep = Dependency(
            upstream_task_id=upstream_id,
            downstream_task_id=downstream_id,
            source="manual",
        )
        session.add(dep)

    await session.commit()
    print(f"[OK] Seeded {len(SEED_TASKS)} tasks and {len(SEED_DEPENDENCIES)} dependencies.")
