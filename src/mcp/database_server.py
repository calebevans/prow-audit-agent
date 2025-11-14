"""MCP server for database analytics."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from sqlalchemy import case, func, select

from ..database.models import Run, Stage, Step, StepAnalysis
from ..database.repository import AuditRepository


class DatabaseAnalyticsServer:
    """MCP server for database analytics operations."""

    def __init__(self, database_url: str) -> None:
        """Initialize the MCP server.

        Args:
            database_url: SQLite database URL
        """
        self.repository = AuditRepository(database_url)

    def find_similar_failures(
        self,
        error_category: Optional[str] = None,
        failure_type: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Find steps with similar failure characteristics.

        Args:
            error_category: Optional error category filter
            failure_type: Optional failure type filter
            limit: Maximum number of results

        Returns:
            Dictionary with similar failures
        """
        with self.repository.get_session() as session:
            stmt = select(StepAnalysis).join(Step)

            if error_category:
                stmt = stmt.where(StepAnalysis.error_category == error_category)
            if failure_type:
                stmt = stmt.where(Step.failure_type == failure_type)

            stmt = stmt.limit(limit)
            analyses = session.execute(stmt).scalars().all()

            return {
                "count": len(analyses),
                "failures": [
                    {
                        "step_id": a.step_id,
                        "error_category": a.error_category,
                        "root_cause": a.root_cause,
                        "confidence": a.confidence,
                    }
                    for a in analyses
                ],
            }

    def analyze_trends(self) -> dict[str, Any]:
        """Analyze temporal trends in failure rates.

        Returns:
            Dictionary with trend data
        """
        with self.repository.get_session() as session:
            runs_by_date = session.execute(
                select(
                    func.date(Run.timestamp).label("date"),
                    func.count(Run.id).label("total"),
                    func.sum(case((Run.passed.is_(False), 1), else_=0)).label("failed"),
                )
                .group_by(func.date(Run.timestamp))
                .order_by(func.date(Run.timestamp))
            ).all()

            return {
                "trends": [
                    {
                        "date": str(row.date),
                        "total_runs": row.total,
                        "failed_runs": row.failed or 0,
                        "failure_rate": (
                            (row.failed or 0) / row.total if row.total > 0 else 0
                        ),
                    }
                    for row in runs_by_date
                ],
            }

    def get_stage_statistics(self) -> dict[str, Any]:
        """Get success/failure rates per stage.

        Returns:
            Dictionary with stage statistics
        """
        with self.repository.get_session() as session:
            stats = session.execute(
                select(
                    Stage.stage_name,
                    func.count(Stage.id).label("total"),
                    func.sum(case((Stage.passed.is_(False), 1), else_=0)).label(
                        "failed"
                    ),
                )
                .group_by(Stage.stage_name)
                .order_by(func.count(Stage.id).desc())
            ).all()

            return {
                "stages": [
                    {
                        "stage_name": row.stage_name,
                        "total": row.total,
                        "failed": row.failed or 0,
                        "failure_rate": (
                            (row.failed or 0) / row.total if row.total > 0 else 0
                        ),
                    }
                    for row in stats
                ],
            }

    def correlate_failures(self, stage_name: str) -> dict[str, Any]:
        """Find co-occurring failures across steps in a stage.

        Args:
            stage_name: Name of the stage to analyze

        Returns:
            Dictionary with correlation data
        """
        with self.repository.get_session() as session:
            stmt = (
                select(Step, StepAnalysis)
                .join(Stage)
                .outerjoin(StepAnalysis)
                .where(Stage.stage_name == stage_name)
                .where(Step.status == "FAILURE")
            )
            results = session.execute(stmt).all()

            step_failures = []
            for step, analysis in results:
                step_failures.append(
                    {
                        "step_name": step.step_name,
                        "failure_type": step.failure_type,
                        "error_category": analysis.error_category if analysis else None,
                        "root_cause": analysis.root_cause if analysis else None,
                    }
                )

            return {
                "stage_name": stage_name,
                "total_failures": len(step_failures),
                "failures": step_failures,
            }

    def get_run_details(self, run_id: int) -> dict[str, Any]:
        """Get detailed information about a specific run.

        Args:
            run_id: Run ID

        Returns:
            Dictionary with run details
        """
        run = self.repository.get_run_by_id(run_id)
        if not run:
            return {"error": "Run not found"}

        stages = self.repository.get_stages_by_run(run_id)

        return {
            "run": {
                "id": run.id,
                "pr_number": run.pr_number,
                "job_name": run.job_name,
                "build_number": run.build_number,
                "status": run.overall_status,
                "passed": run.passed,
                "timestamp": run.timestamp.isoformat(),
            },
            "stages": [
                {
                    "id": stage.id,
                    "name": stage.stage_name,
                    "status": stage.status,
                    "passed": stage.passed,
                }
                for stage in stages
            ],
        }

    def get_root_cause_distribution(
        self,
        limit: int = 15,
        use_semantic_clustering: bool = False,
        similarity_threshold: float = 0.75,
    ) -> dict[str, Any]:
        """Get distribution of root causes across all failures.

        Args:
            limit: Maximum number of root causes to return
            use_semantic_clustering: Whether to cluster similar root causes
            similarity_threshold: Similarity threshold for clustering

        Returns:
            Dictionary with root cause distribution
        """
        with self.repository.get_session() as session:
            stmt = (
                select(
                    StepAnalysis.root_cause,
                    func.count(StepAnalysis.id).label("count"),
                )
                .where(StepAnalysis.root_cause.isnot(None))
                .group_by(StepAnalysis.root_cause)
                .order_by(func.count(StepAnalysis.id).desc())
                .limit(limit)
            )
            results = session.execute(stmt).all()

            causes = [
                {
                    "root_cause": row.root_cause,
                    "count": row.count,
                }
                for row in results
            ]

            if use_semantic_clustering and len(causes) > 1:
                try:
                    from ..utils.semantic_clustering import cluster_root_causes

                    print(
                        f"\n   Using semantic clustering (threshold={similarity_threshold})..."
                    )
                    clusters = cluster_root_causes(
                        causes,
                        similarity_threshold=similarity_threshold,
                    )

                    clustered_causes = []
                    for cluster in clusters[:limit]:
                        clustered_causes.append(
                            {
                                "root_cause": cluster.representative_text,
                                "count": cluster.total_count,
                                "cluster_size": len(cluster.items),
                                "avg_similarity": cluster.avg_similarity,
                                "variants": [
                                    item["root_cause"] for item in cluster.items[:5]
                                ],
                            }
                        )

                    print(
                        f"   Clustered {len(causes)} causes into {len(clusters)} semantic groups"
                    )

                    return {
                        "total_unique_causes": len(results),
                        "clustered_count": len(clusters),
                        "causes": clustered_causes,
                        "semantic_clustering_enabled": True,
                    }

                except ImportError as e:
                    print(f"   Warning: Semantic clustering unavailable: {e}")
                    print("   Falling back to exact matching...")

            return {
                "total_unique_causes": len(results),
                "causes": causes,
                "semantic_clustering_enabled": False,
            }

    def get_error_category_breakdown(self) -> dict[str, Any]:
        """Get breakdown of failures by error category."""
        with self.repository.get_session() as session:
            stmt = (
                select(
                    StepAnalysis.error_category,
                    func.count(StepAnalysis.id).label("count"),
                )
                .where(StepAnalysis.error_category.isnot(None))
                .group_by(StepAnalysis.error_category)
                .order_by(func.count(StepAnalysis.id).desc())
            )
            results = session.execute(stmt).all()

            total = sum(row.count for row in results)

            return {
                "total_analyzed": total,
                "categories": [
                    {
                        "category": row.error_category,
                        "count": row.count,
                        "percentage": (row.count / total * 100) if total > 0 else 0,
                    }
                    for row in results
                ],
            }

    def get_step_failure_analysis(self, limit: int = 15) -> dict[str, Any]:
        """Get detailed analysis of most frequently failing steps.

        Args:
            limit: Maximum number of steps to analyze

        Returns:
            Dictionary with step failure details
        """
        with self.repository.get_session() as session:
            stmt = (
                select(
                    Step.step_name,
                    func.count(Step.id).label("failure_count"),
                )
                .where(Step.status == "FAILURE")
                .group_by(Step.step_name)
                .order_by(func.count(Step.id).desc())
                .limit(limit)
            )
            step_counts = session.execute(stmt).all()

            step_details = []
            for step_row in step_counts:
                step_name = step_row.step_name
                failure_count = step_row.failure_count

                cause_stmt = (
                    select(
                        StepAnalysis.root_cause,
                        StepAnalysis.error_category,
                        func.count(StepAnalysis.id).label("count"),
                    )
                    .join(Step)
                    .where(Step.step_name == step_name)
                    .where(StepAnalysis.root_cause.isnot(None))
                    .group_by(StepAnalysis.root_cause, StepAnalysis.error_category)
                    .order_by(func.count(StepAnalysis.id).desc())
                    .limit(5)
                )
                causes = session.execute(cause_stmt).all()

                step_details.append(
                    {
                        "step_name": step_name,
                        "total_failures": failure_count,
                        "top_root_causes": [
                            {
                                "root_cause": c.root_cause,
                                "error_category": c.error_category,
                                "count": c.count,
                            }
                            for c in causes
                        ],
                    }
                )

            return {
                "total_steps_analyzed": len(step_details),
                "steps": step_details,
            }

    def export_data(self, output_path: Path, format: str = "json") -> dict[str, str]:
        """Export filtered data in various formats.

        Args:
            output_path: Path to export file
            format: Export format (json, csv)

        Returns:
            Dictionary with export status
        """
        if format == "json":
            stats = self.repository.get_failure_statistics()

            data = {
                "statistics": stats,
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)

            return {"status": "success", "path": str(output_path)}

        return {"status": "error", "message": f"Unsupported format: {format}"}


