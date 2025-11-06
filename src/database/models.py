"""SQLAlchemy models for the Prow audit database."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):  # type: ignore
    """Base class for all database models."""

    pass


class AuditMetadata(Base):
    """Stores metadata about the audit scan for accurate statistics."""

    __tablename__ = "audit_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total_runs_scanned: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_runs_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    successful_runs_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scan_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    filter_stage: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    analysis_duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    semantic_clustering_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    similarity_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AuditMetadata(scanned={self.total_runs_scanned}, "
            f"failed={self.failed_runs_analyzed})>"
        )


class Run(Base):
    """Represents a single Prow job run."""

    __tablename__ = "runs"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pr_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    job_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    build_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revision: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    repo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stages: Mapped[List["Stage"]] = relationship(
        "Stage", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Run(id={self.id}, pr={self.pr_number}, "
            f"job={self.job_name}, build={self.build_number})>"
        )


class Stage(Base):
    """Represents a stage within a Prow job run."""

    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id"), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["Run"] = relationship("Run", back_populates="stages")
    steps: Mapped[List["Step"]] = relationship(
        "Step", back_populates="stage", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Stage(id={self.id}, name={self.stage_name}, status={self.status})>"


class Step(Base):
    """Represents a step within a stage."""

    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    log_path: Mapped[str] = mapped_column(String(500), nullable=False)
    log_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_sidecar_logs: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stage: Mapped["Stage"] = relationship("Stage", back_populates="steps")
    analysis: Mapped[Optional["StepAnalysis"]] = relationship(
        "StepAnalysis",
        back_populates="step",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Step(id={self.id}, name={self.step_name}, status={self.status})>"


class StepAnalysis(Base):
    """Stores LLM analysis results for a step."""

    __tablename__ = "step_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step_id: Mapped[int] = mapped_column(
        ForeignKey("steps.id"), nullable=False, unique=True, index=True
    )
    analysis_text: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    llm_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    step: Mapped["Step"] = relationship("Step", back_populates="analysis")

    def __repr__(self) -> str:
        return (
            f"<StepAnalysis(id={self.id}, step_id={self.step_id}, "
            f"category={self.error_category})>"
        )


def create_database(database_url: str) -> None:
    """Create all database tables.

    Args:
        database_url: SQLAlchemy database URL
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
