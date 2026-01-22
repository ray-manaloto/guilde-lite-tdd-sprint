"""Unit tests for the TelemetryCollector module.

Tests cover:
- TelemetryBackend enum values
- TelemetryEvent dataclass and serialization
- MemoryBackend operations and filtering
- JSONLBackend file operations and buffering
- LogfireBackend integration (mocked)
- PrometheusBackend metrics (mocked)
- TelemetryCollector multi-backend coordination
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.agents.orchestration.telemetry import (
    JSONLBackend,
    MemoryBackend,
    TelemetryBackend,
    TelemetryCollector,
    TelemetryEvent,
)


# ============================================================================
# TelemetryBackend Enum Tests
# ============================================================================


class TestTelemetryBackendEnum:
    """Tests for the TelemetryBackend enumeration."""

    def test_backend_values(self) -> None:
        """TelemetryBackend has expected values."""
        assert TelemetryBackend.LOGFIRE.value == "logfire"
        assert TelemetryBackend.JSONL.value == "jsonl"
        assert TelemetryBackend.PROMETHEUS.value == "prometheus"
        assert TelemetryBackend.MEMORY.value == "memory"

    def test_backend_from_string(self) -> None:
        """Can create TelemetryBackend from string value."""
        assert TelemetryBackend("logfire") == TelemetryBackend.LOGFIRE
        assert TelemetryBackend("jsonl") == TelemetryBackend.JSONL
        assert TelemetryBackend("prometheus") == TelemetryBackend.PROMETHEUS
        assert TelemetryBackend("memory") == TelemetryBackend.MEMORY

    def test_backend_invalid_string(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            TelemetryBackend("invalid")


# ============================================================================
# TelemetryEvent Tests
# ============================================================================


class TestTelemetryEvent:
    """Tests for the TelemetryEvent dataclass."""

    def test_event_default_values(self) -> None:
        """TelemetryEvent has sensible default values."""
        event = TelemetryEvent(event_type="test_event")
        assert event.event_type == "test_event"
        assert event.agent_name is None
        assert event.provider is None
        assert event.model is None
        assert event.success is True
        assert event.latency_ms == 0.0
        assert event.token_usage == {}
        assert event.error is None
        assert event.metadata == {}
        assert isinstance(event.id, UUID)
        assert isinstance(event.timestamp, datetime)

    def test_event_with_all_fields(self) -> None:
        """TelemetryEvent can be created with all fields."""
        event = TelemetryEvent(
            event_type="agent_response",
            agent_name="gpt-4o",
            provider="openai",
            model="gpt-4o-2024-05-13",
            success=True,
            latency_ms=1234.5,
            token_usage={"input": 100, "output": 50, "total": 150},
            error=None,
            metadata={"temperature": 0.7},
        )
        assert event.event_type == "agent_response"
        assert event.agent_name == "gpt-4o"
        assert event.provider == "openai"
        assert event.model == "gpt-4o-2024-05-13"
        assert event.success is True
        assert event.latency_ms == 1234.5
        assert event.token_usage == {"input": 100, "output": 50, "total": 150}
        assert event.metadata == {"temperature": 0.7}

    def test_event_with_error(self) -> None:
        """TelemetryEvent can represent a failed event."""
        event = TelemetryEvent(
            event_type="agent_response",
            agent_name="claude",
            provider="anthropic",
            success=False,
            error="Rate limit exceeded",
        )
        assert event.success is False
        assert event.error == "Rate limit exceeded"

    def test_event_to_dict(self) -> None:
        """TelemetryEvent serializes to dictionary correctly."""
        event = TelemetryEvent(
            event_type="test_event",
            agent_name="test-agent",
            provider="test-provider",
            model="test-model",
            success=True,
            latency_ms=500.0,
            token_usage={"input": 10, "output": 20},
            metadata={"key": "value"},
        )
        data = event.to_dict()

        assert data["event_type"] == "test_event"
        assert data["agent_name"] == "test-agent"
        assert data["provider"] == "test-provider"
        assert data["model"] == "test-model"
        assert data["success"] is True
        assert data["latency_ms"] == 500.0
        assert data["token_usage"] == {"input": 10, "output": 20}
        assert data["metadata"] == {"key": "value"}
        assert isinstance(data["id"], str)
        assert isinstance(data["timestamp"], str)

    def test_event_to_dict_uuid_format(self) -> None:
        """TelemetryEvent to_dict converts UUID to string correctly."""
        event = TelemetryEvent(event_type="test")
        data = event.to_dict()
        # Should be valid UUID string
        UUID(data["id"])

    def test_event_to_dict_timestamp_format(self) -> None:
        """TelemetryEvent to_dict converts timestamp to ISO format."""
        event = TelemetryEvent(event_type="test")
        data = event.to_dict()
        # Should be parseable ISO format
        datetime.fromisoformat(data["timestamp"])


# ============================================================================
# MemoryBackend Tests
# ============================================================================


class TestMemoryBackend:
    """Tests for the MemoryBackend handler."""

    @pytest.fixture
    def backend(self) -> MemoryBackend:
        """Create a fresh MemoryBackend for each test."""
        return MemoryBackend(max_events=100)

    @pytest.mark.asyncio
    async def test_record_event(self, backend: MemoryBackend) -> None:
        """Can record an event to memory."""
        event = TelemetryEvent(event_type="test_event", agent_name="test-agent")
        await backend.record(event)
        events = backend.get_events()
        assert len(events) == 1
        assert events[0] == event

    @pytest.mark.asyncio
    async def test_record_multiple_events(self, backend: MemoryBackend) -> None:
        """Can record multiple events."""
        events_to_record = [
            TelemetryEvent(event_type=f"event_{i}", agent_name=f"agent_{i}")
            for i in range(5)
        ]
        for event in events_to_record:
            await backend.record(event)

        stored_events = backend.get_events()
        assert len(stored_events) == 5

    @pytest.mark.asyncio
    async def test_max_events_limit(self) -> None:
        """MemoryBackend enforces max_events limit."""
        backend = MemoryBackend(max_events=5)

        for i in range(10):
            event = TelemetryEvent(event_type=f"event_{i}")
            await backend.record(event)

        events = backend.get_events(limit=100)
        assert len(events) == 5
        # Oldest events should be removed (FIFO)
        assert events[0].event_type == "event_5"
        assert events[-1].event_type == "event_9"

    @pytest.mark.asyncio
    async def test_flush_is_noop(self, backend: MemoryBackend) -> None:
        """Flush does nothing for MemoryBackend."""
        event = TelemetryEvent(event_type="test")
        await backend.record(event)
        await backend.flush()
        # Events should still be there
        assert len(backend.get_events()) == 1

    @pytest.mark.asyncio
    async def test_get_events_filter_by_event_type(
        self, backend: MemoryBackend
    ) -> None:
        """Can filter events by event_type."""
        await backend.record(TelemetryEvent(event_type="type_a", agent_name="agent1"))
        await backend.record(TelemetryEvent(event_type="type_b", agent_name="agent2"))
        await backend.record(TelemetryEvent(event_type="type_a", agent_name="agent3"))

        filtered = backend.get_events(event_type="type_a")
        assert len(filtered) == 2
        assert all(e.event_type == "type_a" for e in filtered)

    @pytest.mark.asyncio
    async def test_get_events_filter_by_agent_name(
        self, backend: MemoryBackend
    ) -> None:
        """Can filter events by agent_name."""
        await backend.record(TelemetryEvent(event_type="event", agent_name="agent1"))
        await backend.record(TelemetryEvent(event_type="event", agent_name="agent2"))
        await backend.record(TelemetryEvent(event_type="event", agent_name="agent1"))

        filtered = backend.get_events(agent_name="agent1")
        assert len(filtered) == 2
        assert all(e.agent_name == "agent1" for e in filtered)

    @pytest.mark.asyncio
    async def test_get_events_filter_combined(self, backend: MemoryBackend) -> None:
        """Can filter events by both event_type and agent_name."""
        await backend.record(TelemetryEvent(event_type="type_a", agent_name="agent1"))
        await backend.record(TelemetryEvent(event_type="type_b", agent_name="agent1"))
        await backend.record(TelemetryEvent(event_type="type_a", agent_name="agent2"))
        await backend.record(TelemetryEvent(event_type="type_a", agent_name="agent1"))

        filtered = backend.get_events(event_type="type_a", agent_name="agent1")
        assert len(filtered) == 2
        assert all(
            e.event_type == "type_a" and e.agent_name == "agent1" for e in filtered
        )

    @pytest.mark.asyncio
    async def test_get_events_limit(self, backend: MemoryBackend) -> None:
        """Can limit the number of returned events."""
        for i in range(10):
            await backend.record(TelemetryEvent(event_type=f"event_{i}"))

        limited = backend.get_events(limit=3)
        assert len(limited) == 3
        # Should return the most recent events (last 3)
        assert limited[0].event_type == "event_7"
        assert limited[-1].event_type == "event_9"

    @pytest.mark.asyncio
    async def test_get_events_empty(self, backend: MemoryBackend) -> None:
        """Returns empty list when no events match."""
        filtered = backend.get_events(event_type="nonexistent")
        assert filtered == []

    @pytest.mark.asyncio
    async def test_get_events_no_filter(self, backend: MemoryBackend) -> None:
        """Returns all events when no filter specified."""
        for i in range(5):
            await backend.record(TelemetryEvent(event_type=f"event_{i}"))

        all_events = backend.get_events()
        assert len(all_events) == 5


# ============================================================================
# JSONLBackend Tests
# ============================================================================


class TestJSONLBackend:
    """Tests for the JSONLBackend handler."""

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            return Path(f.name)

    @pytest.fixture
    def backend(self, temp_file: Path) -> JSONLBackend:
        """Create a fresh JSONLBackend for each test."""
        return JSONLBackend(
            file_path=temp_file,
            buffer_size=5,
            flush_interval_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_record_buffers_events(self, backend: JSONLBackend) -> None:
        """Events are buffered before writing."""
        event = TelemetryEvent(event_type="test_event")
        await backend.record(event)
        # Event should be in buffer, not yet written
        assert len(backend._buffer) == 1

    @pytest.mark.asyncio
    async def test_flush_writes_to_file(
        self, backend: JSONLBackend, temp_file: Path
    ) -> None:
        """Flush writes buffered events to file."""
        event = TelemetryEvent(event_type="test_event", agent_name="test-agent")
        await backend.record(event)
        await backend.flush()

        # Buffer should be empty
        assert len(backend._buffer) == 0

        # File should contain the event
        content = temp_file.read_text()
        assert "test_event" in content
        assert "test-agent" in content

    @pytest.mark.asyncio
    async def test_auto_flush_on_buffer_full(
        self, backend: JSONLBackend, temp_file: Path
    ) -> None:
        """Buffer automatically flushes when full."""
        # Buffer size is 5
        for i in range(6):
            await backend.record(TelemetryEvent(event_type=f"event_{i}"))

        # First 5 events should have been flushed
        content = temp_file.read_text()
        assert "event_0" in content
        assert "event_4" in content
        # Event 5 should still be in buffer
        assert len(backend._buffer) == 1

    @pytest.mark.asyncio
    async def test_flush_empty_buffer(self, backend: JSONLBackend) -> None:
        """Flush with empty buffer does nothing."""
        await backend.flush()
        # Should not raise

    @pytest.mark.asyncio
    async def test_multiple_flushes(
        self, backend: JSONLBackend, temp_file: Path
    ) -> None:
        """Multiple flushes append to file correctly."""
        await backend.record(TelemetryEvent(event_type="event_1"))
        await backend.flush()

        await backend.record(TelemetryEvent(event_type="event_2"))
        await backend.flush()

        lines = temp_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "event_1" in lines[0]
        assert "event_2" in lines[1]

    @pytest.mark.asyncio
    async def test_start_stop_auto_flush(self, backend: JSONLBackend) -> None:
        """Can start and stop auto-flush task."""
        await backend.start_auto_flush()
        assert backend._flush_task is not None
        assert not backend._flush_task.done()

        await backend.stop_auto_flush()
        assert backend._flush_task is None or backend._flush_task.done()

    @pytest.mark.asyncio
    async def test_stop_auto_flush_flushes_buffer(
        self, backend: JSONLBackend, temp_file: Path
    ) -> None:
        """Stopping auto-flush flushes remaining events."""
        await backend.start_auto_flush()
        await backend.record(TelemetryEvent(event_type="final_event"))
        await backend.stop_auto_flush()

        content = temp_file.read_text()
        assert "final_event" in content

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self) -> None:
        """Creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "subdir" / "nested" / "events.jsonl"
            backend = JSONLBackend(file_path=nested_path, buffer_size=1)
            await backend.record(TelemetryEvent(event_type="test"))
            await backend.flush()
            assert nested_path.exists()


