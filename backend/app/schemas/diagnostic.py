"""Pydantic schemas for self-diagnostic capabilities.

These schemas support:
1. Error event capture and Logfire/telemetry enrichment
2. Error pattern detection and categorization
3. Diagnostic report generation
4. User feedback collection (oss-gtm-feedback compatible)
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, computed_field

from app.schemas.base import BaseSchema, TimestampSchema

# =============================================================================
# Enums for Error Classification
# =============================================================================


class ErrorSeverity(StrEnum):
    """Severity levels for errors."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(StrEnum):
    """High-level error categories for AI-powered classification."""

    # Infrastructure errors
    DATABASE = "database"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    DEPENDENCY = "dependency"  # Missing package or import errors

    # Application errors
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"

    # AI/Agent errors
    LLM_API = "llm_api"
    TOOL_EXECUTION = "tool_execution"
    AGENT_LOOP = "agent_loop"
    PROMPT_ERROR = "prompt_error"
    TOKEN_LIMIT = "token_limit"

    # External service errors
    EXTERNAL_API = "external_api"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Unknown/uncategorized
    UNKNOWN = "unknown"


class ErrorSource(StrEnum):
    """Source component where error originated."""

    API = "api"
    SERVICE = "service"
    REPOSITORY = "repository"
    AGENT = "agent"
    TOOL = "tool"
    MIDDLEWARE = "middleware"
    BACKGROUND_TASK = "background_task"
    EXTERNAL = "external"


class FeedbackType(StrEnum):
    """Types of user feedback."""

    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    PERFORMANCE_ISSUE = "performance_issue"
    DOCUMENTATION = "documentation"
    USABILITY = "usability"
    OTHER = "other"


class FeedbackStatus(StrEnum):
    """Status of user feedback processing."""

    NEW = "new"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


