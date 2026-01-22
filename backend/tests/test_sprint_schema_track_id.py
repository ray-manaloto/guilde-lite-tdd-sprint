"""Tests for Sprint schema track_id support."""

from app.schemas.sprint import SprintCreate


def test_sprint_create_accepts_track_id():
    sprint = SprintCreate(name="Test Sprint", track_id="track-001")
    assert sprint.track_id == "track-001"