# ============================================================================
# TelemetryCollector Tests
# ============================================================================


class TestTelemetryCollector:
    """Tests for the TelemetryCollector class."""

    def test_default_initialization(self) -> None:
        """TelemetryCollector initializes with default memory backend."""
        collector = TelemetryCollector()
        assert collector.get_memory_backend() is not None

    def test_initialization_with_memory_backend(self) -> None:
        """Can initialize with explicit memory backend."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])
        assert collector.get_memory_backend() is not None

    def test_initialization_with_jsonl_backend(self) -> None:
        """Can initialize with JSONL backend."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            collector = TelemetryCollector(
                backends=[TelemetryBackend.JSONL],
                jsonl_path=Path(f.name),
            )
            assert len(collector._handlers) == 1

    def test_initialization_jsonl_requires_path(self) -> None:
        """JSONL backend requires jsonl_path."""
        with pytest.raises(ValueError, match="jsonl_path"):
            TelemetryCollector(backends=[TelemetryBackend.JSONL])

    def test_initialization_multiple_backends(self) -> None:
        """Can initialize with multiple backends."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            collector = TelemetryCollector(
                backends=[TelemetryBackend.MEMORY, TelemetryBackend.JSONL],
                jsonl_path=Path(f.name),
            )
            assert len(collector._handlers) == 2
            assert collector.get_memory_backend() is not None

    @pytest.mark.asyncio
    async def test_record_to_single_backend(self) -> None:
        """Can record event to single backend."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])
        event = TelemetryEvent(event_type="test_event", agent_name="test-agent")
        await collector.record(event)

        memory = collector.get_memory_backend()
        assert memory is not None
        events = memory.get_events()
        assert len(events) == 1
        assert events[0] == event

    @pytest.mark.asyncio
    async def test_record_to_multiple_backends(self) -> None:
        """Can record event to multiple backends simultaneously."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)

        collector = TelemetryCollector(
            backends=[TelemetryBackend.MEMORY, TelemetryBackend.JSONL],
            jsonl_path=temp_path,
        )
        event = TelemetryEvent(event_type="multi_backend_event")
        await collector.record(event)
        await collector.flush()

        # Check memory backend
        memory = collector.get_memory_backend()
        assert memory is not None
        assert len(memory.get_events()) == 1

        # Check JSONL file
        content = temp_path.read_text()
        assert "multi_backend_event" in content

    @pytest.mark.asyncio
    async def test_flush_all_backends(self) -> None:
        """Flush writes to all backends."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = Path(f.name)

        collector = TelemetryCollector(
            backends=[TelemetryBackend.MEMORY, TelemetryBackend.JSONL],
            jsonl_path=temp_path,
        )

        for i in range(3):
            await collector.record(TelemetryEvent(event_type=f"event_{i}"))

        await collector.flush()

        content = temp_path.read_text()
        assert "event_0" in content
        assert "event_2" in content

    @pytest.mark.asyncio
    async def test_get_recent_events(self) -> None:
        """Can retrieve recent events from memory backend."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])

        for i in range(5):
            await collector.record(
                TelemetryEvent(event_type=f"event_{i}", agent_name=f"agent_{i % 2}")
            )

        events = await collector.get_recent_events(limit=3)
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_get_recent_events_with_filter(self) -> None:
        """Can filter recent events by event_type and agent_name."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])

        await collector.record(TelemetryEvent(event_type="type_a", agent_name="agent1"))
        await collector.record(TelemetryEvent(event_type="type_b", agent_name="agent1"))
        await collector.record(TelemetryEvent(event_type="type_a", agent_name="agent2"))

        filtered = await collector.get_recent_events(event_type="type_a")
        assert len(filtered) == 2
        assert all(e.event_type == "type_a" for e in filtered)

    @pytest.mark.asyncio
    async def test_get_recent_events_no_memory_backend(self) -> None:
        """Returns empty list when no memory backend configured."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            collector = TelemetryCollector(
                backends=[TelemetryBackend.JSONL],
                jsonl_path=Path(f.name),
            )
            events = await collector.get_recent_events()
            assert events == []

    def test_get_memory_backend_returns_none_when_not_configured(self) -> None:
        """get_memory_backend returns None when memory backend not configured."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            collector = TelemetryCollector(
                backends=[TelemetryBackend.JSONL],
                jsonl_path=Path(f.name),
            )
            assert collector.get_memory_backend() is None

    @pytest.mark.asyncio
    async def test_record_continues_on_backend_error(self) -> None:
        """Recording continues even if one backend fails."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])

        # Add a mock failing backend
        failing_backend = MagicMock()
        failing_backend.record = AsyncMock(side_effect=Exception("Backend error"))
        collector._handlers.append(failing_backend)

        event = TelemetryEvent(event_type="test_event")
        # Should not raise despite one backend failing
        await collector.record(event)

        # Memory backend should still have the event
        memory = collector.get_memory_backend()
        assert memory is not None
        assert len(memory.get_events()) == 1


# ============================================================================
# LogfireBackend Tests (Mocked)
# ============================================================================


class TestLogfireBackend:
    """Tests for the LogfireBackend handler (with mocked logfire)."""

    @pytest.mark.asyncio
    async def test_logfire_backend_record_success_event(self) -> None:
        """LogfireBackend records success events correctly."""
        with patch.dict("sys.modules", {"logfire": MagicMock()}):
            from app.agents.orchestration.telemetry import LogfireBackend

            mock_logfire = MagicMock()
            backend = LogfireBackend(service_name="test-service")
            backend._logfire = mock_logfire

            event = TelemetryEvent(
                event_type="agent_response",
                agent_name="test-agent",
                success=True,
                latency_ms=100.0,
            )
            await backend.record(event)

            mock_logfire.info.assert_called_once()
            call_args = mock_logfire.info.call_args
            assert "agent_response" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_logfire_backend_record_error_event(self) -> None:
        """LogfireBackend records error events correctly."""
        with patch.dict("sys.modules", {"logfire": MagicMock()}):
            from app.agents.orchestration.telemetry import LogfireBackend

            mock_logfire = MagicMock()
            backend = LogfireBackend(service_name="test-service")
            backend._logfire = mock_logfire

            event = TelemetryEvent(
                event_type="agent_response",
                success=False,
                error="Connection timeout",
            )
            await backend.record(event)

            mock_logfire.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_logfire_backend_flush_is_noop(self) -> None:
        """LogfireBackend flush does nothing."""
        with patch.dict("sys.modules", {"logfire": MagicMock()}):
            from app.agents.orchestration.telemetry import LogfireBackend

            backend = LogfireBackend(service_name="test-service")
            await backend.flush()  # Should not raise


# ============================================================================
# PrometheusBackend Tests (Mocked)
# ============================================================================


class TestPrometheusBackend:
    """Tests for the PrometheusBackend handler (with mocked prometheus_client)."""

    @pytest.mark.asyncio
    async def test_prometheus_backend_record_event(self) -> None:
        """PrometheusBackend records metrics correctly."""
        mock_counter = MagicMock()
        mock_histogram = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "prometheus_client": MagicMock(
                    Counter=MagicMock(return_value=mock_counter),
                    Histogram=MagicMock(return_value=mock_histogram),
                )
            },
        ):
            from app.agents.orchestration.telemetry import PrometheusBackend

            backend = PrometheusBackend(service_name="test-service")
            # Force initialization
            backend._ensure_initialized()

            event = TelemetryEvent(
                event_type="agent_response",
                agent_name="test-agent",
                provider="openai",
                success=True,
                latency_ms=150.0,
            )
            await backend.record(event)

            # Verify metrics were recorded
            assert mock_counter.labels.called or mock_histogram.labels.called

    @pytest.mark.asyncio
    async def test_prometheus_backend_flush_is_noop(self) -> None:
        """PrometheusBackend flush does nothing."""
        with patch.dict("sys.modules", {"prometheus_client": MagicMock()}):
            from app.agents.orchestration.telemetry import PrometheusBackend

            backend = PrometheusBackend(service_name="test-service")
            await backend.flush()  # Should not raise


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_collector_operations(self) -> None:
        """Operations work correctly on empty collector."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])

        events = await collector.get_recent_events()
        assert events == []

        await collector.flush()  # Should not raise

    @pytest.mark.asyncio
    async def test_event_with_none_fields(self) -> None:
        """Events with None fields serialize correctly."""
        event = TelemetryEvent(
            event_type="test",
            agent_name=None,
            provider=None,
            model=None,
            error=None,
        )
        data = event.to_dict()
        assert data["agent_name"] is None
        assert data["provider"] is None
        assert data["model"] is None
        assert data["error"] is None

    @pytest.mark.asyncio
    async def test_event_with_complex_metadata(self) -> None:
        """Events with complex metadata serialize correctly."""
        collector = TelemetryCollector(backends=[TelemetryBackend.MEMORY])

        event = TelemetryEvent(
            event_type="test",
            metadata={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "number": 42.5,
                "boolean": True,
            },
        )
        await collector.record(event)

        memory = collector.get_memory_backend()
        assert memory is not None
        stored = memory.get_events()[0]
        assert stored.metadata["nested"]["key"] == "value"
        assert stored.metadata["list"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_large_token_usage(self) -> None:
        """Events with large token counts work correctly."""
        event = TelemetryEvent(
            event_type="test",
            token_usage={
                "input": 100000,
                "output": 50000,
                "total": 150000,
            },
        )
        data = event.to_dict()
        assert data["token_usage"]["total"] == 150000

    @pytest.mark.asyncio
    async def test_high_latency_value(self) -> None:
        """Events with high latency values work correctly."""
        event = TelemetryEvent(
            event_type="test",
            latency_ms=999999.999,
        )
        data = event.to_dict()
        assert data["latency_ms"] == 999999.999
