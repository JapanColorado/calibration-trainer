"""Main Textual application for the calibration trainer."""

from pathlib import Path

from textual.app import App

from calibration_trainer.database import Repository
from calibration_trainer.questions import load_bundled_questions
from calibration_trainer.screens import DashboardScreen, SettingsScreen, StatsScreen, TrainingScreen
from calibration_trainer.screens.modals import TrainingSetupModal


class CalibrationApp(App):
    """Main application for calibration training."""

    TITLE = "Calibration Trainer"
    CSS_PATH = "styles/app.tcss"

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.repo = Repository(db_path=db_path)
        self._load_bundled_questions()

    def _load_bundled_questions(self) -> None:
        """Load bundled questions into the database.

        Uses INSERT OR REPLACE so this is idempotent — new questions are
        added and existing ones (matched by content-hash ID) are updated.
        """
        questions = load_bundled_questions()
        self.repo.add_questions_batch(questions)

    def on_unmount(self) -> None:
        """Clean up resources."""
        self.repo.close()

    def on_mount(self) -> None:
        """Initialize the application."""
        stats = self.repo.get_overall_stats()
        self.push_screen(DashboardScreen(stats))

    def action_start_training(self) -> None:
        """Open the training setup modal."""
        settings = self.repo.get_settings()
        categories = self.repo.get_categories()

        def on_setup_complete(result: dict | None) -> None:
            if result is not None:
                training_screen = TrainingScreen(
                    repo=self.repo,
                    mode=result["mode"],
                    session_length=result["length"],
                    confidence_level=result["confidence"],
                    question_filter=result["filter"],
                    categories=result.get("categories"),
                )
                self.push_screen(training_screen)

        modal = TrainingSetupModal(
            default_mode=settings.default_mode,
            default_length=settings.default_session_length,
            default_confidence=settings.default_confidence_level,
            categories=categories,
        )
        self.push_screen(modal, on_setup_complete)

    def action_show_stats(self) -> None:
        """Show the statistics screen."""
        self.push_screen(StatsScreen(self.repo))

    def action_show_settings(self) -> None:
        """Show the settings screen."""
        self.push_screen(SettingsScreen(self.repo))

    def on_screen_resume(self) -> None:
        """Called when returning to a screen."""
        current = self.screen
        if isinstance(current, DashboardScreen):
            stats = self.repo.get_overall_stats()
            current.update_stats(stats)
