"""Settings screen for user preferences."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from calibration_trainer.database import Repository
from calibration_trainer.models import Settings
from calibration_trainer.questions.loader import load_questions_from_file, validate_question_file
from calibration_trainer.screens.modals import ResetConfirmModal


class SettingsScreen(Screen):
    """Screen for managing user settings."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("b", "back", "Back"),
    ]

    def __init__(self, repo: Repository) -> None:
        super().__init__()
        self.repo = repo
        self.settings = repo.get_settings()

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Vertical(
                Label("Settings", id="settings-title"),
                Label("Default Session Length:"),
                Select(
                    [(f"{n} questions", n) for n in [5, 10, 15, 20, 25]],
                    value=self.settings.default_session_length,
                    id="length-select",
                ),
                Label("Default Mode:"),
                Select(
                    [("Binary", "binary"), ("Interval", "interval")],
                    value=self.settings.default_mode,
                    id="mode-select",
                ),
                Label("Default Confidence Level:"),
                Select(
                    [(f"{n}%", n) for n in [50, 60, 70, 80, 90]],
                    value=self.settings.default_confidence_level,
                    id="confidence-select",
                ),
                Static("─" * 40, classes="separator"),
                Label("Data Management"),
                Horizontal(
                    Input(placeholder="/path/to/questions.json", id="import-path"),
                    Button("Import", id="import-btn", variant="primary"),
                    id="import-row",
                ),
                Static("", id="import-status"),
                Horizontal(
                    Button("Reset Training Data", id="reset-btn", variant="error"),
                    Static("Clears all responses and calibration data", id="reset-description"),
                    id="reset-row",
                ),
                Horizontal(
                    Button("Save", id="save-btn", variant="primary"),
                    Button("Back [B]", id="back-btn", variant="default"),
                    id="settings-buttons",
                ),
                id="settings-content",
            ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "import-btn":
            self._import_questions()
        elif event.button.id == "reset-btn":
            self._confirm_reset()

    def _save_settings(self, notify: bool = True) -> None:
        """Save current settings."""
        length_select = self.query_one("#length-select", Select)
        mode_select = self.query_one("#mode-select", Select)
        confidence_select = self.query_one("#confidence-select", Select)

        self.settings.default_session_length = (
            length_select.value if length_select.value != Select.BLANK else 10
        )
        self.settings.default_mode = (
            mode_select.value if mode_select.value != Select.BLANK else "binary"
        )
        self.settings.default_confidence_level = (
            confidence_select.value if confidence_select.value != Select.BLANK else 80
        )

        self.repo.save_settings(self.settings)
        if notify:
            self.notify("Settings saved")

    def _import_questions(self) -> None:
        """Import questions from a file."""
        import_input = self.query_one("#import-path", Input)
        status = self.query_one("#import-status", Static)

        file_path = import_input.value.strip()
        if not file_path:
            status.update("Please enter a file path")
            return

        path = Path(file_path).expanduser()

        # Validate first
        is_valid, message = validate_question_file(path)
        if not is_valid:
            status.update(f"Error: {message}")
            return

        try:
            questions = load_questions_from_file(path)
            self.repo.add_questions_batch(questions)

            # Track imported file
            if str(path) not in self.settings.imported_question_files:
                self.settings.imported_question_files.append(str(path))
                self.repo.save_settings(self.settings)

            status.update(f"Successfully imported {len(questions)} questions")
            import_input.value = ""
            self.notify(f"Imported {len(questions)} questions")

        except Exception as e:
            status.update(f"Error importing: {e}")

    def _confirm_reset(self) -> None:
        """Show confirmation modal before resetting training data."""
        def on_confirm(result: bool) -> None:
            if result:
                self.repo.reset_training_data()
                self.notify("Training data has been reset")

        self.app.push_screen(ResetConfirmModal(), on_confirm)

    def action_back(self) -> None:
        """Go back to dashboard, auto-saving settings."""
        self._save_settings(notify=False)
        self.app.pop_screen()