class PatternStatus(StrEnum):
    """Status of error patterns."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    INVESTIGATING = "investigating"
    KNOWN_ISSUE = "known_issue"


# =============================================================================
# Error Event Schemas (Logfire/Telemetry Enrichment)
# =============================================================================


class StackFrame(BaseSchema):
    """Single frame in a stack trace."""

    filename: str = Field(description="Source file path")
    lineno: int = Field(description="Line number")
    function: str = Field(description="Function name")
    code_context: str | None = Field(default=None, description="Code snippet at this line")
    local_vars: dict[str, str] | None = Field(
        default=None, description="Local variable names and types (not values for security)"
    )


class ErrorContext(BaseSchema):
    """Contextual information about when/where error occurred."""

    # Request context (if HTTP-triggered)
    request_id: str | None = Field(default=None, description="HTTP request ID")
    request_path: str | None = Field(default=None, description="HTTP endpoint path")
    request_method: str | None = Field(default=None, description="HTTP method")
    user_id: UUID | None = Field(default=None, description="User who triggered the error")

    # Agent context (if agent-triggered)
    agent_run_id: UUID | None = Field(default=None, description="Agent run ID")
    agent_name: str | None = Field(default=None, description="Agent name")
    tool_name: str | None = Field(default=None, description="Tool being executed")
    checkpoint_id: UUID | None = Field(default=None, description="Last checkpoint before error")

    # Sprint/workflow context
    sprint_id: UUID | None = Field(default=None, description="Active sprint ID")
    spec_id: UUID | None = Field(default=None, description="Related spec ID")
    phase: str | None = Field(default=None, description="Workflow phase")

    # Environment context
    environment: str | None = Field(default=None, description="Environment name")
    hostname: str | None = Field(default=None, description="Server hostname")
    service_version: str | None = Field(default=None, description="Application version")


class ErrorEventBase(BaseSchema):
    """Base schema for error events captured for analysis."""

    # Core error identification
    error_type: str = Field(description="Exception class name")
    error_code: str | None = Field(default=None, description="Application error code")
    message: str = Field(description="Error message")

    # Classification (can be AI-enriched)
    severity: ErrorSeverity = Field(default=ErrorSeverity.ERROR)
    category: ErrorCategory = Field(default=ErrorCategory.UNKNOWN)
    source: ErrorSource = Field(default=ErrorSource.API)

    # Stack trace
    stack_trace: list[StackFrame] = Field(default_factory=list)
    root_cause_frame: StackFrame | None = Field(
        default=None, description="Most relevant frame for debugging"
    )

    # Context
    context: ErrorContext = Field(default_factory=ErrorContext)

    # Telemetry correlation
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID")
    span_id: str | None = Field(default=None, description="OpenTelemetry span ID")
    parent_span_id: str | None = Field(default=None, description="Parent span ID")

    # Additional structured data
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Additional key-value attributes"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")


class ErrorEventCreate(ErrorEventBase):
    """Schema for creating an error event."""

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorEventRead(ErrorEventBase, TimestampSchema):
    """Schema for reading an error event."""

    id: UUID
    occurred_at: datetime
    fingerprint: str = Field(description="Hash for grouping similar errors")

    @computed_field
    @property
    def is_agent_error(self) -> bool:
        """Check if error is agent-related."""
        return self.context.agent_run_id is not None


class ErrorEventList(BaseSchema):
    """Paginated list of error events."""

    items: list[ErrorEventRead]
    total: int
    page: int = 1
    page_size: int = 50


# =============================================================================
# Error Pattern Schemas (Recurring Issue Detection)
# =============================================================================


class PatternMatchCriteria(BaseSchema):
    """Criteria for matching errors to a pattern."""

    error_types: list[str] = Field(default_factory=list, description="Error types to match")
    categories: list[ErrorCategory] = Field(default_factory=list, description="Categories to match")
    sources: list[ErrorSource] = Field(default_factory=list, description="Sources to match")
    message_pattern: str | None = Field(default=None, description="Regex for message matching")
    file_pattern: str | None = Field(default=None, description="Regex for file path matching")
    function_pattern: str | None = Field(default=None, description="Regex for function matching")
    min_occurrences: int = Field(default=3, description="Min occurrences to trigger pattern")
    time_window_hours: int = Field(default=24, description="Time window for occurrence counting")


class PatternStatistics(BaseSchema):
    """Statistics for an error pattern."""

    total_occurrences: int = Field(default=0)
    occurrences_last_hour: int = Field(default=0)
    occurrences_last_24h: int = Field(default=0)
    occurrences_last_7d: int = Field(default=0)
    first_seen: datetime | None = Field(default=None)
    last_seen: datetime | None = Field(default=None)
    affected_users_count: int = Field(default=0)
    affected_agent_runs_count: int = Field(default=0)
    mean_time_between_occurrences_seconds: float | None = Field(default=None)


class ErrorPatternBase(BaseSchema):
    """Base schema for error patterns."""

    name: str = Field(max_length=255, description="Pattern name")
    description: str | None = Field(default=None, description="Pattern description")
    fingerprint: str = Field(description="Unique fingerprint for this pattern")

    # Classification
    severity: ErrorSeverity = Field(default=ErrorSeverity.ERROR)
    category: ErrorCategory = Field(default=ErrorCategory.UNKNOWN)
    status: PatternStatus = Field(default=PatternStatus.ACTIVE)

    # Matching criteria
    match_criteria: PatternMatchCriteria = Field(default_factory=PatternMatchCriteria)

    # AI-generated insights
    ai_summary: str | None = Field(default=None, description="AI-generated pattern summary")
    ai_root_cause: str | None = Field(default=None, description="AI-suggested root cause")
    ai_fix_suggestions: list[str] = Field(default_factory=list, description="AI-suggested fixes")
    ai_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="AI confidence in analysis"
    )

    # Related documentation/issues
    related_docs: list[str] = Field(default_factory=list, description="URLs to related docs")
    github_issue_url: str | None = Field(default=None, description="Linked GitHub issue")


class ErrorPatternCreate(ErrorPatternBase):
    """Schema for creating an error pattern."""

    pass


class ErrorPatternUpdate(BaseSchema):
    """Schema for updating an error pattern."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    status: PatternStatus | None = Field(default=None)
    ai_summary: str | None = Field(default=None)
    ai_root_cause: str | None = Field(default=None)
    ai_fix_suggestions: list[str] | None = Field(default=None)
    github_issue_url: str | None = Field(default=None)


class ErrorPatternRead(ErrorPatternBase, TimestampSchema):
    """Schema for reading an error pattern."""

    id: UUID
    statistics: PatternStatistics = Field(default_factory=PatternStatistics)


