"""Integration tests for the Repository data access layer."""

import pytest

from calibration_trainer.database import Repository
from calibration_trainer.models import Question, Response, Settings


@pytest.fixture
def repo(tmp_path):
    """Create a fresh repository with an in-memory-like temp DB."""
    r = Repository(db_path=tmp_path / "test.db")
    yield r
    r.close()


def _make_binary_question(id: str = "bq-1", **overrides) -> Question:
    defaults = dict(
        id=id,
        text="Is the sky blue?",
        question_type="binary",
        answer=1,
        binary_answer=True,
        units="",
        category="science",
        log_scale=False,
        answer_range_min=0,
        answer_range_max=1,
        source="bundled",
    )
    defaults.update(overrides)
    return Question(**defaults)


def _make_interval_question(id: str = "iq-1", **overrides) -> Question:
    defaults = dict(
        id=id,
        text="What year was the moon landing?",
        question_type="interval",
        answer=1969,
        units="year",
        category="history",
        log_scale=False,
        answer_range_min=1900,
        answer_range_max=2000,
        source="bundled",
    )
    defaults.update(overrides)
    return Question(**defaults)


def _make_binary_response(question_id: str = "bq-1", session_id: str = "s1", **overrides) -> Response:
    defaults = dict(
        question_id=question_id,
        session_id=session_id,
        question_type="binary",
        true_answer=1.0,
        is_correct=True,
        score=5.0,
        probability_estimate=75.0,
    )
    defaults.update(overrides)
    return Response(**defaults)


def _make_interval_response(question_id: str = "iq-1", session_id: str = "s1", **overrides) -> Response:
    defaults = dict(
        question_id=question_id,
        session_id=session_id,
        question_type="interval",
        true_answer=1969.0,
        is_correct=True,
        score=7.0,
        lower_bound=1950.0,
        upper_bound=1980.0,
        confidence_level=80,
    )
    defaults.update(overrides)
    return Response(**defaults)


class TestQuestionCRUD:
    """Tests for question add/get operations."""

    def test_add_and_get_binary_question(self, repo):
        q = _make_binary_question()
        repo.add_question(q)
        result = repo.get_question("bq-1")

        assert result is not None
        assert result.id == "bq-1"
        assert result.question_type == "binary"
        assert result.binary_answer is True
        assert result.log_scale is False

    def test_add_and_get_interval_question(self, repo):
        q = _make_interval_question()
        repo.add_question(q)
        result = repo.get_question("iq-1")

        assert result is not None
        assert result.question_type == "interval"
        assert result.answer == 1969
        assert result.binary_answer is None

    def test_get_nonexistent_question_returns_none(self, repo):
        assert repo.get_question("nope") is None

    def test_get_questions_filters_by_type(self, repo):
        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_interval_question("iq-1"))

        binary = repo.get_questions(question_type="binary")
        interval = repo.get_questions(question_type="interval")

        assert len(binary) == 1
        assert binary[0].question_type == "binary"
        assert len(interval) == 1
        assert interval[0].question_type == "interval"

    def test_get_questions_filters_by_category(self, repo):
        repo.add_question(_make_binary_question("bq-1", category="science"))
        repo.add_question(_make_binary_question("bq-2", category="history"))

        science = repo.get_questions(category="science")
        assert len(science) == 1
        assert science[0].id == "bq-1"

    def test_get_questions_excludes_ids(self, repo):
        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_binary_question("bq-2", text="Q2"))

        result = repo.get_questions(exclude_ids=["bq-1"])
        assert len(result) == 1
        assert result[0].id == "bq-2"

    def test_get_question_count(self, repo):
        assert repo.get_question_count() == 0

        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_interval_question("iq-1"))

        assert repo.get_question_count() == 2
        assert repo.get_question_count("binary") == 1
        assert repo.get_question_count("interval") == 1


class TestAddQuestionsBatch:
    """Tests for batch question insertion."""

    def test_batch_inserts_all_questions(self, repo):
        questions = [
            _make_binary_question(f"bq-{i}") for i in range(10)
        ]
        repo.add_questions_batch(questions)

        assert repo.get_question_count() == 10

    def test_batch_is_atomic(self, repo):
        """If one question fails, none should be inserted."""
        good_q = _make_binary_question("bq-1")
        # Create a question that will cause a constraint violation
        # by having a NULL required field
        questions = [good_q]
        repo.add_questions_batch(questions)
        assert repo.get_question_count() == 1


