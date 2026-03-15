"""Modal dialogs for the calibration trainer."""

from typing import Literal

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RadioButton, RadioSet, Select, SelectionList, Static


CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    "astronomy": "Astronomy",
    "biology": "Biology",
    "cognitive_science": "Cognitive Science",
    "computer_science": "Computer Science",
    "ea_global_dev": "EA & Global Dev",
    "economics": "Economics",
    "energy_environment": "Energy & Environment",
    "geography": "Geography",
    "global_health": "Global Health",
    "history": "History",
    "physics_chemistry": "Physics & Chemistry",
}


class TrainingSetupModal(ModalScreen[dict | None]):
    """Modal for setting up a training session."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        default_mode: str = "binary",
        default_length: int = 10,
        default_confidence: int = 80,
        categories: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.default_mode = default_mode
        self.default_length = default_length
        self.default_confidence = default_confidence
        self.categories = categories or ["all"]

    def compose(self) -> ComposeResult:
        category_items = [
            (CATEGORY_DISPLAY_NAMES.get(c, c.replace("_", " ").title()), c, True)
            for c in sorted(self.categories)
            if c not in ("all", "wrong")
        ]
        yield Vertical(
            Label("Training Setup", id="modal-title"),
            Label("Mode:"),
            RadioSet(
                RadioButton("Binary (True/False)", id="mode-binary", value=self.default_mode == "binary"),
                RadioButton("Interval (Confidence Ranges)", id="mode-interval", value=self.default_mode == "interval"),
                id="mode-select",
            ),
            Label("Session Length:"),
            Select(
                [(f"{n} questions", n) for n in [5, 10, 15, 20, 25]],
                value=self.default_length,
                id="length-select",
            ),
            Label("Confidence Level:", id="confidence-label"),
            Select(
                [(f"{n}%", n) for n in [50, 60, 70, 80, 90]],
                value=self.default_confidence,
                id="confidence-select",
            ),
            Label("Question Filter:"),
            Select(
                [("All Questions", "all"), ("Previously Wrong", "wrong")],
                value="all",
                id="filter-select",
            ),
            Label("Categories:"),
            SelectionList(*category_items, id="category-select"),
            Horizontal(
                Button("Start", id="start-btn", variant="primary"),
                Button("Cancel", id="cancel-btn", variant="default"),
                id="modal-buttons",
            ),
            id="training-setup-modal",
        )

    def on_mount(self) -> None:
        """Set initial visibility of confidence selector."""
        self._update_confidence_visibility(self.default_mode == "interval")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Toggle confidence selector visibility based on mode."""
        self._update_confidence_visibility(event.index == 1)

    def _update_confidence_visibility(self, show: bool) -> None:
        """Show or hide the confidence level selector."""
        self.query_one("#confidence-label", Label).display = show
        self.query_one("#confidence-select", Select).display = show

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "start-btn":
            mode_set = self.query_one("#mode-select", RadioSet)
            mode = "interval" if mode_set.pressed_index == 1 else "binary"

            length_select = self.query_one("#length-select", Select)
            length = length_select.value if length_select.value != Select.BLANK else self.default_length

            confidence_select = self.query_one("#confidence-select", Select)
            confidence = confidence_select.value if confidence_select.value != Select.BLANK else self.default_confidence

            filter_select = self.query_one("#filter-select", Select)
            question_filter = filter_select.value if filter_select.value != Select.BLANK else "all"

            category_list = self.query_one("#category-select", SelectionList)
            selected_categories = list(category_list.selected)
            # Fall back to all categories if none selected
            if not selected_categories:
                selected_categories = None

            self.dismiss({
                "mode": mode,
                "length": length,
                "confidence": confidence,
                "filter": question_filter,
                "categories": selected_categories,
            })

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class SessionSummaryModal(ModalScreen[None]):
    """Modal showing session summary."""

    BINDINGS = [("escape", "close", "Close"), ("enter", "close", "Close")]

    def __init__(
        self,
        total: int,
        correct: int,
        avg_score: float,
        total_score: float,
    ) -> None:
        super().__init__()
        self.total = total
        self.correct = correct
        self.avg_score = avg_score
        self.total_score = total_score

    def compose(self) -> ComposeResult:
        accuracy = (self.correct / self.total * 100) if self.total > 0 else 0

        yield Vertical(
            Label("Session Complete!", id="modal-title"),
            Static(""),
            Static(f"Questions Answered: {self.total}"),
            Static(f"Correct: {self.correct} ({accuracy:.1f}%)"),
            Static(""),
            Static(f"Total Score: {self.total_score:.2f}"),
            Static(f"Average Score: {self.avg_score:.2f}"),
            Static(""),
            Button("Continue", id="continue-btn", variant="primary"),
            id="session-summary-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "continue-btn":
            self.dismiss(None)

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)


class ResetConfirmModal(ModalScreen[bool]):
    """Modal to confirm resetting all training data."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Reset Training Data", id="modal-title"),
            Static(""),
            Static("This will permanently delete:"),
            Static("  \u2022 All response history"),
            Static("  \u2022 All calibration data"),
            Static(""),
            Static("Questions and settings will be preserved."),
            Static(""),
            Horizontal(
                Button("Reset", id="confirm-btn", variant="error"),
                Button("Cancel", id="cancel-btn", variant="default"),
                id="modal-buttons",
            ),
            id="reset-confirm-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ResultModal(ModalScreen[None]):
    """Modal showing result of a question."""

    BINDINGS = [("escape", "close", "Close"), ("enter", "close", "Continue")]

    def __init__(
        self,
        is_correct: bool,
        score: float,
        true_answer: str,
        user_answer: str,
        explanation: str = "",
    ) -> None:
        super().__init__()
        self.is_correct = is_correct
        self.score = score
        self.true_answer = true_answer
        self.user_answer = user_answer
        self.explanation = explanation

    def compose(self) -> ComposeResult:
        status = "Correct!" if self.is_correct else "Incorrect"
        status_class = "correct" if self.is_correct else "incorrect"

        yield Vertical(
            Label(status, id="result-status", classes=status_class),
            Static(""),
            Static(f"Your answer: {self.user_answer}"),
            Static(f"Correct answer: {self.true_answer}"),
            Static(""),
            Static(f"Score: {self.score:+.2f}"),
            Static(self.explanation) if self.explanation else Static(""),
            Static(""),
            Button("Continue", id="continue-btn", variant="primary"),
            id="result-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "continue-btn":
            self.dismiss(None)

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)
