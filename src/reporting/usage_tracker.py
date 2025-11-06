"""LLM usage tracking for cost and performance monitoring."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class LLMCallRecord:
    """Record of a single LLM call."""

    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    call_type: str
    success: bool
    error: Optional[str] = None


@dataclass
class UsageStatistics:
    """Aggregated usage statistics."""

    total_llm_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    web_searches: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    calls_by_type: dict[str, int] = field(default_factory=dict)

    def add_call(self, record: LLMCallRecord) -> None:
        """Add a call record to statistics.

        Args:
            record: Call record to add
        """
        self.total_llm_calls += 1
        if record.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        self.total_input_tokens += record.input_tokens
        self.total_output_tokens += record.output_tokens
        self.total_tokens += record.input_tokens + record.output_tokens

        if record.call_type not in self.calls_by_type:
            self.calls_by_type[record.call_type] = 0
        self.calls_by_type[record.call_type] += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting.

        Returns:
            Dictionary representation
        """
        duration_seconds = 0.0
        if self.start_time and self.end_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()

        return {
            "total_llm_calls": self.total_llm_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": (
                self.successful_calls / self.total_llm_calls
                if self.total_llm_calls > 0
                else 0
            ),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "web_searches": self.web_searches,
            "duration_seconds": duration_seconds,
            "calls_by_type": self.calls_by_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class UsageTracker:
    """Tracks LLM and tool usage throughout the audit."""

    def __init__(self) -> None:
        """Initialize the usage tracker."""
        self.statistics = UsageStatistics()
        self.call_history: list[LLMCallRecord] = []
        self.statistics.start_time = datetime.utcnow()

    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        call_type: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record an LLM call.

        Args:
            model: Model used
            input_tokens: Input token count
            output_tokens: Output token count
            call_type: Type of call
            success: Whether the call succeeded
            error: Error message if failed
        """
        record = LLMCallRecord(
            timestamp=datetime.utcnow(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            call_type=call_type,
            success=success,
            error=error,
        )

        self.call_history.append(record)
        self.statistics.add_call(record)

    def record_web_search(self) -> None:
        """Record a web search."""
        self.statistics.web_searches += 1

    def finalize(self) -> UsageStatistics:
        """Finalize tracking and return statistics.

        Returns:
            Final usage statistics
        """
        self.statistics.end_time = datetime.utcnow()
        return self.statistics

    def get_statistics(self) -> UsageStatistics:
        """Get current statistics.

        Returns:
            Current usage statistics
        """
        return self.statistics

    def generate_usage_report(self) -> str:
        """Generate a formatted usage report.

        Returns:
            Formatted report string
        """
        stats = self.statistics.to_dict()

        report_lines = [
            "# LLM Usage Report",
            "",
            "## Overall Statistics",
            f"- Total LLM Calls: {stats['total_llm_calls']}",
            f"- Successful Calls: {stats['successful_calls']}",
            f"- Failed Calls: {stats['failed_calls']}",
            f"- Success Rate: {stats['success_rate']:.2%}",
            "",
            "## Token Usage",
            f"- Input Tokens: {stats['total_input_tokens']:,}",
            f"- Output Tokens: {stats['total_output_tokens']:,}",
            f"- Total Tokens: {stats['total_tokens']:,}",
            "",
            "## Tool Usage",
            f"- Web Searches: {stats['web_searches']}",
            "",
            "## Calls by Type",
        ]

        for call_type, count in sorted(
            stats["calls_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            report_lines.append(f"- {call_type}: {count}")

        report_lines.extend(
            [
                "",
                f"Duration: {stats['duration_seconds']:.1f} seconds",
            ]
        )

        return "\n".join(report_lines)