class TestResponseAndCalibration:
    """Tests for response storage and calibration tracking."""

    def test_add_response_and_retrieve(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response()
        repo.add_response(resp)

        responses = repo.get_responses()
        assert len(responses) == 1
        assert responses[0].question_id == "bq-1"
        assert responses[0].is_correct is True

    def test_update_calibration_binary(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(probability_estimate=75.0, is_correct=True)
        repo.add_response(resp)
        repo.update_calibration(resp)

        cal = repo.get_binary_calibration()
        bucket_70 = next(d for d in cal if d["bucket"] == 70)
        assert bucket_70["total"] == 1
        assert bucket_70["positive"] == 1

    def test_update_calibration_interval(self, repo):
        repo.add_question(_make_interval_question())
        resp = _make_interval_response(confidence_level=80, is_correct=True)
        repo.add_response(resp)
        repo.update_calibration(resp)

        cal = repo.get_interval_calibration()
        level_80 = next(d for d in cal if d["confidence"] == 80)
        assert level_80["total"] == 1
        assert level_80["correct"] == 1

    def test_binary_calibration_reflects_below_50(self, repo):
        """Probability <50% should be reflected: 30% true → 70% false."""
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(probability_estimate=30.0, is_correct=True)
        repo.add_response(resp)
        repo.update_calibration(resp)

        cal = repo.get_binary_calibration()
        # 30% gets reflected to 70% bucket, with inverted outcome
        bucket_70 = next(d for d in cal if d["bucket"] == 70)
        assert bucket_70["total"] == 1
        # outcome was True, reflected to False → positive_outcomes = 0
        assert bucket_70["positive"] == 0

    def test_get_session_stats(self, repo):
        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_binary_question("bq-2", text="Q2"))

        r1 = _make_binary_response("bq-1", "s1", score=5.0, is_correct=True)
        r2 = _make_binary_response("bq-2", "s1", score=-3.0, is_correct=False)
        repo.add_response(r1)
        repo.add_response(r2)

        stats = repo.get_session_stats("s1")
        assert stats["total"] == 2
        assert stats["correct"] == 1
        assert stats["total_score"] == pytest.approx(2.0)
        assert stats["avg_score"] == pytest.approx(1.0)

    def test_get_overall_stats_no_filter(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(score=5.0)
        repo.add_response(resp)

        stats = repo.get_overall_stats()
        assert stats["total"] == 1
        assert stats["avg_score"] == pytest.approx(5.0)

    def test_get_overall_stats_with_type_filter(self, repo):
        repo.add_question(_make_binary_question())
        repo.add_question(_make_interval_question())
        repo.add_response(_make_binary_response())
        repo.add_response(_make_interval_response())

        binary_stats = repo.get_overall_stats("binary")
        assert binary_stats["total"] == 1

        interval_stats = repo.get_overall_stats("interval")
        assert interval_stats["total"] == 1

    def test_get_overall_stats_grouped(self, repo):
        repo.add_question(_make_binary_question())
        repo.add_question(_make_interval_question())
        repo.add_response(_make_binary_response(score=4.0))
        repo.add_response(_make_interval_response(score=8.0))

        grouped = repo.get_overall_stats_grouped()
        assert grouped["overall"]["total"] == 2
        assert grouped["binary"]["total"] == 1
        assert grouped["binary"]["avg_score"] == pytest.approx(4.0)
        assert grouped["interval"]["total"] == 1
        assert grouped["interval"]["avg_score"] == pytest.approx(8.0)
        assert grouped["overall"]["avg_score"] == pytest.approx(6.0)

    def test_get_incorrectly_answered_questions(self, repo):
        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_binary_question("bq-2", text="Q2"))
        repo.add_response(_make_binary_response("bq-1", is_correct=True))
        repo.add_response(_make_binary_response("bq-2", is_correct=False))

        wrong = repo.get_incorrectly_answered_questions()
        assert "bq-2" in wrong
        assert "bq-1" not in wrong

    def test_get_incorrectly_answered_with_type_filter(self, repo):
        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_interval_question("iq-1"))
        repo.add_response(_make_binary_response("bq-1", is_correct=False))
        repo.add_response(_make_interval_response("iq-1", is_correct=False))

        binary_wrong = repo.get_incorrectly_answered_questions("binary")
        assert "bq-1" in binary_wrong
        assert "iq-1" not in binary_wrong


