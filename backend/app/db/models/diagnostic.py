"""SQLAlchemy models for self-diagnostic capabilities.

These models support:
1. Error event persistence and querying
2. Error pattern detection and tracking
3. Diagnostic report storage
4. User feedback collection
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# =============================================================================
# Enums (mirroring schema enums for database constraints)
# =============================================================================


class ErrorSeverity(StrEnum):
    """Severity levels for errors."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(StrEnum):
    """High-level error categories."""

    DATABASE = "database"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"
    LLM_API = "llm_api"
    TOOL_EXECUTION = "tool_execution"
    AGENT_LOOP = "agent_loop"
    PROMPT_ERROR = "prompt_error"
    TOKEN_LIMIT = "token_limit"
    EXTERNAL_API = "external_api"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
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
# Error Event Model
# =============================================================================


class ErrorEvent(Base, TimestampMixin):
    """Captured error event for analysis.

    Stores structured error data with full context for:
    - Pattern detection
    - AI-powered categorization
    - Diagnostic report generation
    - Correlation with agent runs and sprints
    """

    __tablename__ = "error_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core error identification
    error_type: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Exception class name"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, comment="Application error code"
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Fingerprint for grouping similar errors
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA256 hash for grouping similar errors",
    )

    # Classification
    severity: Mapped[ErrorSeverity] = mapped_column(
        Enum(ErrorSeverity, name="error_severity"),
        default=ErrorSeverity.ERROR,
        nullable=False,
        index=True,
    )
    category: Mapped[ErrorCategory] = mapped_column(
        Enum(ErrorCategory, name="error_category"),
        default=ErrorCategory.UNKNOWN,
        nullable=False,
        index=True,
    )
    source: Mapped[ErrorSource] = mapped_column(
        Enum(ErrorSource, name="error_source"),
        default=ErrorSource.API,
        nullable=False,
        index=True,
    )

    # When the error occurred
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Stack trace (stored as JSONB for flexibility)
    stack_trace: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, comment="List of StackFrame objects"
    )
    root_cause_frame: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Most relevant frame for debugging"
    )

    # Context (JSONB for flexible structure)
    context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="ErrorContext object"
    )

    # Telemetry correlation
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Foreign keys for direct correlation
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Pattern correlation
    pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_patterns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Additional attributes and tags
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Relationships
    pattern: Mapped[ErrorPattern | None] = relationship("ErrorPattern", back_populates="events")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_error_events_category_occurred", "category", "occurred_at"),
        Index("ix_error_events_fingerprint_occurred", "fingerprint", "occurred_at"),
        Index("ix_error_events_severity_occurred", "severity", "occurred_at"),
        Index("ix_error_events_source_category", "source", "category"),
    )

    @staticmethod
    def compute_fingerprint(
        error_type: str, message: str, source: str, file_path: str | None = None
    ) -> str:
        """Compute fingerprint for grouping similar errors.

        The fingerprint is based on:
        - Error type (exception class)
        - Normalized message (numbers removed)
        - Source component
        - File path (if available)
        """
        import re

        # Normalize message by removing variable parts (numbers, UUIDs, etc.)
        normalized_message = re.sub(r"\b[0-9a-fA-F-]{36}\b", "<UUID>", message)  # UUIDs
        normalized_message = re.sub(r"\b\d+\b", "<NUM>", normalized_message)  # Numbers
        normalized_message = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", normalized_message)  # Hex

        # Truncate message to avoid overly specific fingerprints
        normalized_message = normalized_message[:200]

        fingerprint_data = f"{error_type}|{normalized_message}|{source}"
        if file_path:
            fingerprint_data += f"|{file_path}"

        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    def __repr__(self) -> str:
        return f"<ErrorEvent(id={self.id}, type={self.error_type}, category={self.category})>"


# =============================================================================
# Error Pattern Model
# =============================================================================


