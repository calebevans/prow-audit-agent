"""Main entry point for Prow Audit Agent CLI."""

from pathlib import Path
from typing import Optional

import click

from .agent.audit_agent import AuditAgent
from .utils.config import configure_dspy_lm, get_llm_config


@click.command()  # type: ignore
@click.option(
    "--log-path",
    required=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to the directory containing Prow logs (not required with --report-only)",
)
@click.option(
    "--output-path",
    default="./results",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Path to store analysis results (default: ./results)",
)
@click.option(
    "--stage",
    type=str,
    default=None,
    help="Optional: Specific stage name to analyze (analyzes all stages if not provided)",
)
@click.option(
    "--database",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to SQLite database file (default: output-path/prow_audit.db)",
)
@click.option(
    "--report-only",
    is_flag=True,
    default=False,
    help="Only regenerate reports from existing database (skip log analysis)",
)
@click.option(
    "--semantic-clustering/--no-semantic-clustering",
    default=True,
    help=(
        "Use semantic similarity to group related failures "
        "(enabled by default, requires sentence-transformers)"
    ),
)
@click.option(
    "--similarity-threshold",
    type=float,
    default=0.65,
    help="Cosine similarity threshold for clustering (0.0-1.0, default: 0.65)",
)
@click.version_option(version="1.0.0", prog_name="Prow Audit Agent")
def cli(
    log_path: Path,
    output_path: Path,
    stage: Optional[str],
    database: Optional[Path],
    report_only: bool,
    semantic_clustering: bool,
    similarity_threshold: float,
) -> None:
    """Prow Audit Agent - AI-powered CI/CD failure analysis tool.

    Analyzes Prow job logs to identify systemic issues and provide
    actionable recommendations for improving pipeline reliability.

    Examples:

        # Analyze all stages in a job
        prow-audit --log-path /path/to/logs --output-path ./results

        # Analyze specific stage
        prow-audit --log-path /path/to/logs --stage appstudio-e2e-tests

        # Custom database location
        prow-audit --log-path /path/to/logs --database ./custom.db
    """
    # Validate arguments
    if not report_only and log_path is None:
        click.echo("Error: --log-path is required unless using --report-only", err=True)
        return

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Set database path
    if database is None:
        database = output_path / "prow_audit.db"

    # Display configuration
    click.echo("Prow Audit Agent v1.0.0")
    click.echo("=" * 60)
    if not report_only:
        click.echo(f"Log Path: {log_path}")
    click.echo(f"Output Path: {output_path}")
    click.echo(f"Database: {database}")
    if stage and not report_only:
        click.echo(f"Filter Stage: {stage}")
    if report_only:
        click.echo("Mode: Report Generation Only")
    if semantic_clustering:
        click.echo(f"Semantic Clustering: Enabled (threshold={similarity_threshold})")
    else:
        click.echo("Semantic Clustering: Disabled")
    click.echo("=" * 60)
    click.echo()

    # For report-only mode, verify database exists
    if report_only:
        if not database.exists():
            click.echo(f"Error: Database not found at {database}", err=True)
            click.echo(
                "Please provide a valid database path using --database", err=True
            )
            return
        click.echo(f"Using existing database: {database}")
        click.echo("Skipping log analysis, generating reports only...")
        click.echo()

    # Configure LLM
    try:
        llm_config = get_llm_config()
        click.echo(f"LLM Provider: {llm_config.provider}")
        click.echo(f"Model: {llm_config.model}")
        click.echo()

        configure_dspy_lm(llm_config)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo()
        click.echo("Please set the following environment variables:")
        click.echo("  - LLM_PROVIDER (e.g., openai, anthropic, ollama)")
        click.echo("  - LLM_API_KEY (your API key)")
        click.echo("  - LLM_MODEL (optional, e.g., gpt-4, claude-3-5-sonnet)")
        return

    # Run audit or regenerate reports
    try:
        # For report-only mode, log_path can be a dummy path
        actual_log_path = log_path if log_path else output_path

        agent = AuditAgent(
            log_path=actual_log_path,
            output_path=output_path,
            database_path=database,
            filter_stage=stage,
            use_semantic_clustering=semantic_clustering,
            similarity_threshold=similarity_threshold,
        )

        if report_only:
            tarball_path = agent.regenerate_reports()
        else:
            tarball_path = agent.run_audit()

        click.echo()
        click.echo("=" * 60)
        click.echo("Audit Complete!")
        click.echo("=" * 60)
        click.echo(f"Results tarball: {tarball_path}")
        click.echo(f"Database: {database}")
        click.echo()
        click.echo("To query the database interactively, you can:")
        click.echo("1. Extract the tarball")
        click.echo("2. Use the MCP server with Claude Desktop or other MCP clients")
        click.echo()

    except Exception as e:
        click.echo(f"Error during audit: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()


if __name__ == "__main__":
    cli()
