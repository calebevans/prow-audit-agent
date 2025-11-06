"""Standardized taxonomy for categorizing failures in Prow audit analysis.

This module defines enums for consistent categorization of failures, enabling
accurate queries and statistical analysis.
"""

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    """Standardized error categories for step analysis.

    These categories represent the technical nature of the failure.
    """

    # Infrastructure and environment
    INFRASTRUCTURE = "infrastructure"
    NETWORK = "network"
    RESOURCE = "resource"
    TIMEOUT = "timeout"

    # Code and compilation
    COMPILATION = "compilation"
    SYNTAX = "syntax"
    DEPENDENCY = "dependency"

    # Runtime issues
    RUNTIME = "runtime"
    CRASH = "crash"
    ASSERTION = "assertion"

    # Testing
    TEST_FAILURE = "test_failure"
    FLAKY_TEST = "flaky_test"

    # Configuration
    CONFIGURATION = "configuration"
    PERMISSIONS = "permissions"
    AUTHENTICATION = "authentication"

    # Deployment
    DEPLOYMENT = "deployment"
    CONTAINER = "container"

    # Data
    DATABASE = "database"
    DATA_VALIDATION = "data_validation"

    # Other
    UNKNOWN = "unknown"
    OTHER = "other"


class FailureType(str, Enum):
    """Standardized failure types for steps.

    These types represent the high-level category of what went wrong.
    """

    # Build failures
    BUILD_FAILURE = "build_failure"
    COMPILATION_ERROR = "compilation_error"
    DEPENDENCY_ERROR = "dependency_error"

    # Test failures
    UNIT_TEST_FAILURE = "unit_test_failure"
    INTEGRATION_TEST_FAILURE = "integration_test_failure"
    E2E_TEST_FAILURE = "e2e_test_failure"
    FLAKY_TEST = "flaky_test"

    # Infrastructure
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    NETWORK_FAILURE = "network_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TIMEOUT = "timeout"

    # Deployment
    DEPLOYMENT_FAILURE = "deployment_failure"
    CONTAINER_FAILURE = "container_failure"
    IMAGE_PULL_FAILURE = "image_pull_failure"

    # Configuration
    CONFIGURATION_ERROR = "configuration_error"
    AUTHENTICATION_FAILURE = "authentication_failure"
    PERMISSION_DENIED = "permission_denied"

    # Application
    APPLICATION_CRASH = "application_crash"
    APPLICATION_ERROR = "application_error"

    # Other
    UNKNOWN = "unknown"
    OTHER = "other"


class Severity(str, Enum):
    """Standardized severity levels for issues and patterns."""

    CRITICAL = "critical"  # Pipeline completely blocked
    HIGH = "high"  # Major impact, needs immediate attention
    MEDIUM = "medium"  # Moderate impact, should be addressed soon
    LOW = "low"  # Minor impact, can be addressed later
    INFO = "info"  # Informational only


class ComponentArea(str, Enum):
    """Standardized component areas for systemic issues.

    These represent which part of the system is affected.
    """

    BUILD = "build"
    TEST = "test"
    INFRASTRUCTURE = "infrastructure"
    DEPLOYMENT = "deployment"
    NETWORKING = "networking"
    STORAGE = "storage"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    APPLICATION = "application"
    UNKNOWN = "unknown"


