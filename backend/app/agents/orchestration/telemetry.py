"""Telemetry collector for multi-agent orchestration.

Supports multiple backends: Logfire, JSONL file, and Prometheus metrics.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import orjson


class TelemetryBackend(str, Enum):
    """Supported telemetry backends."""

    LOGFIRE = "logfire"
    JSONL = "jsonl"
    PROMETHEUS = "prometheus"
    MEMORY = "memory"


@dataclass
class TelemetryEvent:
    """A single telemetry event.

    Attributes:
        id: Unique event identifier
        event_type: Type of event (e.g., "agent_response", "checkpoint_created")
        agent_name: Name of the agent (if applicable)
        provider: Provider name (if applicable)
        model: Model used (if applicable)
        success: Whether operation succeeded
        latency_ms: Operation latency in milliseconds
        token_usage: Token counts
        error: Error message if failed
        metadata: Additional event data
        timestamp: When event occurred
    """

    event_type: str
    agent_name: str | None = None
    provider: str | None = None
    model: str | None = None
    success: bool = True
    latency_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "agent_name": self.agent_name,
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class TelemetryBackendHandler(ABC):
    """Abstract base for telemetry backend handlers."""

    @abstractmethod
    async def record(self, event: TelemetryEvent) -> None:
        """Record a telemetry event."""

    @abstractmethod
    async def flush(self) -> None:
        """Flush any buffered events."""


class MemoryBackend(TelemetryBackendHandler):
    """In-memory telemetry backend for testing."""

    def __init__(self, max_events: int = 10000) -> None:
        self.events: list[TelemetryEvent] = []
        self.max_events = max_events

    async def record(self, event: TelemetryEvent) -> None:
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    async def flush(self) -> None:
        pass

    def get_events(
        self,
        event_type: str | None = None,
        agent_name: str | None = None,
        limit: int = 100,
    ) -> list[TelemetryEvent]:
        """Query events with optional filters."""
        events = self.events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if agent_name:
            events = [e for e in events if e.agent_name == agent_name]
        return events[-limit:]


class JSONLBackend(TelemetryBackendHandler):
    """JSONL file telemetry backend."""

    def __init__(
        self,
        file_path: Path,
        buffer_size: int = 100,
        flush_interval_seconds: float = 5.0,
    ) -> None:
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval_seconds
        self._buffer: list[TelemetryEvent] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None

    async def record(self, event: TelemetryEvent) -> None:
        async with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self.buffer_size:
                await self._write_buffer()

    async def flush(self) -> None:
        async with self._lock:
            await self._write_buffer()

    async def _write_buffer(self) -> None:
        if not self._buffer:
            return

        # Append to file
        lines = [orjson.dumps(e.to_dict()).decode() + "\n" for e in self._buffer]
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("a") as f:
            f.writelines(lines)

        self._buffer.clear()

    async def start_auto_flush(self) -> None:
        """Start background task for periodic flushing."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._auto_flush_loop())

    async def stop_auto_flush(self) -> None:
        """Stop background flush task."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
            await self.flush()

    async def _auto_flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()


class LogfireBackend(TelemetryBackendHandler):
    """Logfire telemetry backend.

    Integrates with Pydantic Logfire for structured observability.
    """

    def __init__(self, service_name: str = "orchestration") -> None:
        self.service_name = service_name
        self._logfire: Any = None

    def _get_logfire(self) -> Any:
        """Lazy import and configure logfire."""
        if self._logfire is None:
            try:
                import logfire
                self._logfire = logfire
            except ImportError:
                # Logfire not installed, use no-op
                self._logfire = None
        return self._logfire

    async def record(self, event: TelemetryEvent) -> None:
        logfire = self._get_logfire()
        if logfire is None:
            return

        # Build span attributes
        attributes = {
            "event_type": event.event_type,
            "success": event.success,
            "latency_ms": event.latency_ms,
        }
        if event.agent_name:
            attributes["agent_name"] = event.agent_name
        if event.provider:
            attributes["provider"] = event.provider
        if event.model:
            attributes["model"] = event.model
        if event.token_usage:
            attributes["token_usage"] = event.token_usage
        if event.error:
            attributes["error"] = event.error

        # Log as span
        if event.success:
            logfire.info(
                f"{self.service_name}.{event.event_type}",
                **attributes,
            )
        else:
            logfire.error(
                f"{self.service_name}.{event.event_type}",
                **attributes,
            )

    async def flush(self) -> None:
        # Logfire handles its own flushing
        pass


class PrometheusBackend(TelemetryBackendHandler):
    """Prometheus metrics backend.

    Exposes metrics for scraping by Prometheus.
    """

    def __init__(self, service_name: str = "orchestration") -> None:
        self.service_name = service_name
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of Prometheus metrics."""
        if self._initialized:
            return

        try:
            from prometheus_client import Counter, Histogram

            self._counters["requests"] = Counter(
                "orchestration_agent_requests_total",
                "Total agent requests",
                ["agent_name", "provider", "model", "success"],
            )
            self._counters["tokens"] = Counter(
                "orchestration_tokens_total",
                "Total tokens used",
                ["agent_name", "provider", "type"],
            )
            self._histograms["latency"] = Histogram(
                "orchestration_agent_latency_seconds",
                "Agent request latency",
                ["agent_name", "provider"],
                buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
            )
            self._initialized = True
        except ImportError:
            # prometheus_client not installed
            pass

    async def record(self, event: TelemetryEvent) -> None:
        self._ensure_initialized()
        if not self._initialized:
            return

        labels = {
            "agent_name": event.agent_name or "unknown",
            "provider": event.provider or "unknown",
            "model": event.model or "unknown",
            "success": str(event.success).lower(),
        }

        # Increment request counter
        self._counters["requests"].labels(**labels).inc()

        # Record latency
        self._histograms["latency"].labels(
            agent_name=labels["agent_name"],
            provider=labels["provider"],
        ).observe(event.latency_ms / 1000)

        # Record token usage
        if event.token_usage:
            for token_type, count in event.token_usage.items():
                self._counters["tokens"].labels(
                    agent_name=labels["agent_name"],
                    provider=labels["provider"],
                    type=token_type,
                ).inc(count)

    async def flush(self) -> None:
        # Prometheus handles its own scraping
        pass


