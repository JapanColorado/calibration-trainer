"""Textual pilot tests for screen navigation."""

import pytest
from pathlib import Path

from textual.widgets import Static

from calibration_trainer.app import CalibrationApp
from calibration_trainer.screens.dashboard import DashboardScreen
from calibration_trainer.screens.settings import SettingsScreen
from calibration_trainer.screens.stats import StatsScreen
from calibration_trainer.screens.modals import TrainingSetupModal, ResetConfirmModal

# Resolve the CSS path from the actual package location
_CSS_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "calibration_trainer"
    / "styles"
    / "app.tcss"
)


class ScreenTestApp(CalibrationApp):
    """App subclass with CSS path resolved for tests."""

    CSS_PATH = str(_CSS_PATH)


@pytest.fixture
def app(tmp_path):
    return ScreenTestApp(db_path=tmp_path / "test.db")


async def test_app_starts_with_dashboard(app):
    async with app.run_test() as pilot:
        assert isinstance(app.screen, DashboardScreen)


async def test_press_t_opens_training_setup(app):
    async with app.run_test() as pilot:
        await pilot.press("t")
        assert isinstance(app.screen, TrainingSetupModal)


async def test_press_s_opens_stats(app):
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, StatsScreen)


async def test_press_o_opens_settings(app):
    async with app.run_test() as pilot:
        await pilot.press("o")
        assert isinstance(app.screen, SettingsScreen)


async def test_press_q_quits(app):
    async with app.run_test() as pilot:
        await pilot.press("q")
        assert app.return_code is not None or not app.is_running


async def test_dashboard_shows_stats_summary(app):
    async with app.run_test() as pilot:
        widget = app.screen.query_one("#stats-summary", Static)
        assert "No training sessions" in str(widget.render())


async def test_stats_screen_renders_empty(app):
    """Stats screen should not crash with no data."""
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, StatsScreen)


async def test_settings_screen_has_reset_button(app):
    """Settings screen should contain the reset training data button."""
    async with app.run_test() as pilot:
        await pilot.press("o")
        assert isinstance(app.screen, SettingsScreen)
        button = app.screen.query_one("#reset-btn")
        assert button is not None