class ErrorPatternList(BaseSchema):
    """Paginated list of error patterns."""

    items: list[ErrorPatternRead]
    total: int


# =============================================================================
# Diagnostic Report Schemas (Debugging Reports)
# =============================================================================


class DiagnosticSection(BaseSchema):
    """A section in a diagnostic report."""

    title: str = Field(description="Section title")
    content: str = Field(description="Section content (markdown supported)")
    severity: ErrorSeverity = Field(default=ErrorSeverity.INFO)
    data: dict[str, Any] = Field(default_factory=dict, description="Structured data")


class SystemHealthMetrics(BaseSchema):
    """System health metrics for diagnostics."""

    # API health
    api_latency_p50_ms: float | None = Field(default=None)
    api_latency_p99_ms: float | None = Field(default=None)
    api_error_rate_percent: float | None = Field(default=None)
    active_requests: int | None = Field(default=None)

    # Database health
    db_connection_pool_size: int | None = Field(default=None)
    db_active_connections: int | None = Field(default=None)
    db_query_latency_p50_ms: float | None = Field(default=None)

    # Agent health
    active_agent_runs: int | None = Field(default=None)
    agent_success_rate_percent: float | None = Field(default=None)
    avg_agent_duration_seconds: float | None = Field(default=None)

    # Resource utilization
    memory_usage_percent: float | None = Field(default=None)
    cpu_usage_percent: float | None = Field(default=None)


class DiagnosticReportBase(BaseSchema):
    """Base schema for diagnostic reports."""

    title: str = Field(max_length=255, description="Report title")
    report_type: str = Field(description="Type of report (manual, auto, scheduled)")

    # Context
    trigger_error_id: UUID | None = Field(default=None, description="Error that triggered report")
    trigger_pattern_id: UUID | None = Field(
        default=None, description="Pattern that triggered report"
    )
    agent_run_id: UUID | None = Field(default=None)
    sprint_id: UUID | None = Field(default=None)

    # Report content
    summary: str = Field(description="Executive summary")
    sections: list[DiagnosticSection] = Field(default_factory=list)

    # System state at time of report
    system_health: SystemHealthMetrics = Field(default_factory=SystemHealthMetrics)

    # Recommendations
    recommendations: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list, description="Urgent actions needed")

    # Time range covered
    time_range_start: datetime | None = Field(default=None)
    time_range_end: datetime | None = Field(default=None)