# Mapping for migrating old/free-form values to standardized ones
ERROR_CATEGORY_MIGRATION_MAP = {
    # Infrastructure variations
    "Infrastructure/Resource Management": ErrorCategory.INFRASTRUCTURE,
    "infrastructure": ErrorCategory.INFRASTRUCTURE,
    "infrastructure_or_deployment": ErrorCategory.INFRASTRUCTURE,
    "infra": ErrorCategory.INFRASTRUCTURE,
    # Network variations
    "network": ErrorCategory.NETWORK,
    "networking": ErrorCategory.NETWORK,
    "dns": ErrorCategory.NETWORK,
    "connection": ErrorCategory.NETWORK,
    # Timeout variations
    "timeout": ErrorCategory.TIMEOUT,
    "time_out": ErrorCategory.TIMEOUT,
    "timed_out": ErrorCategory.TIMEOUT,
    # Test variations
    "test": ErrorCategory.TEST_FAILURE,
    "test_failure": ErrorCategory.TEST_FAILURE,
    "testing": ErrorCategory.TEST_FAILURE,
    "flaky": ErrorCategory.FLAKY_TEST,
    "flaky_test": ErrorCategory.FLAKY_TEST,
    # Build/compilation variations
    "build": ErrorCategory.COMPILATION,
    "compilation": ErrorCategory.COMPILATION,
    "compile": ErrorCategory.COMPILATION,
    "syntax": ErrorCategory.SYNTAX,
    # Runtime variations
    "runtime": ErrorCategory.RUNTIME,
    "execution": ErrorCategory.RUNTIME,
    "crash": ErrorCategory.CRASH,
    # Resource variations
    "resource": ErrorCategory.RESOURCE,
    "resource_exhaustion": ErrorCategory.RESOURCE,
    "memory": ErrorCategory.RESOURCE,
    "disk": ErrorCategory.RESOURCE,
    "cpu": ErrorCategory.RESOURCE,
    # Configuration variations
    "config": ErrorCategory.CONFIGURATION,
    "configuration": ErrorCategory.CONFIGURATION,
    "misconfiguration": ErrorCategory.CONFIGURATION,
    # Dependency variations
    "dependency": ErrorCategory.DEPENDENCY,
    "dependencies": ErrorCategory.DEPENDENCY,
    "package": ErrorCategory.DEPENDENCY,
    # Deployment variations
    "deployment": ErrorCategory.DEPLOYMENT,
    "deploy": ErrorCategory.DEPLOYMENT,
    # Container variations
    "container": ErrorCategory.CONTAINER,
    "docker": ErrorCategory.CONTAINER,
    "pod": ErrorCategory.CONTAINER,
    # Synchronization
    "synchronization": ErrorCategory.RUNTIME,
    "synchronization_failure": ErrorCategory.RUNTIME,
    "sync": ErrorCategory.RUNTIME,
    # Authentication
    "auth": ErrorCategory.AUTHENTICATION,
    "authentication": ErrorCategory.AUTHENTICATION,
    "permission": ErrorCategory.PERMISSIONS,
    "permissions": ErrorCategory.PERMISSIONS,
    # Database
    "database": ErrorCategory.DATABASE,
    "db": ErrorCategory.DATABASE,
    "sql": ErrorCategory.DATABASE,
    # Unknown
    "unknown": ErrorCategory.UNKNOWN,
    "other": ErrorCategory.OTHER,
}


