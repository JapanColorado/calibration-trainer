"""Dashboard screen - main entry point."""

from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.css.query import NoMatches
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static


class DashboardScreen(Screen):
    """Main dashboard screen with navigation options."""

    BINDINGS = [
        ("t", "train", "Train"),
        ("s", "stats", "Stats"),
        ("o", "settings", "Settings"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, stats: dict | None = None) -> None:
        super().__init__()
        self.stats = stats or {}

    def on_screen_resume(self, event: ScreenResume) -> None:
        """Refresh stats when returning to dashboard from another screen."""
        stats = self.app.repo.get_overall_stats()
        self.update_stats(stats)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Middle(
            Center(
                Vertical(
                    Label("Calibration Trainer", id="title"),
                    Static("Improve your probabilistic calibration skills", id="subtitle"),
                    self._stats_widget(),
                    Button("Start Training [T]", id="train-btn", variant="primary"),
                    Button("View Statistics [S]", id="stats-btn", variant="default"),
                    Button("Settings [O]", id="settings-btn", variant="default"),
                    Button("Quit [Q]", id="quit-btn", variant="error"),
                    id="dashboard-content",
                ),
            ),
        )
        yield Footer()

    def _stats_widget(self) -> Static:
        """Create the stats summary widget."""
        total = self.stats.get("total", 0)
        if total == 0:
            return Static(
                "No training sessions yet. Start training to build your calibration!",
                id="stats-summary",
            )

        correct = self.stats.get("correct", 0)
        avg_score = self.stats.get("avg_score", 0)
        accuracy = (correct / total * 100) if total > 0 else 0

        return Static(
            f"Total Questions: {total}  |  Accuracy: {accuracy:.1f}%  |  Avg Score: {avg_score:.2f}",
            id="stats-summary",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "train-btn":
            self.action_train()
        elif event.button.id == "stats-btn":
            self.action_stats()
        elif event.button.id == "settings-btn":
            self.action_settings()
        elif event.button.id == "quit-btn":
            self.action_quit()

    def action_train(self) -> None:
        """Start training."""
        self.app.action_start_training()

    def action_stats(self) -> None:
        """View statistics."""
        self.app.action_show_stats()

    def action_settings(self) -> None:
        """Open settings."""
        self.app.action_show_settings()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def update_stats(self, stats: dict) -> None:
        """Update the displayed statistics."""
        self.stats = stats
        try:
            old_widget = self.query_one("#stats-summary", Static)
            new_widget = self._stats_widget()
            old_widget.update(new_widget.render())
        except NoMatches:
            pass
