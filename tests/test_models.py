"""Tests for data models."""

import json
import pytest
from datetime import datetime

from calibration_trainer.models import Question, Response, Settings


class TestQuestion:
    """Tests for Question model."""

    def test_create_interval_question(self):
        """Test creating an interval question."""
        q = Question(
            id="test-1",
            text="What year did WWII end?",
            question_type="interval",
            answer=1945,
            units="year",
            category="history",
            log_scale=False,
            answer_range_min=1900,
            answer_range_max=2000,
        )

        assert q.id == "test-1"
        assert q.question_type == "interval"
        assert q.answer == 1945
        assert q.binary_answer is None

    def test_create_binary_question(self):
        """Test creating a binary question."""
        q = Question(
            id="test-2",
            text="Is the Earth round?",
            question_type="binary",
            answer=1,
            binary_answer=True,
            units="",
            category="science",
            log_scale=False,
            answer_range_min=0,
            answer_range_max=1,
        )

        assert q.question_type == "binary"
        assert q.binary_answer is True

    def test_to_dict_and_from_dict(self):
        """Test round-trip conversion."""
        original = Question(
            id="test-3",
            text="Test question",
            question_type="interval",
            answer=42,
            units="items",
            category="test",
            log_scale=True,
            answer_range_min=1,
            answer_range_max=100,
            source="bundled",
        )

        data = original.to_dict()
        restored = Question.from_dict(data)

        assert restored.id == original.id
        assert restored.text == original.text
        assert restored.question_type == original.question_type
        assert restored.answer == original.answer
        assert restored.log_scale == original.log_scale
        assert restored.source == original.source


class TestResponse:
    """Tests for Response model."""

    def test_create_binary_response(self):
        """Test creating a binary response."""
        r = Response(
            question_id="q1",
            session_id="s1",
            question_type="binary",
            true_answer=1.0,
            is_correct=True,
            score=5.5,
            probability_estimate=75.0,
        )

        assert r.question_type == "binary"
        assert r.probability_estimate == 75.0
        assert r.is_correct is True

    def test_create_interval_response(self):
        """Test creating an interval response."""
        r = Response(
            question_id="q2",
            session_id="s1",
            question_type="interval",
            true_answer=66.0,
            is_correct=True,
            score=8.2,
            lower_bound=50.0,
            upper_bound=80.0,
            confidence_level=80,
        )

        assert r.question_type == "interval"
        assert r.lower_bound == 50.0
        assert r.upper_bound == 80.0
        assert r.confidence_level == 80

    def test_auto_generates_id_and_timestamp(self):
        """Test that ID and timestamp are auto-generated."""
        r = Response(
            question_id="q1",
            session_id="s1",
            question_type="binary",
            true_answer=1.0,
            is_correct=True,
            score=0.0,
        )

        assert r.id is not None
        assert len(r.id) > 0
        assert r.timestamp is not None

    def test_to_dict_and_from_dict(self):
        """Test round-trip conversion."""
        original = Response(
            question_id="q1",
            session_id="s1",
            question_type="interval",
            true_answer=100.0,
            is_correct=False,
            score=-5.0,
            lower_bound=20.0,
            upper_bound=50.0,
            confidence_level=90,
        )

        data = original.to_dict()
        restored = Response.from_dict(data)

        assert restored.question_id == original.question_id
        assert restored.session_id == original.session_id
        assert restored.is_correct == original.is_correct
        assert restored.score == original.score
        assert restored.lower_bound == original.lower_bound


class TestSettings:
    """Tests for Settings model."""

    def test_default_values(self):
        """Test default settings values."""
        s = Settings()

        assert s.default_session_length == 10
        assert s.default_confidence_level == 80
        assert s.default_mode == "binary"
        assert isinstance(s.imported_question_files, list)
        assert isinstance(s.enabled_categories, list)

    def test_to_dict_and_from_dict(self):
        """Test round-trip conversion."""
        original = Settings(
            default_session_length=15,
            default_confidence_level=90,
            default_mode="interval",
            imported_question_files=["file1.json", "file2.json"],
            enabled_categories=["science", "history"],
        )

        data = original.to_dict()
        # Verify to_dict produces JSON strings
        assert data["imported_question_files"] == json.dumps(["file1.json", "file2.json"])
        assert data["enabled_categories"] == json.dumps(["science", "history"])

        restored = Settings.from_dict(data)

        assert restored.default_session_length == 15
        assert restored.default_confidence_level == 90
        assert restored.default_mode == "interval"
        assert restored.imported_question_files == ["file1.json", "file2.json"]
        assert restored.enabled_categories == ["science", "history"]

    def test_handles_empty_strings_in_lists(self):
        """Test that empty strings in serialized lists are handled."""
        data = {
            "imported_question_files": "",
            "enabled_categories": "",
        }

        s = Settings.from_dict(data)

        assert s.imported_question_files == []
        assert s.enabled_categories == []

    def test_handles_legacy_comma_separated_format(self):
        """Test backward compatibility with comma-separated format."""
        data = {
            "imported_question_files": "file1.json,file2.json",
            "enabled_categories": "science,history",
        }

        s = Settings.from_dict(data)

        assert s.imported_question_files == ["file1.json", "file2.json"]
        assert s.enabled_categories == ["science", "history"]

    def test_handles_paths_with_commas_in_json_format(self):
        """Test that JSON format correctly handles paths containing commas."""
        files_with_commas = ["/path/to/file,v2.json", "another,file.json"]
        data = {
            "imported_question_files": json.dumps(files_with_commas),
            "enabled_categories": json.dumps(["science"]),
        }

        s = Settings.from_dict(data)

        assert s.imported_question_files == files_with_commas