class DiagnosticReportCreate(DiagnosticReportBase):
    """Schema for creating a diagnostic report."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiagnosticReportRead(DiagnosticReportBase, TimestampSchema):
    """Schema for reading a diagnostic report."""

    id: UUID
    generated_at: datetime

    # Statistics about errors in the report period
    error_count: int = Field(default=0)
    unique_patterns_count: int = Field(default=0)
    affected_users_count: int = Field(default=0)


class DiagnosticReportList(BaseSchema):
    """Paginated list of diagnostic reports."""

    items: list[DiagnosticReportRead]
    total: int


# =============================================================================
# User Feedback Schemas (oss-gtm-feedback compatible)
# =============================================================================


class FeedbackEnvironment(BaseSchema):
    """Environment information for feedback."""

    browser: str | None = Field(default=None)
    os: str | None = Field(default=None)
    screen_resolution: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    language: str | None = Field(default=None)
    app_version: str | None = Field(default=None)


class FeedbackBase(BaseSchema):
    """Base schema for user feedback (oss-gtm-feedback compatible)."""

    # Core feedback fields
    feedback_type: FeedbackType = Field(default=FeedbackType.BUG_REPORT)
    title: str = Field(max_length=255, description="Brief summary")
    description: str = Field(description="Detailed description")

    # Optional context
    steps_to_reproduce: list[str] = Field(default_factory=list)
    expected_behavior: str | None = Field(default=None)
    actual_behavior: str | None = Field(default=None)

    # Correlation to errors/runs
    related_error_id: UUID | None = Field(default=None)
    related_agent_run_id: UUID | None = Field(default=None)
    related_sprint_id: UUID | None = Field(default=None)

    # Environment
    environment: FeedbackEnvironment = Field(default_factory=FeedbackEnvironment)
    page_url: str | None = Field(default=None, description="Page where feedback was submitted")

    # User sentiment
    satisfaction_score: int | None = Field(default=None, ge=1, le=5, description="1-5 rating")

    # Attachments
    screenshot_urls: list[str] = Field(default_factory=list)
    log_snippet: str | None = Field(default=None, description="Relevant log snippet")

    # Contact preference
    contact_email: str | None = Field(default=None)
    allow_follow_up: bool = Field(default=False)

    # Tags for categorization
    tags: list[str] = Field(default_factory=list)


class FeedbackCreate(FeedbackBase):
    """Schema for creating user feedback."""

    user_id: UUID | None = Field(default=None, description="Submitting user (if authenticated)")


class FeedbackUpdate(BaseSchema):
    """Schema for updating feedback status."""

    status: FeedbackStatus | None = Field(default=None)
    internal_notes: str | None = Field(default=None)
    resolution: str | None = Field(default=None)
    linked_pattern_id: UUID | None = Field(default=None)
    linked_github_issue: str | None = Field(default=None)


class FeedbackRead(FeedbackBase, TimestampSchema):
    """Schema for reading user feedback."""

    id: UUID
    user_id: UUID | None = None
    status: FeedbackStatus = Field(default=FeedbackStatus.NEW)
    internal_notes: str | None = Field(default=None)
    resolution: str | None = Field(default=None)
    linked_pattern_id: UUID | None = Field(default=None)
    linked_github_issue: str | None = Field(default=None)


class FeedbackList(BaseSchema):
    """Paginated list of feedback."""

    items: list[FeedbackRead]
    total: int


# =============================================================================
# Aggregation and Analysis Schemas
# =============================================================================


class ErrorTrend(BaseSchema):
    """Error trend data point."""

    timestamp: datetime
    count: int
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    severity_breakdown: dict[str, int] = Field(default_factory=dict)


class ErrorAnalyticsSummary(BaseSchema):
    """Summary of error analytics over a time period."""

    time_range_start: datetime
    time_range_end: datetime

    # Totals
    total_errors: int = 0
    unique_error_types: int = 0
    active_patterns: int = 0

    # Breakdowns
    by_category: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)

    # Top issues
    top_patterns: list[ErrorPatternRead] = Field(default_factory=list)
    top_affected_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    top_affected_agents: list[dict[str, Any]] = Field(default_factory=list)

    # Trends
    trends: list[ErrorTrend] = Field(default_factory=list)

    # Health indicators
    error_rate_change_percent: float | None = Field(
        default=None, description="Change from previous period"
    )
    mttr_seconds: float | None = Field(default=None, description="Mean time to resolution")


# =============================================================================
# Logfire Event Enrichment Schema
# =============================================================================


class LogfireErrorEnrichment(BaseSchema):
    """Schema for enriching Logfire events with diagnostic data.

    This schema defines the structured attributes that should be
    attached to Logfire spans when errors occur.
    """

    # Standard fields (match Logfire conventions)
    error_type: str
    error_message: str
    error_code: str | None = None

    # Classification (for filtering in Logfire dashboard)
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    error_source: ErrorSource

    # Pattern correlation
    pattern_fingerprint: str | None = None
    pattern_name: str | None = None
    is_known_issue: bool = False

    # Context identifiers (for correlation queries)
    agent_run_id: str | None = None
    sprint_id: str | None = None
    user_id: str | None = None

    # AI insights (if available)
    ai_suggested_category: str | None = None
    ai_confidence: float | None = None

    def to_logfire_attributes(self) -> dict[str, Any]:
        """Convert to Logfire-compatible attribute dictionary.

        Returns a flat dict with 'diagnostic.' prefixed keys suitable for
        attaching to Logfire spans. All values are converted to primitive
        types (str, int, float, bool) for compatibility.
        """
        attrs = {}
        # Use mode='json' to serialize enums to their string values
        for key, value in self.model_dump(exclude_none=True, mode="json").items():
            # Prefix custom attributes with 'diagnostic.' namespace
            attrs[f"diagnostic.{key}"] = (
                str(value) if not isinstance(value, (str, int, float, bool)) else value
            )
        return attrs
