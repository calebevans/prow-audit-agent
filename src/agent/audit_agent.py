"""Main DSPy agent orchestrator for Prow audit analysis."""

from pathlib import Path
from typing import Any, Optional

import dspy

from ..database.repository import AuditRepository
from ..database.taxonomy import normalize_error_category, normalize_failure_type
from ..mcp.database_server import DatabaseAnalyticsServer
from ..parsers.log_parser import LogStreamParser, create_log_context
from ..parsers.prow_structure import ProwRunInfo, ProwStageInfo, ProwStructureParser
from ..reporting.report_generator import ReportGenerator
from ..reporting.usage_tracker import UsageTracker
from ..utils.progress import AuditProgress
from .signatures import (
    AnalyzeStepLog,
    EnrichAnalysis,
    SearchDecision,
    StepAnalysisOutput,
)
from .tools import ToolRegistry


class AuditAgent:
    """Main orchestrator for the Prow audit analysis."""

    def __init__(
        self,
        log_path: Path,
        output_path: Path,
        database_path: Path,
        filter_stage: Optional[str] = None,
        use_semantic_clustering: bool = True,
        similarity_threshold: float = 0.65,
    ) -> None:
        """Initialize the audit agent.

        Args:
            log_path: Path to Prow logs
            output_path: Path for output files
            database_path: Path to SQLite database
            filter_stage: Optional stage name filter
            use_semantic_clustering: Use semantic similarity for grouping failures
            similarity_threshold: Cosine similarity threshold for clustering
        """
        self.log_path = Path(log_path)
        self.output_path = Path(output_path)
        self.database_path = Path(database_path)
        self.filter_stage = filter_stage
        self.use_semantic_clustering = use_semantic_clustering
        self.similarity_threshold = similarity_threshold

        # Track total runs for accurate statistics
        self.total_runs_scanned = 0
        self.failed_runs_count = 0

        # Initialize components
        self.parser = ProwStructureParser(log_path)
        self.log_parser = LogStreamParser()
        self.repository = AuditRepository(f"sqlite:///{database_path}")
        self.db_server = DatabaseAnalyticsServer(f"sqlite:///{database_path}")
        self.tools = ToolRegistry()
        self.usage_tracker = UsageTracker()
        self.progress = AuditProgress()
        self.report_generator = ReportGenerator(output_path)

        self.step_analyzer = dspy.ChainOfThought(AnalyzeStepLog)
        self.search_decider = dspy.Predict(SearchDecision)
        self.analysis_enricher = dspy.ChainOfThought(EnrichAnalysis)

    def run_audit(self) -> Path:
        """Run the complete audit process.

        Returns:
            Path to the generated tarball
        """
        self.progress.start()
        self.progress.print_header("Prow Audit Agent v1.0.0")

        try:
            # Phase 0: Pre-filtering
            failed_runs = self._phase_0_prefiltering()

            # Phase 1: Log processing
            self._phase_1_log_processing(failed_runs)

            # Phase 2: Report generation
            report_path = self._phase_2_report_generation()

            # Create tarball
            tarball_path = self._create_output_tarball(report_path)

            self.progress.print_success(f"Audit complete! Results: {tarball_path}")
            return tarball_path

        finally:
            self.progress.stop()

    def regenerate_reports(self) -> Path:
        """Regenerate reports from existing database without re-analyzing logs.

        Returns:
            Path to the generated tarball
        """
        self.progress.start()
        self.progress.print_header("Prow Audit Agent v1.0.0 - Report Generation")

        try:
            # Phase 2: Report generation
            report_path = self._phase_2_report_generation()

            # Create tarball
            tarball_path = self._create_output_tarball(report_path)

            self.progress.print_success(
                f"Report regeneration complete! Results: {tarball_path}"
            )
            return tarball_path

        finally:
            self.progress.stop()

    def _phase_0_prefiltering(self) -> list[ProwRunInfo]:
        """Phase 0: Pre-filter runs to identify failures.

        Returns:
            List of failed run information
        """
        self.progress.add_task(
            "prefilter",
            "Scanning logs and filtering failed runs...",
        )

        total_runs = self.parser.count_total_runs(filter_stage=self.filter_stage)
        failed_count = 0
        failed_runs = []

        for run_info in self.parser.find_failed_runs(filter_stage=self.filter_stage):
            failed_runs.append(run_info)
            failed_count += 1

        # Store for accurate statistics in report
        self.total_runs_scanned = total_runs
        self.failed_runs_count = failed_count

        import os

        self.repository.create_audit_metadata(
            total_runs_scanned=total_runs,
            failed_runs_analyzed=failed_count,
            successful_runs_count=total_runs - failed_count,
            filter_stage=self.filter_stage,
            llm_model=os.getenv("LLM_MODEL"),
            llm_provider=os.getenv("LLM_PROVIDER"),
            semantic_clustering_enabled=self.use_semantic_clustering,
            similarity_threshold=self.similarity_threshold,
        )

        self.progress.complete_task(
            "prefilter", f"Found {failed_count}/{total_runs} failed runs to analyze"
        )

        self.progress.print_info(
            f"Total runs: {total_runs}, Failed: {failed_count}, "
            f"Success rate: {(total_runs - failed_count) / total_runs * 100:.1f}%"
        )

        return failed_runs

    def _phase_1_log_processing(self, failed_runs: list[ProwRunInfo]) -> None:
        """Phase 1: Process logs and analyze failures.

        Args:
            failed_runs: List of failed runs to analyze
        """
        total_steps = sum(
            sum(
                1
                for step in stage.steps
                if not (step.metadata and step.metadata.passed)
            )
            for run in failed_runs
            for stage in run.stages
        )

        self.progress.add_task(
            "log_processing",
            "Analyzing step logs...",
            total=total_steps,
        )

        step_count = 0
        run_count = 0

        for run_info in failed_runs:
            run_count += 1

            run_metadata = run_info.metadata
            if not run_metadata:
                continue

            print(
                f"\n📋 Analyzing Run {run_count}/{len(failed_runs)}: Build {run_info.build_number}"
            )
            print(f"   Job: {run_info.job_name}, Stages: {len(run_info.stages)}")

            run = self.repository.create_run(
                pr_number=run_info.pr_number,
                job_name=run_info.job_name,
                build_number=run_info.build_number,
                timestamp=run_metadata.timestamp,
                overall_status=run_metadata.result,
                result=run_metadata.result,
                passed=run_metadata.passed,
                revision=run_metadata.revision,
            )

            for stage_idx, stage_info in enumerate(run_info.stages, 1):
                failed_steps = [
                    s for s in stage_info.steps if s.metadata and not s.metadata.passed
                ]
                total_steps = len(stage_info.steps)

                print(
                    f"   🔹 Stage {stage_idx}/{len(run_info.stages)}: "
                    f"{stage_info.stage_name} ({len(failed_steps)}/{total_steps} failed steps)"
                )
                stage = self._process_stage(run.id, stage_info)

                for step_idx, step_info in enumerate(stage_info.steps, 1):
                    if step_info.metadata and step_info.metadata.passed:
                        print(
                            f"      ⊘ Step {step_idx}/{total_steps}: "
                            f"{step_info.step_name} (PASSED - skipped)"
                        )
                        continue

                    step_count += 1
                    status_str = "FAILED" if step_info.metadata else "UNKNOWN"
                    print(
                        f"      → Step {step_idx}/{total_steps}: "
                        f"{step_info.step_name} ({status_str} - analyzing)"
                    )
                    self.progress.update_task(
                        "log_processing",
                        description=(
                            f"Analyzing: {stage_info.stage_name}/{step_info.step_name}"
                        ),
                    )

                    self._process_step(stage.id, step_info, stage_info.stage_name)
                    self.progress.update_task("log_processing", advance=1)

        self.progress.complete_task("log_processing", f"Analyzed {step_count} steps")

    def _process_stage(self, run_id: int, stage_info: ProwStageInfo) -> Any:
        """Process a single stage.

        Args:
            run_id: Parent run ID
            stage_info: Stage information

        Returns:
            Stage database object
        """
        stage_metadata = stage_info.metadata

        stage = self.repository.create_stage(
            run_id=run_id,
            stage_name=stage_info.stage_name,
            status=stage_metadata.result if stage_metadata else "UNKNOWN",
            passed=stage_metadata.passed if stage_metadata else False,
            timestamp=stage_metadata.timestamp if stage_metadata else None,
        )

        return stage

    def _process_step(
        self,
        stage_id: int,
        step_info: Any,
        stage_name: str,
    ) -> None:
        """Process a single step with LLM analysis.

        Args:
            stage_id: Parent stage ID
            step_info: Step information
            stage_name: Stage name
        """
        log_context = create_log_context(
            step_info.build_log_path,
            max_head_lines=100,
            max_tail_lines=200,
        )

        try:
            analysis_result = self.step_analyzer(
                step_name=step_info.step_name,
                stage_name=stage_name,
                log_head="\n".join(log_context.get("head_lines", [])[:100]),
                log_tail="\n".join(log_context.get("tail_lines", [])[-200:]),
                extracted_errors="\n".join(
                    log_context.get("extracted_errors", [])[:30]
                ),
                total_lines=log_context.get("total_lines", 0),
            )

            self.usage_tracker.record_llm_call(
                model="configured_model",
                input_tokens=1000,
                output_tokens=500,
                call_type="step_analysis",
            )

            output: StepAnalysisOutput = analysis_result.analysis_output

            print(
                f"         ✓ Analysis complete: {output.status} "
                f"(confidence: {output.confidence:.2f})"
            )

            if output.needs_search:
                print("         🔍 Performing web search for additional context...")
                search_result = self._enrich_analysis(output, step_info.step_name)
                if search_result:
                    output.analysis = search_result
                    print("         ✓ Analysis enriched with search results")

        except Exception as e:
            print(f"         ✗ Analysis failed: {str(e)[:100]}")
            self.progress.print_warning(
                f"Analysis failed for {step_info.step_name}: {e}"
            )
            output = StepAnalysisOutput(
                status="ERROR",
                analysis=f"Analysis failed: {str(e)}",
                confidence=0.0,
            )
            self.usage_tracker.record_llm_call(
                model="configured_model",
                input_tokens=1000,
                output_tokens=0,
                call_type="step_analysis",
                success=False,
                error=str(e),
            )

        normalized_failure_type = normalize_failure_type(output.failure_type)
        normalized_error_category = normalize_error_category(output.error_category)

        log_size = log_context.get("file_size_bytes", 0)
        step = self.repository.create_step(
            stage_id=stage_id,
            step_name=step_info.step_name,
            status=output.status.upper(),
            log_path=str(step_info.build_log_path),
            failure_type=normalized_failure_type,
            log_size_bytes=int(log_size) if isinstance(log_size, (int, float)) else 0,
            has_sidecar_logs=step_info.has_sidecar_logs,
        )

        self.repository.create_step_analysis(
            step_id=step.id,
            analysis_text=output.analysis,
            confidence=output.confidence,
            root_cause=output.root_cause,
            error_category=normalized_error_category,
        )

    def _enrich_analysis(
        self,
        initial_output: StepAnalysisOutput,
        step_name: str,
    ) -> Optional[str]:
        """Enrich analysis with web search.

        Args:
            initial_output: Initial analysis output
            step_name: Step name

        Returns:
            Enriched analysis or None
        """
        try:
            search_results = self.tools.perform_web_search(
                f"{initial_output.root_cause} {step_name}"
            )
            self.usage_tracker.record_web_search()

            enriched = self.analysis_enricher(
                initial_analysis=initial_output.analysis,
                search_results=search_results,
                step_name=step_name,
            )

            self.usage_tracker.record_llm_call(
                model="configured_model",
                input_tokens=1500,
                output_tokens=600,
                call_type="analysis_enrichment",
            )

            return str(enriched.enriched_analysis)

        except Exception as e:
            self.progress.print_warning(f"Enrichment failed: {e}")
            return None

    def _phase_2_report_generation(self) -> Path:
        """Phase 2: Generate final reports with detailed insights.

        Returns:
            Path to main report
        """
        print("\n📊 Phase 2: Generating Reports")
        self.progress.add_task(
            "report_generation",
            "Generating reports...",
        )

        statistics = self.repository.get_failure_statistics()

        root_cause_dist = self.db_server.get_root_cause_distribution(
            limit=100,
            use_semantic_clustering=self.use_semantic_clustering,
            similarity_threshold=self.similarity_threshold,
        )
        error_categories = self.db_server.get_error_category_breakdown()
        step_analysis = self.db_server.get_step_failure_analysis(limit=10)

        report_path = self.report_generator.generate_audit_report(
            statistics=statistics,
            metadata={
                "job_name": "Analyzed Jobs",
                "analysis_period": "Latest runs",
                "log_path": str(self.log_path),
                "database_path": str(self.database_path),
            },
            root_cause_distribution=root_cause_dist,
            error_category_breakdown=error_categories,
            step_failure_analysis=step_analysis,
        )

        usage_stats = self.usage_tracker.finalize()
        usage_stats.web_searches = self.tools.get_usage_stats()["web_searches"]

        usage_report = self.usage_tracker.generate_usage_report()
        usage_report_path = self.output_path / "usage_report.md"
        with open(usage_report_path, "w") as f:
            f.write(usage_report)

        self.progress.complete_task("report_generation", "Reports generated")
        return report_path

    def _create_output_tarball(self, report_path: Path) -> Path:
        """Create tarball of outputs.

        Args:
            report_path: Path to main report

        Returns:
            Path to tarball
        """
        import tarfile

        tarball_path = self.output_path / "prow_audit_results.tar.gz"

        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(self.database_path, arcname="audit_database.db")
            tar.add(report_path, arcname="audit_report.md")
            usage_report_path = self.output_path / "usage_report.md"
            if usage_report_path.exists():
                tar.add(usage_report_path, arcname="usage_report.md")

        return tarball_path
