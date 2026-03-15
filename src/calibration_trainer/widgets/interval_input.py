"""Interval confidence input widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Static


class IntervalInput(Static):
    """Widget for inputting confidence intervals (lower/upper bounds)."""

    class Submitted(Message):
        """Message sent when the user submits their interval."""

        def __init__(self, lower: float, upper: float) -> None:
            self.lower = lower
            self.upper = upper
            super().__init__()

    def __init__(
        self,
        question_text: str = "",
        units: str = "",
        confidence_level: int = 80,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.question_text = question_text
        self.units = units
        self.confidence_level = confidence_level

    def compose(self) -> ComposeResult:
        units_display = f" ({self.units})" if self.units else ""
        yield Vertical(
            Label(self.question_text, id="question-text"),
            Static(""),
            Label(
                f"Provide a {self.confidence_level}% confidence interval{units_display}:",
                id="instruction-label",
            ),
            Static(""),
            Horizontal(
                Vertical(
                    Label("Lower bound:"),
                    Input(placeholder="Enter lower bound", id="lower-input", restrict=r"-?[0-9]*\.?[0-9]*"),
                    id="lower-container",
                ),
                Vertical(
                    Label("Upper bound:"),
                    Input(placeholder="Enter upper bound", id="upper-input", restrict=r"-?[0-9]*\.?[0-9]*"),
                    id="upper-container",
                ),
                id="bounds-row",
            ),
            Static(""),
            Static(
                f"You should be {self.confidence_level}% confident the true answer falls within your interval.",
                id="help-text",
            ),
            Static(""),
            Button("Submit", id="submit-btn", variant="primary"),
            id="interval-input-container",
        )

    def on_mount(self) -> None:
        """Focus the lower bound input when mounted."""
        self.query_one("#lower-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-btn":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in inputs."""
        if event.input.id == "lower-input":
            self.query_one("#upper-input", Input).focus()
        elif event.input.id == "upper-input":
            self._submit()

    def _submit(self) -> None:
        """Validate and submit the interval."""
        lower_input = self.query_one("#lower-input", Input)
        upper_input = self.query_one("#upper-input", Input)

        try:
            lower = float(lower_input.value)
            upper = float(upper_input.value)

            if lower > upper:
                lower_input.add_class("error")
                upper_input.add_class("error")
                self.notify("Lower bound must be less than or equal to upper bound", severity="error")
                return

            lower_input.remove_class("error")
            upper_input.remove_class("error")
            self.post_message(self.Submitted(lower, upper))

        except ValueError:
            if not lower_input.value:
                lower_input.add_class("error")
            if not upper_input.value:
                upper_input.add_class("error")
            self.notify("Please enter valid numbers for both bounds", severity="error")

    def set_question(self, question_text: str, units: str = "", confidence_level: int = 80) -> None:
        """Update the question and parameters."""
        self.question_text = question_text
        self.units = units
        self.confidence_level = confidence_level

        self.query_one("#question-text", Label).update(question_text)

        units_display = f" ({units})" if units else ""
        self.query_one("#instruction-label", Label).update(
            f"Provide a {confidence_level}% confidence interval{units_display}:"
        )
        self.query_one("#help-text", Static).update(
            f"You should be {confidence_level}% confident the true answer falls within your interval."
        )

        lower_input = self.query_one("#lower-input", Input)
        upper_input = self.query_one("#upper-input", Input)
        lower_input.value = ""
        upper_input.value = ""
        lower_input.remove_class("error")
        upper_input.remove_class("error")
        lower_input.focus()
