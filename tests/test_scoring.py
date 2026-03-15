"""Tests for scoring algorithms."""

import pytest
from math import log

from calibration_trainer.scoring import binary_log_score, calculate_c, greenberg_score
from calibration_trainer.scoring.binary_log import binary_score_with_details


class TestBinaryLogScore:
    """Tests for binary log scoring."""

    def test_fifty_percent_scores_zero(self):
        """50% probability should always score 0."""
        assert binary_log_score(50, True) == pytest.approx(0, abs=0.01)
        assert binary_log_score(50, False) == pytest.approx(0, abs=0.01)

    def test_higher_confidence_correct_scores_positive(self):
        """Higher confidence in correct outcome should score positive."""
        score_70 = binary_log_score(70, True)
        score_90 = binary_log_score(90, True)
        score_99 = binary_log_score(99, True)

        assert score_70 > 0
        assert score_90 > score_70
        assert score_99 > score_90

    def test_higher_confidence_wrong_scores_negative(self):
        """Higher confidence in wrong outcome should score more negative."""
        score_70 = binary_log_score(70, False)
        score_90 = binary_log_score(90, False)

        assert score_70 < 0
        assert score_90 < score_70  # More negative

    def test_symmetric_for_true_and_false(self):
        """Score should be symmetric for predicting true vs false."""
        # 70% true, outcome true = 30% true, outcome false
        score_a = binary_log_score(70, True)
        score_b = binary_log_score(30, False)

        assert score_a == pytest.approx(score_b, abs=0.01)

    def test_max_score_near_ten(self):
        """Maximum score should be near 10."""
        score = binary_log_score(99.9, True)
        assert score > 9
        assert score < 15  # Not unreasonably high

    def test_score_with_details(self):
        """Test binary_score_with_details returns correct structure."""
        details = binary_score_with_details(75, True)

        assert "score" in details
        assert "is_correct" in details
        assert "predicted" in details
        assert "actual" in details
        assert "confidence" in details

        assert details["is_correct"] is True
        assert details["predicted"] is True
        assert details["actual"] is True
        assert details["confidence"] == 75


class TestCalculateC:
    """Tests for C parameter calculation."""

    def test_linear_scale(self):
        """Test C calculation for linear scale."""
        c = calculate_c(0, 100, log_scale=False)
        assert c == 25  # (100 - 0) / 4

        c = calculate_c(50, 150, log_scale=False)
        assert c == 25  # (150 - 50) / 4

    def test_log_scale(self):
        """Test C calculation for log scale."""
        # For range 1 to 10000 (4 orders of magnitude)
        # log_range = 4, so C = 10^1 = 10
        c = calculate_c(1, 10000, log_scale=True)
        assert c == pytest.approx(10, rel=0.01)

        # For range 1 to 1000000 (6 orders of magnitude)
        # log_range = 6, so C = 10^1.5 ≈ 31.6
        c = calculate_c(1, 1000000, log_scale=True)
        assert c == pytest.approx(31.62, rel=0.01)


class TestGreenbergScore:
    """Tests for Greenberg interval scoring."""

    def test_hit_scores_positive(self):
        """Hitting the interval should score positive."""
        score, is_hit = greenberg_score(
            lower=50,
            upper=70,
            true_value=60,
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        assert is_hit is True
        assert score > 0

    def test_miss_scores_negative(self):
        """Missing the interval should score negative."""
        score, is_hit = greenberg_score(
            lower=50,
            upper=70,
            true_value=30,
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        assert is_hit is False
        assert score < 0

    def test_tighter_interval_scores_higher(self):
        """Tighter intervals that hit should score higher."""
        score_wide, _ = greenberg_score(
            lower=20,
            upper=80,
            true_value=50,
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        score_tight, _ = greenberg_score(
            lower=40,
            upper=60,
            true_value=50,
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        assert score_tight > score_wide

    def test_larger_miss_penalized_more(self):
        """Larger misses should be penalized more heavily."""
        score_small_miss, _ = greenberg_score(
            lower=50,
            upper=70,
            true_value=75,  # Small miss
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        score_large_miss, _ = greenberg_score(
            lower=50,
            upper=70,
            true_value=95,  # Large miss
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        assert score_small_miss > score_large_miss  # Less negative

    def test_boundary_cases(self):
        """Test edge cases at interval boundaries."""
        # Exactly on lower bound
        score, is_hit = greenberg_score(
            lower=50,
            upper=70,
            true_value=50,
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )
        assert is_hit is True

        # Exactly on upper bound
        score, is_hit = greenberg_score(
            lower=50,
            upper=70,
            true_value=70,
            confidence_level=80,
            range_min=0,
            range_max=100,
            log_scale=False,
        )
        assert is_hit is True

    def test_log_scale_scoring(self):
        """Test scoring with log scale."""
        score, is_hit = greenberg_score(
            lower=1000,
            upper=10000,
            true_value=5000,
            confidence_level=80,
            range_min=100,
            range_max=100000,
            log_scale=True,
        )

        assert is_hit is True
        assert score > 0

    def test_higher_confidence_higher_penalty(self):
        """Higher confidence should mean higher penalty for misses."""
        score_50, _ = greenberg_score(
            lower=50,
            upper=70,
            true_value=30,
            confidence_level=50,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        score_90, _ = greenberg_score(
            lower=50,
            upper=70,
            true_value=30,
            confidence_level=90,
            range_min=0,
            range_max=100,
            log_scale=False,
        )

        assert score_50 > score_90  # 50% confidence miss is less bad