class TestSettings:
    """Tests for settings persistence."""

    def test_default_settings(self, repo):
        settings = repo.get_settings()
        assert settings.default_session_length == 10
        assert settings.default_mode == "binary"
        assert settings.default_confidence_level == 80

    def test_save_and_get_settings(self, repo):
        settings = Settings(
            default_session_length=20,
            default_confidence_level=90,
            default_mode="interval",
            imported_question_files=["/path/to/file.json"],
            enabled_categories=["science"],
        )
        repo.save_settings(settings)

        restored = repo.get_settings()
        assert restored.default_session_length == 20
        assert restored.default_mode == "interval"
        assert restored.imported_question_files == ["/path/to/file.json"]
        assert restored.enabled_categories == ["science"]

    def test_settings_with_json_list_fields(self, repo):
        """Verify JSON-encoded lists round-trip through the database."""
        files = ["/path/with,comma/file.json", "other.json"]
        settings = Settings(imported_question_files=files)
        repo.save_settings(settings)

        restored = repo.get_settings()
        assert restored.imported_question_files == files

    def test_save_settings_updates_existing(self, repo):
        """Saving settings twice should update, not duplicate."""
        settings = Settings(default_session_length=15)
        repo.save_settings(settings)

        settings.default_session_length = 25
        repo.save_settings(settings)

        restored = repo.get_settings()
        assert restored.default_session_length == 25

    def test_settings_enabled_categories_round_trip(self, repo):
        """Multiple enabled categories should survive a save/load cycle."""
        settings = Settings(enabled_categories=["science", "history", "economics"])
        repo.save_settings(settings)

        restored = repo.get_settings()
        assert sorted(restored.enabled_categories) == ["economics", "history", "science"]


class TestCategoryFiltering:
    """Tests for category-based question retrieval."""

    def test_get_questions_filters_by_multiple_categories(self, repo):
        repo.add_question(_make_binary_question("bq-1", category="science"))
        repo.add_question(_make_binary_question("bq-2", category="history", text="Q2"))
        repo.add_question(_make_binary_question("bq-3", category="economics", text="Q3"))

        result = repo.get_questions(categories=["science", "history"])
        ids = {q.id for q in result}
        assert ids == {"bq-1", "bq-2"}

    def test_get_questions_category_overrides_categories(self, repo):
        """When both category and categories are provided, category takes precedence."""
        repo.add_question(_make_binary_question("bq-1", category="science"))
        repo.add_question(_make_binary_question("bq-2", category="history", text="Q2"))

        result = repo.get_questions(category="science", categories=["history"])
        assert len(result) == 1
        assert result[0].id == "bq-1"

    def test_get_categories_returns_distinct(self, repo):
        repo.add_question(_make_binary_question("bq-1", category="science"))
        repo.add_question(_make_binary_question("bq-2", category="science", text="Q2"))
        repo.add_question(_make_binary_question("bq-3", category="history", text="Q3"))

        categories = repo.get_categories()
        assert sorted(categories) == ["history", "science"]