class ErrorPattern(Base, TimestampMixin):
    """Pattern for recurring errors.

    Patterns are created automatically when similar errors
    occur repeatedly, or manually by developers.
    """

    __tablename__ = "error_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Pattern identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Classification
    severity: Mapped[ErrorSeverity] = mapped_column(
        Enum(ErrorSeverity, name="error_severity", create_type=False),
        default=ErrorSeverity.ERROR,
        nullable=False,
    )
    category: Mapped[ErrorCategory] = mapped_column(
        Enum(ErrorCategory, name="error_category", create_type=False),
        default=ErrorCategory.UNKNOWN,
        nullable=False,
    )
    status: Mapped[PatternStatus] = mapped_column(
        Enum(PatternStatus, name="pattern_status"),
        default=PatternStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Matching criteria (JSONB for flexibility)
    match_criteria: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="PatternMatchCriteria object",
    )

    # Statistics (denormalized for performance)
    total_occurrences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    affected_users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    affected_agent_runs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # AI-generated insights
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_fix_suggestions: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Related documentation/issues
    related_docs: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    github_issue_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    events: Mapped[list[ErrorEvent]] = relationship("ErrorEvent", back_populates="pattern")

    __table_args__ = (
        Index("ix_error_patterns_status_last_seen", "status", "last_seen"),
        Index("ix_error_patterns_category_status", "category", "status"),
    )

    def increment_occurrence(
        self, user_id: uuid.UUID | None = None, agent_run_id: uuid.UUID | None = None
    ) -> None:
        """Update occurrence statistics when a matching error is found."""
        self.total_occurrences += 1
        self.last_seen = datetime.utcnow()
        if self.first_seen is None:
            self.first_seen = self.last_seen

    def __repr__(self) -> str:
        return (
            f"<ErrorPattern(id={self.id}, name={self.name}, occurrences={self.total_occurrences})>"
        )


# =============================================================================
# Diagnostic Report Model
# =============================================================================


class DiagnosticReport(Base, TimestampMixin):
    """Diagnostic report for debugging.

    Reports can be:
    - Triggered automatically by error patterns
    - Generated manually by developers
    - Created on a schedule
    """

    __tablename__ = "diagnostic_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Report identification
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="manual, auto, scheduled"
    )

    # Trigger context
    trigger_error_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_patterns.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Report content
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, comment="List of DiagnosticSection objects"
    )
    system_health: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="SystemHealthMetrics object"
    )

    # Recommendations
    recommendations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    immediate_actions: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    # Time context
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    time_range_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_range_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Statistics
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_patterns_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    affected_users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (Index("ix_diagnostic_reports_type_generated", "report_type", "generated_at"),)

    def __repr__(self) -> str:
        return f"<DiagnosticReport(id={self.id}, title={self.title}, type={self.report_type})>"


# =============================================================================
# User Feedback Model (oss-gtm-feedback compatible)
# =============================================================================


class UserFeedback(Base, TimestampMixin):
    """User-submitted feedback.

    Compatible with oss-gtm-feedback patterns for:
    - Bug reports
    - Feature requests
    - Performance issues
    - General feedback
    """

    __tablename__ = "user_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Submitter
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allow_follow_up: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Feedback classification
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, name="feedback_type"),
        default=FeedbackType.BUG_REPORT,
        nullable=False,
        index=True,
    )
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="feedback_status"),
        default=FeedbackStatus.NEW,
        nullable=False,
        index=True,
    )

    # Feedback content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps_to_reproduce: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    expected_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Context correlation
    related_error_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Environment (JSONB for flexibility)
    environment: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="FeedbackEnvironment object"
    )
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # User sentiment
    satisfaction_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Attachments
    screenshot_urls: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    log_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tags
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Internal processing
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_patterns.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_github_issue: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_user_feedback_type_status", "feedback_type", "status"),
        Index("ix_user_feedback_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, type={self.feedback_type}, status={self.status})>"