class TelemetryCollector:
    """Central telemetry collector with multi-backend support.

    Example:
        >>> collector = TelemetryCollector(
        ...     backends=[TelemetryBackend.MEMORY, TelemetryBackend.JSONL],
        ...     jsonl_path=Path("./telemetry.jsonl")
        ... )
        >>> await collector.record(TelemetryEvent(
        ...     event_type="agent_response",
        ...     agent_name="gpt-4o",
        ...     success=True,
        ...     latency_ms=1234.5
        ... ))
    """

    def __init__(
        self,
        backends: list[TelemetryBackend] | None = None,
        jsonl_path: Path | None = None,
        service_name: str = "orchestration",
    ) -> None:
        """Initialize telemetry collector.

        Args:
            backends: List of backends to use (default: [MEMORY])
            jsonl_path: Path for JSONL backend (required if JSONL in backends)
            service_name: Service name for Logfire backend
        """
        self._handlers: list[TelemetryBackendHandler] = []

        backends = backends or [TelemetryBackend.MEMORY]

        for backend in backends:
            if backend == TelemetryBackend.MEMORY:
                self._handlers.append(MemoryBackend())
            elif backend == TelemetryBackend.JSONL:
                if not jsonl_path:
                    raise ValueError("jsonl_path required for JSONL backend")
                self._handlers.append(JSONLBackend(jsonl_path))
            elif backend == TelemetryBackend.LOGFIRE:
                self._handlers.append(LogfireBackend(service_name))
            elif backend == TelemetryBackend.PROMETHEUS:
                self._handlers.append(PrometheusBackend())

    async def record(self, event: TelemetryEvent) -> None:
        """Record an event to all backends.

        Args:
            event: Event to record
        """
        await asyncio.gather(
            *[handler.record(event) for handler in self._handlers],
            return_exceptions=True,
        )

    async def flush(self) -> None:
        """Flush all backends."""
        await asyncio.gather(
            *[handler.flush() for handler in self._handlers],
            return_exceptions=True,
        )

    def get_memory_backend(self) -> MemoryBackend | None:
        """Get the memory backend if configured.

        Returns:
            Memory backend or None if not configured
        """
        for handler in self._handlers:
            if isinstance(handler, MemoryBackend):
                return handler
        return None

    async def get_recent_events(
        self,
        event_type: str | None = None,
        agent_name: str | None = None,
        limit: int = 100,
    ) -> list[TelemetryEvent]:
        """Query recent events from memory backend.

        Args:
            event_type: Filter by event type
            agent_name: Filter by agent name
            limit: Maximum events to return

        Returns:
            List of events (empty if no memory backend)
        """
        memory = self.get_memory_backend()
        if memory:
            return memory.get_events(event_type, agent_name, limit)
        return []
