"""Streaming log file parser for efficient memory usage."""

import random
from pathlib import Path
from typing import Any


class LogStreamParser:
    """Streaming parser for log files to manage memory efficiently."""

    def get_log_summary(
        self,
        log_path: Path,
        head_lines: int = 50,
        tail_lines: int = 100,
    ) -> tuple[list[str], list[str], int]:
        """Get summary of log file with head and tail lines.

        Args:
            log_path: Path to log file
            head_lines: Number of lines from beginning
            tail_lines: Number of lines from end

        Returns:
            Tuple of (head_lines, tail_lines, total_line_count)
        """
        if not log_path.exists():
            return ([], [], 0)

        head: list[str] = []
        tail: list[str] = []
        total_lines = 0

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(head_lines):
                line = f.readline()
                if not line:
                    break
                head.append(line.rstrip("\n\r"))
                total_lines += 1

            for line in f:
                total_lines += 1
                tail.append(line.rstrip("\n\r"))
                if len(tail) > tail_lines:
                    tail.pop(0)

        return (head, tail, total_lines)

    def extract_errors(self, log_path: Path, max_errors: int = 50) -> list[str]:
        """Extract error lines from log file.

        Args:
            log_path: Path to log file
            max_errors: Maximum number of errors to extract

        Returns:
            List of error lines
        """
        error_patterns = [
            "error:",
            "error ",
            "exception:",
            "exception ",
            "failed:",
            "failed ",
            "failure:",
            "failure ",
            "fatal:",
            "fatal ",
            "panic:",
            "panic ",
            "traceback",
        ]

        if not log_path.exists():
            return []

        errors: list[str] = []

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if len(errors) >= max_errors:
                    break

                line = line.rstrip("\n\r")
                line_lower = line.lower()

                for pattern in error_patterns:
                    if pattern in line_lower:
                        errors.append(line)
                        break

        return errors

    def get_file_size(self, log_path: Path) -> int:
        """Get log file size in bytes.

        Args:
            log_path: Path to log file

        Returns:
            File size in bytes
        """
        if not log_path.exists():
            return 0
        return log_path.stat().st_size


def create_log_context(
    log_path: Path,
    max_head_lines: int = 50,
    max_tail_lines: int = 100,
    max_sample_lines: int = 100,
    sample_threshold: int = 500,
    include_errors: bool = True,
) -> dict[str, Any]:
    """Create a context dictionary for LLM analysis with smart sampling.

    Args:
        log_path: Path to log file
        max_head_lines: Number of lines from beginning
        max_tail_lines: Number of lines from end
        max_sample_lines: Number of random samples from middle for large logs
        sample_threshold: Log must be > this many lines to trigger sampling
        include_errors: Whether to include extracted errors

    Returns:
        Dictionary with log context information
    """
    parser = LogStreamParser()

    head, tail, total_lines = parser.get_log_summary(
        log_path,
        head_lines=max_head_lines,
        tail_lines=max_tail_lines,
    )

    middle_samples: list[str] = []
    has_samples = False

    if total_lines > sample_threshold:
        has_samples = True
        middle_start = max_head_lines
        middle_end = total_lines - max_tail_lines
        middle_region_size = middle_end - middle_start

        if middle_region_size > 0:
            sample_count = min(max_sample_lines, middle_region_size)
            sample_line_numbers = sorted(
                random.sample(range(middle_start, middle_end), sample_count)
            )

            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                current_line = 0
                sample_idx = 0

                for line in f:
                    if sample_idx >= len(sample_line_numbers):
                        break

                    if current_line == sample_line_numbers[sample_idx]:
                        middle_samples.append(line.rstrip("\n\r"))
                        sample_idx += 1

                    current_line += 1

    context: dict[str, Any] = {
        "log_path": str(log_path),
        "total_lines": total_lines,
        "file_size_bytes": parser.get_file_size(log_path),
        "head_lines": head,
        "tail_lines": tail,
        "middle_samples": middle_samples,
        "has_samples": has_samples,
        "is_truncated": total_lines > (max_head_lines + max_tail_lines),
    }

    if include_errors:
        errors = parser.extract_errors(log_path, max_errors=30)
        context["extracted_errors"] = errors
        context["error_count"] = len(errors)

    return context
