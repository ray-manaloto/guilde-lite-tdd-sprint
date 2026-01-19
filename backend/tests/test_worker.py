"""Tests for Celery worker tasks."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


@contextmanager
def task_request(task, task_id: str = "test-task-id", retries: int = 0):
    """Provide a fake Celery request context for bound task execution."""
    request = MagicMock()
    request.id = task_id
    request.retries = retries
    task.request_stack.push(request)
    try:
        yield request
    finally:
        task.request_stack.pop()


class TestExampleTask:
    """Tests for example_task."""

    def test_example_task_success(self):
        """Test example_task completes successfully."""
        from app.worker.tasks.examples import example_task

        with task_request(example_task):
            with patch("app.worker.tasks.examples.time.sleep"):
                result = example_task.run("test message")

        assert result["status"] == "completed"
        assert "test message" in result["message"]
        assert result["task_id"] == "test-task-id"

    def test_example_task_retry_on_error(self):
        """Test example_task retries on error."""
        from app.worker.tasks.examples import example_task

        with task_request(example_task, retries=0):
            with patch("app.worker.tasks.examples.time.sleep", side_effect=Exception("Test error")):
                with patch.object(example_task, "retry", side_effect=Exception("Retry")) as mock_retry:
                    with pytest.raises(Exception, match="Retry"):
                        example_task.run("test message")
                    mock_retry.assert_called_once()


class TestLongRunningTask:
    """Tests for long_running_task."""

    def test_long_running_task_completes(self):
        """Test long_running_task completes with progress."""
        from app.worker.tasks.examples import long_running_task

        with task_request(long_running_task):
            with patch("app.worker.tasks.examples.time.sleep"):
                with patch.object(long_running_task, "update_state") as mock_update_state:
                    result = long_running_task.run(duration=3)

        assert result["status"] == "completed"
        assert result["duration"] == 3
        # Check progress updates were made
        assert mock_update_state.call_count == 3


class TestSendEmailTask:
    """Tests for send_email_task."""

    def test_send_email_task_success(self):
        """Test send_email_task sends email."""
        from app.worker.tasks.examples import send_email_task

        with patch("app.worker.tasks.examples.time.sleep"):
            result = send_email_task("test@example.com", "Subject", "Body")

        assert result["status"] == "sent"
        assert result["to"] == "test@example.com"
        assert result["subject"] == "Subject"


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration."""

    def test_celery_app_exists(self):
        """Test Celery app is configured."""
        from app.worker.celery_app import celery_app

        assert celery_app is not None
        assert celery_app.main == "guilde_lite_tdd_sprint"
