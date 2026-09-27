from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


# ── Task Schemas ────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    column: str = "backlog"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: int = 1
    sort_order: int = 0


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None


class TaskMove(BaseModel):
    column: str
    sort_order: int = 0


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    column: str
    sort_order: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: int
    status: str = "ready"  # Computed: "ready" | "blocked"
    blocked_by: list[str] = []  # List of upstream task titles that are blocking
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Dependency Schemas ──────────────────────────────────────────────

class DependencyCreate(BaseModel):
    upstream_task_id: str
    downstream_task_id: str
    source: str = "manual"


class DependencyResponse(BaseModel):
    id: str
    upstream_task_id: str
    downstream_task_id: str
    upstream_title: str = ""
    downstream_title: str = ""
    source: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ── DAG Schemas ─────────────────────────────────────────────────────

class WhatIfRequest(BaseModel):
    task_id: str
    new_start_date: Optional[date] = None
    new_end_date: Optional[date] = None


class WhatIfResult(BaseModel):
    task_id: str
    title: str
    old_start: Optional[str] = None
    old_end: Optional[str] = None
    new_start: Optional[str] = None
    new_end: Optional[str] = None
    shift_days: int


class CriticalPathResponse(BaseModel):
    path: list[dict]
    total_duration_days: int


class HealthMetrics(BaseModel):
    total_tasks: int
    blocked_count: int
    ready_count: int
    done_count: int
    critical_path_length: int
    critical_path_duration_days: int
    average_chain_depth: float
    total_dependencies: int
    bottlenecks: list[dict]


# ── AI Schemas ──────────────────────────────────────────────────────

class AISuggestRequest(BaseModel):
    task_id: str


class AISuggestion(BaseModel):
    upstream_task_id: str
    upstream_task_title: str
    confidence: int = Field(..., ge=0, le=100)
    reasoning: str


class AISuggestResponse(BaseModel):
    suggestions: list[AISuggestion]
    model_used: str = ""
    prompt_summary: str = ""
