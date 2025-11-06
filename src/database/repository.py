"""Database repository for CRUD operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import AuditMetadata, Base, Run, Stage, Step, StepAnalysis


class AuditRepository:
    """Repository for managing audit database operations."""

    def __init__(self, database_url: str) -> None:
        """Initialize the repository.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            Database session
        """
        return self.SessionLocal()

    def create_run(
        self,
        pr_number: str,
        job_name: str,
        build_number: str,
        timestamp: datetime,
        overall_status: str,
        result: str,
        passed: bool,
        revision: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Run:
        """Create a new run record.

        Args:
            pr_number: Pull request number
            job_name: Name of the job
            build_number: Build identifier
            timestamp: When the run started
            overall_status: Overall status
            result: Result string
            passed: Whether the run passed
            revision: Git revision
            repo: Repository name

        Returns:
            Created or existing Run object
        """
        with self.get_session() as session:
            stmt = select(Run).where(
                Run.build_number == build_number, Run.job_name == job_name
            )
            existing_run = session.execute(stmt).scalar_one_or_none()

            if existing_run:
                return existing_run  # type: ignore

            run = Run(
                pr_number=pr_number,
                job_name=job_name,
                build_number=build_number,
                timestamp=timestamp,
                overall_status=overall_status,
                result=result,
                passed=passed,
                revision=revision,
                repo=repo,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def get_run_by_id(self, run_id: int) -> Optional[Run]:
        """Get a run by ID.

        Args:
            run_id: Run ID

        Returns:
            Run object or None
        """
        with self.get_session() as session:
            return session.get(Run, run_id)  # type: ignore

    def create_stage(
        self,
        run_id: int,
        stage_name: str,
        status: str,
        passed: bool,
        timestamp: Optional[datetime] = None,
        summary: Optional[str] = None,
    ) -> Stage:
        """Create a new stage record.

        Args:
            run_id: Parent run ID
            stage_name: Name of the stage
            status: Stage status
            passed: Whether the stage passed
            timestamp: When the stage ran
            summary: Summary text

        Returns:
            Created Stage object
        """
        with self.get_session() as session:
            stage = Stage(
                run_id=run_id,
                stage_name=stage_name,
                status=status,
                passed=passed,
                timestamp=timestamp,
                summary=summary,
            )
            session.add(stage)
            session.commit()
            session.refresh(stage)
            return stage

    def get_stages_by_run(self, run_id: int) -> List[Stage]:
        """Get all stages for a run.

        Args:
            run_id: Run ID

        Returns:
            List of Stage objects
        """
        with self.get_session() as session:
            stmt = select(Stage).where(Stage.run_id == run_id)
            return list(session.execute(stmt).scalars().all())

    def create_step(
        self,
        stage_id: int,
        step_name: str,
        status: str,
        log_path: str,
        failure_type: Optional[str] = None,
        log_size_bytes: Optional[int] = None,
        has_sidecar_logs: bool = False,
    ) -> Step:
        """Create a new step record.

        Args:
            stage_id: Parent stage ID
            step_name: Name of the step
            status: Step status
            log_path: Path to log file
            failure_type: Type of failure
            log_size_bytes: Size of log file
            has_sidecar_logs: Whether sidecar logs exist

        Returns:
            Created Step object
        """
        with self.get_session() as session:
            step = Step(
                stage_id=stage_id,
                step_name=step_name,
                status=status,
                log_path=log_path,
                failure_type=failure_type,
                log_size_bytes=log_size_bytes,
                has_sidecar_logs=has_sidecar_logs,
            )
            session.add(step)
            session.commit()
            session.refresh(step)
            return step

    def create_step_analysis(
        self,
        step_id: int,
        analysis_text: str,
        confidence: float,
        root_cause: Optional[str] = None,
        error_category: Optional[str] = None,
        llm_reasoning: Optional[str] = None,
        needs_attention: bool = False,
    ) -> StepAnalysis:
        """Create a new step analysis record.

        Args:
            step_id: Step ID
            analysis_text: Analysis text
            confidence: Confidence score
            root_cause: Root cause description
            error_category: Error category
            llm_reasoning: LLM reasoning
            needs_attention: Whether needs attention

        Returns:
            Created StepAnalysis object
        """
        with self.get_session() as session:
            analysis = StepAnalysis(
                step_id=step_id,
                analysis_text=analysis_text,
                confidence=confidence,
                root_cause=root_cause,
                error_category=error_category,
                llm_reasoning=llm_reasoning,
                needs_attention=needs_attention,
            )
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            return analysis

    def create_audit_metadata(
        self,
        total_runs_scanned: int,
        failed_runs_analyzed: int,
        successful_runs_count: int,
        filter_stage: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        analysis_duration_seconds: Optional[int] = None,
        semantic_clustering_enabled: bool = False,
        similarity_threshold: Optional[float] = None,
    ) -> AuditMetadata:
        """Create or update audit metadata."""
        with self.get_session() as session:
            session.execute(delete(AuditMetadata))

            metadata = AuditMetadata(
                total_runs_scanned=total_runs_scanned,
                failed_runs_analyzed=failed_runs_analyzed,
                successful_runs_count=successful_runs_count,
                filter_stage=filter_stage,
                llm_model=llm_model,
                llm_provider=llm_provider,
                analysis_duration_seconds=analysis_duration_seconds,
                semantic_clustering_enabled=semantic_clustering_enabled,
                similarity_threshold=similarity_threshold,
            )
            session.add(metadata)
            session.commit()
            session.refresh(metadata)
            return metadata

    def get_audit_metadata(self) -> Optional[AuditMetadata]:
        """Get the most recent audit metadata.

        Returns:
            Audit metadata or None if not found
        """
        with self.get_session() as session:
            stmt = (
                select(AuditMetadata)
                .order_by(AuditMetadata.scan_timestamp.desc())
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()

    def get_failure_statistics(self) -> dict[str, int]:
        """Get failure statistics.

        Returns:
            Dictionary with statistics
        """
        with self.get_session() as session:
            metadata = self.get_audit_metadata()

            if metadata:
                total_runs = metadata.total_runs_scanned
                failed_runs = metadata.failed_runs_analyzed
            else:
                total_runs = session.execute(select(func.count(Run.id))).scalar_one()
                failed_runs = session.execute(
                    select(func.count(Run.id)).where(Run.passed.is_(False))
                ).scalar_one()

            total_stages = session.execute(select(func.count(Stage.id))).scalar_one()
            failed_stages = session.execute(
                select(func.count(Stage.id)).where(Stage.passed.is_(False))
            ).scalar_one()

            return {
                "total_runs": total_runs,
                "failed_runs": failed_runs,
                "successful_runs": total_runs - failed_runs,
                "total_stages": total_stages,
                "failed_stages": failed_stages,
            }
