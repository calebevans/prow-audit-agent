"""DSPy signatures for Prow audit analysis tasks."""

from typing import Optional

import dspy
from pydantic import BaseModel, Field


class StepAnalysisOutput(BaseModel):  # type: ignore
    """Output model for step log analysis."""

    status: str = Field(description="Status: SUCCESS, FAILURE, ERROR, or UNKNOWN")
    failure_type: Optional[str] = Field(
        default=None,
        description=(
            "Type of failure. Must be one of: "
            "build_failure, compilation_error, dependency_error, "
            "unit_test_failure, integration_test_failure, e2e_test_failure, flaky_test, "
            "infrastructure_failure, network_failure, resource_exhaustion, timeout, "
            "deployment_failure, container_failure, image_pull_failure, "
            "configuration_error, authentication_failure, permission_denied, "
            "application_crash, application_error, unknown, other"
        ),
    )
    root_cause: Optional[str] = Field(
        default=None,
        description=(
            "Root cause in 10 words or less. Be concise, no explanatory details. "
            "Example: 'DNS resolution failure for the API server hostname' NOT "
            "'DNS resolution failure for the API server hostname, causing "
            "inability to connect to the cluster'"
        ),
    )
    analysis: str = Field(description="Detailed analysis of what happened in this step")
    error_category: Optional[str] = Field(
        default=None,
        description=(
            "Technical category of the error. Must be one of: "
            "infrastructure, network, resource, timeout, "
            "compilation, syntax, dependency, "
            "runtime, crash, assertion, "
            "test_failure, flaky_test, "
            "configuration, permissions, authentication, "
            "deployment, container, "
            "database, data_validation, "
            "unknown, other"
        ),
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score 0.0-1.0 in this analysis",
    )
    needs_search: bool = Field(
        default=False,
        description="Whether web search would help understand this failure",
    )


class AnalyzeStepLog(dspy.Signature):  # type: ignore
    """Analyze a Prow step log to identify failures and their causes.

    Examine the provided log excerpt: head (start), tail (end), and random samples from
    middle (for large logs). Focus on identifying the root cause of failures with high confidence.
    The log_head may include random samples from the middle section for better coverage.

    IMPORTANT: Keep root_cause CONCISE (max 10-12 words). State the problem, not consequences.
    Good: "DNS resolution failure for the API server"
    Bad: "DNS resolution failure for the API server causing inability to connect to the cluster"
    """

    step_name: str = dspy.InputField(description="Name of the step being analyzed")
    stage_name: str = dspy.InputField(description="Name of the parent stage")
    log_head: str = dspy.InputField(
        description="First lines + random middle samples (if large log)"
    )
    log_tail: str = dspy.InputField(description="Last lines of the log file")
    extracted_errors: str = dspy.InputField(
        description="Extracted error lines from the log"
    )
    total_lines: int = dspy.InputField(description="Total number of lines in the log")

    analysis_output: StepAnalysisOutput = dspy.OutputField(
        description="Structured analysis of the step"
    )


class SearchDecision(dspy.Signature):  # type: ignore
    """Decide whether to perform web search for additional context.

    Given an error or failure, determine if web search would provide
    valuable additional context for analysis.
    """

    error_context: str = dspy.InputField(description="Error message or failure context")
    initial_analysis: str = dspy.InputField(
        description="Initial analysis of the failure"
    )
    step_name: str = dspy.InputField(description="Name of the step")

    should_search: bool = dspy.OutputField(
        description="Whether web search would be helpful"
    )
    search_query: str = dspy.OutputField(
        description="Optimized search query if should_search is True"
    )
    reasoning: str = dspy.OutputField(description="Brief reasoning for the decision")


class EnrichAnalysis(dspy.Signature):  # type: ignore
    """Enrich initial analysis with web search results.

    Combine the initial analysis with information from web search
    to provide a more comprehensive understanding.
    """

    initial_analysis: str = dspy.InputField(
        description="Initial analysis of the failure"
    )
    search_results: str = dspy.InputField(
        description="Relevant information from web search"
    )
    step_name: str = dspy.InputField(description="Name of the step")

    enriched_analysis: str = dspy.OutputField(
        description="Enhanced analysis incorporating search results"
    )
