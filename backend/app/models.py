import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Text, Integer, Enum, Date, DateTime,
    ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class TaskColumn(str, enum.Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class DependencySource(str, enum.Enum):
    MANUAL = "manual"
    AI_SUGGESTED = "ai_suggested"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    column = Column(Enum(TaskColumn), default=TaskColumn.BACKLOG, nullable=False)
    sort_order = Column(Integer, default=0)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    duration_days = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships for dependency navigation
    upstream_deps = relationship(
        "Dependency",
        foreign_keys="Dependency.downstream_task_id",
        back_populates="downstream_task",
        cascade="all, delete-orphan",
    )
    downstream_deps = relationship(
        "Dependency",
        foreign_keys="Dependency.upstream_task_id",
        back_populates="upstream_task",
        cascade="all, delete-orphan",
    )


class Dependency(Base):
    __tablename__ = "dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upstream_task_id = Column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    downstream_task_id = Column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    source = Column(Enum(DependencySource), default=DependencySource.MANUAL)
    created_at = Column(DateTime, server_default=func.now())

    upstream_task = relationship(
        "Task", foreign_keys=[upstream_task_id], back_populates="downstream_deps"
    )
    downstream_task = relationship(
        "Task", foreign_keys=[downstream_task_id], back_populates="upstream_deps"
    )

    __table_args__ = (
        UniqueConstraint("upstream_task_id", "downstream_task_id", name="uq_dependency"),
    )


class DAGSnapshot(Base):
    __tablename__ = "dag_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_json = Column(Text, nullable=False)
    action_description = Column(String(500), default="")
    created_at = Column(DateTime, server_default=func.now())