def create_mcp_server_config(database_path: Path) -> dict[str, Any]:
    """Create MCP server configuration for Claude Desktop.

    Args:
        database_path: Path to SQLite database

    Returns:
        MCP server configuration dictionary
    """
    return {
        "mcpServers": {
            "prow-audit-db": {
                "command": "python",
                "args": [
                    "-m",
                    "src.mcp.database_server",
                    "--database",
                    str(database_path.absolute()),
                ],
                "env": {},
            }
        }
    }


async def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Prow Audit Database MCP Server")
    parser.add_argument("--database", required=True, help="Path to SQLite database")
    args = parser.parse_args()

    # Initialize the analytics server
    analytics = DatabaseAnalyticsServer(f"sqlite:///{args.database}")
    
    # Create MCP server
    server = Server("prow-audit-db")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="get_root_cause_distribution",
                description="Get distribution of root causes with optional semantic clustering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 15},
                        "use_semantic_clustering": {"type": "boolean", "default": False},
                        "similarity_threshold": {"type": "number", "default": 0.75},
                    },
                },
            ),
            Tool(
                name="get_error_category_breakdown",
                description="Get failure distribution by category",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_step_failure_analysis",
                description="Find which steps fail most frequently",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 15},
                    },
                },
            ),
            Tool(
                name="get_stage_statistics",
                description="Per-stage success/failure rates",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_run_details",
                description="Detailed information about specific runs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "integer"},
                    },
                    "required": ["run_id"],
                },
            ),
            Tool(
                name="find_similar_failures",
                description="Find steps with similar characteristics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "error_category": {"type": "string"},
                        "failure_type": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            ),
            Tool(
                name="analyze_trends",
                description="Temporal analysis of failure rates",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="correlate_failures",
                description="Find co-occurring failures",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stage_name": {"type": "string"},
                    },
                    "required": ["stage_name"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Call a tool."""
        try:
            if name == "get_root_cause_distribution":
                result = analytics.get_root_cause_distribution(**arguments)
            elif name == "get_error_category_breakdown":
                result = analytics.get_error_category_breakdown()
            elif name == "get_step_failure_analysis":
                result = analytics.get_step_failure_analysis(**arguments)
            elif name == "get_stage_statistics":
                result = analytics.get_stage_statistics()
            elif name == "get_run_details":
                result = analytics.get_run_details(**arguments)
            elif name == "find_similar_failures":
                result = analytics.find_similar_failures(**arguments)
            elif name == "analyze_trends":
                result = analytics.analyze_trends()
            elif name == "correlate_failures":
                result = analytics.correlate_failures(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Run the server
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