FAILURE_TYPE_MIGRATION_MAP = {
    # Infrastructure variations
    "infrastructure": FailureType.INFRASTRUCTURE_FAILURE,
    "infra": FailureType.INFRASTRUCTURE_FAILURE,
    "infrastructure_failure": FailureType.INFRASTRUCTURE_FAILURE,
    # Network variations
    "network": FailureType.NETWORK_FAILURE,
    "network_failure": FailureType.NETWORK_FAILURE,
    "dns_resolution_failure": FailureType.NETWORK_FAILURE,
    "dns": FailureType.NETWORK_FAILURE,
    "connection_failure": FailureType.NETWORK_FAILURE,
    # Timeout variations
    "timeout": FailureType.TIMEOUT,
    "time_out": FailureType.TIMEOUT,
    "timed_out": FailureType.TIMEOUT,
    # Build variations
    "build": FailureType.BUILD_FAILURE,
    "build_failure": FailureType.BUILD_FAILURE,
    "compilation": FailureType.COMPILATION_ERROR,
    "compilation_error": FailureType.COMPILATION_ERROR,
    "compile_error": FailureType.COMPILATION_ERROR,
    # Test variations
    "test": FailureType.UNIT_TEST_FAILURE,
    "test_failure": FailureType.UNIT_TEST_FAILURE,
    "unit_test": FailureType.UNIT_TEST_FAILURE,
    "integration_test": FailureType.INTEGRATION_TEST_FAILURE,
    "e2e": FailureType.E2E_TEST_FAILURE,
    "e2e_test": FailureType.E2E_TEST_FAILURE,
    "flaky": FailureType.FLAKY_TEST,
    "flaky_test": FailureType.FLAKY_TEST,
    # Resource variations
    "resource": FailureType.RESOURCE_EXHAUSTION,
    "resource_exhaustion": FailureType.RESOURCE_EXHAUSTION,
    "resource_not_found": FailureType.RESOURCE_EXHAUSTION,
    "oom": FailureType.RESOURCE_EXHAUSTION,
    "out_of_memory": FailureType.RESOURCE_EXHAUSTION,
    # Deployment variations
    "deployment": FailureType.DEPLOYMENT_FAILURE,
    "deployment_failure": FailureType.DEPLOYMENT_FAILURE,
    "deploy_failure": FailureType.DEPLOYMENT_FAILURE,
    # Container variations
    "container": FailureType.CONTAINER_FAILURE,
    "container_failure": FailureType.CONTAINER_FAILURE,
    "pod_failure": FailureType.CONTAINER_FAILURE,
    "image_pull": FailureType.IMAGE_PULL_FAILURE,
    # Application variations
    "application": FailureType.APPLICATION_ERROR,
    "application_error": FailureType.APPLICATION_ERROR,
    "application_degraded": FailureType.APPLICATION_ERROR,
    "app_error": FailureType.APPLICATION_ERROR,
    "crash": FailureType.APPLICATION_CRASH,
    "application_crash": FailureType.APPLICATION_CRASH,
    # Configuration variations
    "config": FailureType.CONFIGURATION_ERROR,
    "configuration": FailureType.CONFIGURATION_ERROR,
    "configuration_error": FailureType.CONFIGURATION_ERROR,
    "misconfiguration": FailureType.CONFIGURATION_ERROR,
    # Authentication variations
    "auth": FailureType.AUTHENTICATION_FAILURE,
    "authentication": FailureType.AUTHENTICATION_FAILURE,
    "authentication_failure": FailureType.AUTHENTICATION_FAILURE,
    "permission": FailureType.PERMISSION_DENIED,
    "permission_denied": FailureType.PERMISSION_DENIED,
    # Dependency variations
    "dependency": FailureType.DEPENDENCY_ERROR,
    "dependency_error": FailureType.DEPENDENCY_ERROR,
    "dependencies": FailureType.DEPENDENCY_ERROR,
    # Unknown
    "unknown": FailureType.UNKNOWN,
    "other": FailureType.OTHER,
}


SEVERITY_MIGRATION_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "med": Severity.MEDIUM,
    "moderate": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
    "informational": Severity.INFO,
}


def normalize_error_category(value: Optional[str]) -> str:
    """Normalize an error category value to a standard enum value.

    Args:
        value: Raw error category string

    Returns:
        Standardized error category value
    """
    if not value:
        return ErrorCategory.UNKNOWN.value

    # Try direct enum match first
    normalized = value.lower().strip().replace(" ", "_").replace("-", "_")

    # Check if it's already a valid enum value
    try:
        return ErrorCategory(normalized).value
    except ValueError:
        pass

    # Try migration map
    if normalized in ERROR_CATEGORY_MIGRATION_MAP:
        return ERROR_CATEGORY_MIGRATION_MAP[normalized].value

    # Try partial matches
    for key, enum_val in ERROR_CATEGORY_MIGRATION_MAP.items():
        if key in normalized or normalized in key:
            return enum_val.value

    return ErrorCategory.UNKNOWN.value


def normalize_failure_type(value: Optional[str]) -> str:
    """Normalize a failure type value to a standard enum value.

    Args:
        value: Raw failure type string

    Returns:
        Standardized failure type value
    """
    if not value:
        return FailureType.UNKNOWN.value

    # Try direct enum match first
    normalized = value.lower().strip().replace(" ", "_").replace("-", "_")

    # Check if it's already a valid enum value
    try:
        return FailureType(normalized).value
    except ValueError:
        pass

    # Try migration map
    if normalized in FAILURE_TYPE_MIGRATION_MAP:
        return FAILURE_TYPE_MIGRATION_MAP[normalized].value

    # Try partial matches
    for key, enum_val in FAILURE_TYPE_MIGRATION_MAP.items():
        if key in normalized or normalized in key:
            return enum_val.value

    return FailureType.UNKNOWN.value