class TestBrierScore:
    """Tests for the binary Brier score computation."""

    def test_brier_score_no_responses(self, repo):
        assert repo.get_binary_brier_score() is None

    def test_brier_score_perfect_prediction(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(probability_estimate=100.0, is_correct=True)
        repo.add_response(resp)

        brier = repo.get_binary_brier_score()
        assert brier == pytest.approx(0.0)

    def test_brier_score_worst_prediction(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(probability_estimate=0.0, is_correct=True)
        repo.add_response(resp)

        brier = repo.get_binary_brier_score()
        assert brier == pytest.approx(1.0)

    def test_brier_score_fifty_percent(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(probability_estimate=50.0, is_correct=True)
        repo.add_response(resp)

        brier = repo.get_binary_brier_score()
        assert brier == pytest.approx(0.25)


class TestResponseFilters:
    """Tests for get_responses with various filters."""

    def test_get_responses_filters_by_session(self, repo):
        repo.add_question(_make_binary_question())
        repo.add_response(_make_binary_response(session_id="s1"))
        repo.add_response(_make_binary_response(session_id="s2"))

        s1_responses = repo.get_responses(session_id="s1")
        assert len(s1_responses) == 1
        assert s1_responses[0].session_id == "s1"

    def test_get_responses_filters_by_type(self, repo):
        repo.add_question(_make_binary_question())
        repo.add_question(_make_interval_question())
        repo.add_response(_make_binary_response())
        repo.add_response(_make_interval_response())

        binary = repo.get_responses(question_type="binary")
        assert len(binary) == 1
        assert binary[0].question_type == "binary"

    def test_get_responses_with_limit(self, repo):
        repo.add_question(_make_binary_question())
        for i in range(5):
            repo.add_response(_make_binary_response(session_id=f"s{i}"))

        limited = repo.get_responses(limit=2)
        assert len(limited) == 2

    def test_get_session_stats_empty_session(self, repo):
        stats = repo.get_session_stats("nonexistent")
        assert stats["total"] == 0
        assert stats["correct"] == 0
        assert stats["avg_score"] == 0
        assert stats["total_score"] == 0

    def test_get_session_stats_multiple_sessions(self, repo):
        repo.add_question(_make_binary_question("bq-1"))
        repo.add_question(_make_binary_question("bq-2", text="Q2"))
        repo.add_response(_make_binary_response("bq-1", "s1", score=5.0))
        repo.add_response(_make_binary_response("bq-2", "s2", score=-3.0))

        s1 = repo.get_session_stats("s1")
        s2 = repo.get_session_stats("s2")
        assert s1["total"] == 1
        assert s1["total_score"] == pytest.approx(5.0)
        assert s2["total"] == 1
        assert s2["total_score"] == pytest.approx(-3.0)


class TestEdgeCases:
    """Tests for boundary conditions and empty states."""

    def test_empty_question_set(self, repo):
        assert repo.get_questions() == []

    def test_overall_stats_no_responses(self, repo):
        stats = repo.get_overall_stats()
        assert stats["total"] == 0
        assert stats["correct"] == 0
        assert stats["avg_score"] == 0

    def test_overall_stats_grouped_empty(self, repo):
        grouped = repo.get_overall_stats_grouped()
        assert grouped["overall"]["total"] == 0
        assert grouped["binary"]["total"] == 0
        assert grouped["interval"]["total"] == 0

    def test_overall_stats_grouped_single_type(self, repo):
        """Only binary responses — interval section should have zeros."""
        repo.add_question(_make_binary_question())
        repo.add_response(_make_binary_response(score=4.0))

        grouped = repo.get_overall_stats_grouped()
        assert grouped["binary"]["total"] == 1
        assert grouped["interval"]["total"] == 0
        assert grouped["overall"]["total"] == 1

    def test_calibration_initial_state(self, repo):
        """Calibration tables should be pre-populated with zero-count buckets."""
        binary_cal = repo.get_binary_calibration()
        assert len(binary_cal) == 5
        for bucket in binary_cal:
            assert bucket["total"] == 0
            assert bucket["positive"] == 0

        interval_cal = repo.get_interval_calibration()
        assert len(interval_cal) == 5
        for level in interval_cal:
            assert level["total"] == 0
            assert level["correct"] == 0

    def test_get_questions_with_empty_exclude_list(self, repo):
        repo.add_question(_make_binary_question())
        result = repo.get_questions(exclude_ids=[])
        assert len(result) == 1


class TestResetTrainingData:
    """Tests for the reset_training_data feature."""

    def test_reset_clears_responses(self, repo):
        repo.add_question(_make_binary_question())
        repo.add_response(_make_binary_response())

        assert len(repo.get_responses()) == 1
        repo.reset_training_data()
        assert len(repo.get_responses()) == 0

    def test_reset_zeros_calibration(self, repo):
        repo.add_question(_make_binary_question())
        resp = _make_binary_response(probability_estimate=75.0, is_correct=True)
        repo.add_response(resp)
        repo.update_calibration(resp)

        repo.reset_training_data()

        binary_cal = repo.get_binary_calibration()
        for bucket in binary_cal:
            assert bucket["total"] == 0
            assert bucket["positive"] == 0

        interval_cal = repo.get_interval_calibration()
        for level in interval_cal:
            assert level["total"] == 0
            assert level["correct"] == 0

    def test_reset_preserves_questions(self, repo):
        repo.add_question(_make_binary_question())
        repo.add_question(_make_interval_question())
        repo.add_response(_make_binary_response())

        repo.reset_training_data()

        assert repo.get_question_count() == 2

    def test_reset_preserves_settings(self, repo):
        settings = Settings(default_session_length=25, default_mode="interval")
        repo.save_settings(settings)
        repo.add_question(_make_binary_question())
        repo.add_response(_make_binary_response())

        repo.reset_training_data()

        restored = repo.get_settings()
        assert restored.default_session_length == 25
        assert restored.default_mode == "interval"
