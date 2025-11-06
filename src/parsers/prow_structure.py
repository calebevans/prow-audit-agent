"""Parser for Prow directory structure and metadata files."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class ProwFinishedMetadata:
    """Metadata from a finished.json file."""

    timestamp: datetime
    passed: bool
    result: str
    revision: Optional[str] = None
    metadata: Optional[dict[str, str]] = None


@dataclass
class ProwStepInfo:
    """Information about a Prow step."""

    step_name: str
    stage_name: str
    build_log_path: Path
    finished_json_path: Optional[Path]
    sidecar_logs_path: Optional[Path]
    has_finished_json: bool
    has_sidecar_logs: bool
    metadata: Optional[ProwFinishedMetadata] = None


@dataclass
class ProwStageInfo:
    """Information about a Prow stage."""

    stage_name: str
    stage_path: Path
    finished_json_path: Optional[Path]
    steps: list[ProwStepInfo]
    metadata: Optional[ProwFinishedMetadata] = None


@dataclass
class ProwRunInfo:
    """Information about a complete Prow run."""

    pr_number: str
    job_name: str
    build_number: str
    run_path: Path
    stages: list[ProwStageInfo]
    finished_json_path: Optional[Path] = None
    metadata: Optional[ProwFinishedMetadata] = None


class ProwStructureParser:
    """Parser for Prow log directory structure."""

    def __init__(self, log_root: Path) -> None:
        """Initialize the parser.

        Args:
            log_root: Root directory containing Prow logs
        """
        self.log_root = Path(log_root)
        if not self.log_root.exists():
            raise ValueError(f"Log root does not exist: {self.log_root}")

    def parse_finished_json(
        self, finished_json_path: Path
    ) -> Optional[ProwFinishedMetadata]:
        """Parse a finished.json file.

        Args:
            finished_json_path: Path to finished.json

        Returns:
            Metadata object or None if parsing fails
        """
        if not finished_json_path.exists():
            return None

        try:
            with open(finished_json_path, "r") as f:
                data = json.load(f)

            timestamp = datetime.fromtimestamp(data.get("timestamp", 0))
            passed = data.get("passed", False)
            result = data.get("result", "UNKNOWN")
            revision = data.get("revision")
            metadata_dict = data.get("metadata")

            return ProwFinishedMetadata(
                timestamp=timestamp,
                passed=passed,
                result=result,
                revision=revision,
                metadata=metadata_dict,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Failed to parse {finished_json_path}: {e}")
            return None

    def find_steps_in_stage(
        self, stage_path: Path, stage_name: str
    ) -> list[ProwStepInfo]:
        """Find all steps within a stage directory.

        Args:
            stage_path: Path to stage directory
            stage_name: Name of the stage

        Returns:
            List of step information objects
        """
        steps: list[ProwStepInfo] = []

        if not stage_path.exists() or not stage_path.is_dir():
            return steps

        # Look for step directories (subdirectories that contain build-log.txt)
        for item in stage_path.iterdir():
            if not item.is_dir():
                continue

            build_log_path = item / "build-log.txt"
            if not build_log_path.exists():
                continue

            step_name = item.name
            finished_json_path = item / "finished.json"
            sidecar_logs_path = item / "sidecar-logs.json"

            # Parse step-level finished.json if it exists
            step_metadata = None
            if finished_json_path.exists():
                step_metadata = self.parse_finished_json(finished_json_path)

            steps.append(
                ProwStepInfo(
                    step_name=step_name,
                    stage_name=stage_name,
                    build_log_path=build_log_path,
                    finished_json_path=(
                        finished_json_path if finished_json_path.exists() else None
                    ),
                    sidecar_logs_path=(
                        sidecar_logs_path if sidecar_logs_path.exists() else None
                    ),
                    has_finished_json=finished_json_path.exists(),
                    has_sidecar_logs=sidecar_logs_path.exists(),
                    metadata=step_metadata,
                )
            )

        return steps

    def find_stages_in_run(self, run_path: Path) -> list[ProwStageInfo]:
        """Find all stages within a run directory.

        Args:
            run_path: Path to run directory

        Returns:
            List of stage information objects
        """
        stages: list[ProwStageInfo] = []
        artifacts_path = run_path / "artifacts"

        if not artifacts_path.exists() or not artifacts_path.is_dir():
            return stages

        # Look for stage directories within artifacts
        for item in artifacts_path.iterdir():
            if not item.is_dir():
                continue

            stage_name = item.name
            finished_json_path = item / "finished.json"

            # Parse stage-level finished.json if it exists
            metadata = None
            if finished_json_path.exists():
                metadata = self.parse_finished_json(finished_json_path)

            # Find steps within this stage
            steps = self.find_steps_in_stage(item, stage_name)

            # Only include stages that have steps
            if steps or finished_json_path.exists():
                stages.append(
                    ProwStageInfo(
                        stage_name=stage_name,
                        stage_path=item,
                        finished_json_path=(
                            finished_json_path if finished_json_path.exists() else None
                        ),
                        steps=steps,
                        metadata=metadata,
                    )
                )

        return stages

    def parse_run(self, run_path: Path) -> Optional[ProwRunInfo]:
        """Parse a single run directory.

        Args:
            run_path: Path to run directory

        Returns:
            Run information object or None if parsing fails
        """
        if not run_path.exists() or not run_path.is_dir():
            return None

        try:
            build_number = run_path.name
            job_name = self.log_root.name
            pr_number = "unknown"
        except (AttributeError, IndexError):
            print(f"Warning: Could not extract metadata from path: {run_path}")
            return None

        stages = self.find_stages_in_run(run_path)

        finished_json_path = run_path / "finished.json"
        metadata = None
        if finished_json_path.exists():
            metadata = self.parse_finished_json(finished_json_path)

        return ProwRunInfo(
            pr_number=pr_number,
            job_name=job_name,
            build_number=build_number,
            run_path=run_path,
            stages=stages,
            finished_json_path=(
                finished_json_path if finished_json_path.exists() else None
            ),
            metadata=metadata,
        )

    def find_all_runs(
        self, filter_stage: Optional[str] = None
    ) -> Iterator[ProwRunInfo]:
        """Find all runs in the log directory.

        Args:
            filter_stage: Optional stage name to filter by

        Yields:
            Run information objects
        """
        seen_builds = set()

        for build_dir in self.log_root.iterdir():
            if not build_dir.is_dir():
                continue

            if build_dir.name.startswith(".") or build_dir.name == "latest-build.txt":
                continue

            if build_dir.name in seen_builds:
                print(f"WARNING: Duplicate build directory detected: {build_dir.name}")
                continue
            seen_builds.add(build_dir.name)

            run_info = self.parse_run(build_dir)
            if run_info is None:
                continue

            if filter_stage:
                run_info.stages = [
                    stage
                    for stage in run_info.stages
                    if stage.stage_name == filter_stage
                ]
                if not run_info.stages:
                    continue

            yield run_info

    def find_failed_runs(
        self, filter_stage: Optional[str] = None
    ) -> Iterator[ProwRunInfo]:
        """Find all failed runs by checking finished.json files.

        Args:
            filter_stage: Optional stage name to filter by

        Yields:
            Failed run information objects
        """
        for run_info in self.find_all_runs(filter_stage=filter_stage):
            has_failure = False

            if run_info.metadata and not run_info.metadata.passed:
                has_failure = True

            if not has_failure:
                for stage in run_info.stages:
                    if stage.metadata and not stage.metadata.passed:
                        has_failure = True
                        break

            if has_failure:
                yield run_info

    def count_total_runs(self, filter_stage: Optional[str] = None) -> int:
        """Count total number of runs.

        Args:
            filter_stage: Optional stage name to filter by

        Returns:
            Total count
        """
        return sum(1 for _ in self.find_all_runs(filter_stage=filter_stage))

    def count_failed_runs(self, filter_stage: Optional[str] = None) -> int:
        """Count number of failed runs.

        Args:
            filter_stage: Optional stage name to filter by

        Returns:
            Failed count
        """
        return sum(1 for _ in self.find_failed_runs(filter_stage=filter_stage))