def normalize_severity(value: Optional[str]) -> str:
    """Normalize a severity value to a standard enum value.

    Args:
        value: Raw severity string

    Returns:
        Standardized severity value
    """
    if not value:
        return Severity.MEDIUM.value

    normalized = value.lower().strip()

    # Try direct enum match
    try:
        return Severity(normalized).value
    except ValueError:
        pass

    # Try migration map
    if normalized in SEVERITY_MIGRATION_MAP:
        return SEVERITY_MIGRATION_MAP[normalized].value

    return Severity.MEDIUM.value


def get_error_category_description(category: ErrorCategory) -> str:
    """Get a human-readable description of an error category.

    Args:
        category: Error category enum

    Returns:
        Description string
    """
    descriptions = {
        ErrorCategory.INFRASTRUCTURE: "Infrastructure and cloud platform issues",
        ErrorCategory.NETWORK: "Network connectivity and DNS issues",
        ErrorCategory.RESOURCE: "Resource exhaustion (CPU, memory, disk)",
        ErrorCategory.TIMEOUT: "Operations that timed out",
        ErrorCategory.COMPILATION: "Code compilation failures",
        ErrorCategory.SYNTAX: "Syntax errors in code",
        ErrorCategory.DEPENDENCY: "Dependency resolution or installation failures",
        ErrorCategory.RUNTIME: "Runtime execution errors",
        ErrorCategory.CRASH: "Application or process crashes",
        ErrorCategory.ASSERTION: "Assertion failures",
        ErrorCategory.TEST_FAILURE: "Test execution failures",
        ErrorCategory.FLAKY_TEST: "Intermittent test failures",
        ErrorCategory.CONFIGURATION: "Configuration or setup errors",
        ErrorCategory.PERMISSIONS: "Permission or access control issues",
        ErrorCategory.AUTHENTICATION: "Authentication failures",
        ErrorCategory.DEPLOYMENT: "Deployment process failures",
        ErrorCategory.CONTAINER: "Container or orchestration issues",
        ErrorCategory.DATABASE: "Database connection or query failures",
        ErrorCategory.DATA_VALIDATION: "Data validation or format issues",
        ErrorCategory.UNKNOWN: "Unknown or unclassified error",
        ErrorCategory.OTHER: "Other types of errors",
    }
    return descriptions.get(category, "No description available")


def get_failure_type_description(failure_type: FailureType) -> str:
    """Get a human-readable description of a failure type.

    Args:
        failure_type: Failure type enum

    Returns:
        Description string
    """
    descriptions = {
        FailureType.BUILD_FAILURE: "Build process failed",
        FailureType.COMPILATION_ERROR: "Code failed to compile",
        FailureType.DEPENDENCY_ERROR: "Dependency resolution failed",
        FailureType.UNIT_TEST_FAILURE: "Unit tests failed",
        FailureType.INTEGRATION_TEST_FAILURE: "Integration tests failed",
        FailureType.E2E_TEST_FAILURE: "End-to-end tests failed",
        FailureType.FLAKY_TEST: "Tests failed intermittently",
        FailureType.INFRASTRUCTURE_FAILURE: "Infrastructure or platform failure",
        FailureType.NETWORK_FAILURE: "Network connectivity failure",
        FailureType.RESOURCE_EXHAUSTION: "System resources exhausted",
        FailureType.TIMEOUT: "Operation timed out",
        FailureType.DEPLOYMENT_FAILURE: "Deployment process failed",
        FailureType.CONTAINER_FAILURE: "Container failed to start or run",
        FailureType.IMAGE_PULL_FAILURE: "Failed to pull container image",
        FailureType.CONFIGURATION_ERROR: "Configuration error",
        FailureType.AUTHENTICATION_FAILURE: "Authentication failed",
        FailureType.PERMISSION_DENIED: "Permission denied",
        FailureType.APPLICATION_CRASH: "Application crashed",
        FailureType.APPLICATION_ERROR: "Application error",
        FailureType.UNKNOWN: "Unknown failure type",
        FailureType.OTHER: "Other failure type",
    }
    return descriptions.get(failure_type, "No description available")
