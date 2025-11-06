"""Report generation for audit findings."""

from datetime import datetime
from pathlib import Path
from typing import Any


class ReportGenerator:
    """Generates comprehensive audit reports in markdown format."""

    def __init__(self, output_path: Path) -> None:
        """Initialize the report generator.

        Args:
            output_path: Path to write reports
        """
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def generate_audit_report(
        self,
        statistics: dict[str, Any],
        metadata: dict[str, str],
        root_cause_distribution: dict[str, Any] | None = None,
        error_category_breakdown: dict[str, Any] | None = None,
        step_failure_analysis: dict[str, Any] | None = None,
    ) -> Path:
        """Generate the main audit report.

        Args:
            statistics: Overall statistics
            metadata: Job metadata
            root_cause_distribution: Distribution of root causes
            error_category_breakdown: Breakdown by error category
            step_failure_analysis: Analysis of failing steps

        Returns:
            Path to generated report
        """
        report_lines = [
            "# Prow CI/CD Pipeline Audit Report",
            "",
            f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Job:** {metadata.get('job_name', 'N/A')}",
            f"**Analysis Period:** {metadata.get('analysis_period', 'N/A')}",
            "",
            "---",
            "",
        ]

        report_lines.extend(self._generate_executive_summary(statistics))
        report_lines.extend(self._generate_statistics_section(statistics))

        if root_cause_distribution:
            report_lines.extend(
                self._generate_root_cause_section(root_cause_distribution)
            )

        if error_category_breakdown:
            report_lines.extend(
                self._generate_error_category_section(error_category_breakdown)
            )

        if step_failure_analysis:
            report_lines.extend(
                self._generate_step_failure_section(step_failure_analysis)
            )

        report_path = self.output_path / "audit_report.md"
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))

        return report_path

    def _generate_executive_summary(
        self,
        statistics: dict[str, Any],
    ) -> list[str]:
        """Generate executive summary section.

        Args:
            statistics: Statistics dictionary

        Returns:
            List of report lines
        """
        total_runs = statistics.get("total_runs", 0)
        failed_runs = statistics.get("failed_runs", 0)
        successful_runs = statistics.get("successful_runs", 0)
        failure_rate = (failed_runs / total_runs * 100) if total_runs > 0 else 0

        return [
            "## Executive Summary",
            "",
            f"This audit analyzed **{total_runs}** CI/CD pipeline runs, "
            f"of which **{failed_runs}** failed and **{successful_runs}** succeeded "
            f"({failure_rate:.1f}% failure rate).",
            "",
            "---",
            "",
        ]

    def _generate_statistics_section(self, statistics: dict[str, Any]) -> list[str]:
        """Generate statistics section.

        Args:
            statistics: Statistics dictionary

        Returns:
            List of report lines
        """
        total = statistics.get("total_runs", 0)
        failed = statistics.get("failed_runs", 0)
        successful = statistics.get("successful_runs", total - failed)
        failure_rate = (failed / total * 100) if total > 0 else 0

        return [
            "## Overall Statistics",
            "",
            "### Run Statistics",
            f"- Total Runs Scanned: {total}",
            f"- Failed Runs: {failed}",
            f"- Successful Runs: {successful}",
            f"- Failure Rate: {failure_rate:.1f}%",
            "",
            "### Stage Statistics",
            f"- Total Stages: {statistics.get('total_stages', 0)}",
            f"- Failed Stages: {statistics.get('failed_stages', 0)}",
            "",
            "---",
            "",
        ]

    def _generate_root_cause_section(
        self, root_cause_distribution: dict[str, Any]
    ) -> list[str]:
        """Generate root cause analysis section.

        Args:
            root_cause_distribution: Root cause distribution data

        Returns:
            List of report lines
        """
        is_clustered = root_cause_distribution.get("semantic_clustering_enabled", False)

        lines = [
            "## Top Root Causes of Failures",
            "",
        ]

        if is_clustered:
            lines.extend(
                [
                    (
                        "This section identifies the most common root causes using "
                        "**semantic clustering** to group similar failures together."
                    ),
                    "",
                    (
                        f"**Note:** {root_cause_distribution['total_unique_causes']} "
                        f"unique root cause descriptions were clustered into "
                        f"{root_cause_distribution['clustered_count']} semantic groups."
                    ),
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    (
                        "This section identifies the most common root causes "
                        "across all analyzed failures."
                    ),
                    "",
                ]
            )

        for i, cause_info in enumerate(root_cause_distribution["causes"][:15], 1):
            root_cause = cause_info["root_cause"]
            count = cause_info["count"]

            lines.extend(
                [
                    f"### {i}. {root_cause}",
                    "",
                    f"**Total Occurrences:** {count}",
                ]
            )

            # If clustered, show cluster info
            if is_clustered and "cluster_size" in cause_info:
                cluster_size = cause_info["cluster_size"]
                avg_similarity = cause_info.get("avg_similarity", 0)

                lines.append(
                    f"**Cluster Size:** {cluster_size} similar failure descriptions"
                )
                lines.append(f"**Avg. Similarity:** {avg_similarity:.2%}")

                # Show variants if available
                if "variants" in cause_info and len(cause_info["variants"]) > 1:
                    lines.append("")
                    lines.append("**Variants in this cluster:**")
                    for variant in cause_info["variants"][:5]:
                        if variant != root_cause:  # Don't repeat the main one
                            lines.append(f"- {variant}")

            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_error_category_section(
        self, error_category_breakdown: dict[str, Any]
    ) -> list[str]:
        """Generate error category breakdown section.

        Args:
            error_category_breakdown: Error category data

        Returns:
            List of report lines
        """
        lines = [
            "## Error Category Breakdown",
            "",
            f"**Total Failures Analyzed:** {error_category_breakdown['total_analyzed']}",
            "",
        ]

        for cat_info in error_category_breakdown["categories"]:
            category = cat_info["category"]
            count = cat_info["count"]
            percentage = cat_info["percentage"]

            lines.append(
                f"- **{category.upper()}**: {count} failures ({percentage:.1f}%)"
            )

        lines.extend(["", "---", ""])
        return lines

    def _generate_step_failure_section(
        self, step_failure_analysis: dict[str, Any]
    ) -> list[str]:
        """Generate step failure analysis section.

        Args:
            step_failure_analysis: Step failure data

        Returns:
            List of report lines
        """
        lines = [
            "## Most Frequently Failing Steps",
            "",
            "This section shows which steps fail most often and their common root causes.",
            "",
        ]

        for step_info in step_failure_analysis["steps"][:10]:
            step_name = step_info["step_name"]
            total_failures = step_info["total_failures"]
            top_causes = step_info["top_root_causes"]

            lines.extend(
                [
                    f"### `{step_name}`",
                    "",
                    f"**Total Failures:** {total_failures}",
                    "",
                ]
            )

            if top_causes:
                lines.append("**Top Root Causes:**")
                for cause in top_causes[:3]:
                    lines.append(f"- ({cause['count']}x) {cause['root_cause']}")
                lines.append("")

        lines.extend(["---", ""])
        return lines
