"""Database migration utilities for normalizing taxonomy values.

This module provides functions to migrate existing database entries to use
standardized taxonomy values for error_category, failure_type, and severity.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .models import Step, StepAnalysis
from .taxonomy import normalize_error_category, normalize_failure_type


def migrate_database(database_url: str, dry_run: bool = False) -> dict[str, int]:
    """Migrate database to use standardized taxonomy values.

    Args:
        database_url: SQLAlchemy database URL
        dry_run: If True, only report what would be changed without making changes

    Returns:
        Dictionary with counts of updated records per table
    """
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    stats = {
        "step_analysis_updated": 0,
        "steps_updated": 0,
    }

    try:
        # Migrate step_analysis error_category
        print("Migrating step_analysis.error_category...")
        analyses = session.query(StepAnalysis).all()
        for analysis in analyses:
            if analysis.error_category:
                normalized = normalize_error_category(analysis.error_category)
                if normalized != analysis.error_category:
                    print(f"  {analysis.error_category} -> {normalized}")
                    if not dry_run:
                        analysis.error_category = normalized
                    stats["step_analysis_updated"] += 1

        # Migrate steps failure_type
        print("\nMigrating steps.failure_type...")
        steps = session.query(Step).all()
        for step in steps:
            if step.failure_type:
                normalized = normalize_failure_type(step.failure_type)
                if normalized != step.failure_type:
                    print(f"  {step.failure_type} -> {normalized}")
                    if not dry_run:
                        step.failure_type = normalized
                    stats["steps_updated"] += 1

        if not dry_run:
            session.commit()
            print("\n✓ Migration completed successfully")
        else:
            print("\n✓ Dry run completed (no changes made)")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        session.close()

    return stats


def get_category_statistics(database_url: str) -> dict[str, dict[str, int]]:
    """Get statistics on current category usage.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        Dictionary with category counts per table
    """
    engine = create_engine(database_url, echo=False)

    stats = {}

    with engine.connect() as conn:
        # error_category stats
        result = conn.execute(
            text(
                "SELECT error_category, COUNT(*) as count "
                "FROM step_analysis "
                "WHERE error_category IS NOT NULL "
                "GROUP BY error_category "
                "ORDER BY count DESC"
            )
        )
        stats["error_category"] = {row[0]: row[1] for row in result}

        # failure_type stats
        result = conn.execute(
            text(
                "SELECT failure_type, COUNT(*) as count "
                "FROM steps "
                "WHERE failure_type IS NOT NULL "
                "GROUP BY failure_type "
                "ORDER BY count DESC"
            )
        )
        stats["failure_type"] = {row[0]: row[1] for row in result}

    return stats


def print_category_statistics(stats: dict[str, dict[str, int]]) -> None:
    """Print category statistics in a readable format.

    Args:
        stats: Statistics dictionary from get_category_statistics
    """
    print("\n" + "=" * 60)
    print("Current Category Usage Statistics")
    print("=" * 60)

    for category_name, counts in stats.items():
        print(f"\n{category_name.upper()}:")
        if not counts:
            print("  (no data)")
        else:
            for value, count in counts.items():
                print(f"  {value:40s} : {count:4d}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    """Command-line interface for database migration."""
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Migrate database to use standardized taxonomy values"
    )
    parser.add_argument(
        "--database",
        type=str,
        required=True,
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics without migrating",
    )

    args = parser.parse_args()

    # Verify database exists
    db_path = Path(args.database)
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    database_url = f"sqlite:///{db_path}"

    # Show current statistics
    print("Analyzing current database...")
    stats = get_category_statistics(database_url)
    print_category_statistics(stats)

    if args.stats_only:
        sys.exit(0)

    # Run migration
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No changes will be made")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("Starting migration...")
        print("=" * 60 + "\n")

        response = input("Proceed with migration? [y/N]: ")
        if response.lower() != "y":
            print("Migration cancelled")
            sys.exit(0)

    migration_stats = migrate_database(database_url, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    for table, count in migration_stats.items():
        print(f"  {table:40s} : {count:4d} records updated")

    if not args.dry_run:
        print("\nVerifying changes...")
        new_stats = get_category_statistics(database_url)
        print_category_statistics(new_stats)
