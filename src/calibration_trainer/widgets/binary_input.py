"""Binary probability input widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Static


class BinaryInput(Static):
    """Widget for inputting probability estimates (0-100%)."""

    class Submitted(Message):
        """Message sent when the user submits their estimate."""

        def __init__(self, probability: float) -> None:
            self.probability = probability
            super().__init__()

    def __init__(self, question_text: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.question_text = question_text

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.question_text, id="question-text"),
            Static(""),
            Label("What is your probability estimate that this is TRUE? (0-100%)"),
            Static(""),
            Horizontal(
                Input(placeholder="Enter probability", id="probability-input", restrict=r"[0-9]*\.?[0-9]*"),
                Label("%", id="percent-label"),
                id="input-row",
            ),
            Static(""),
            Horizontal(
                Button("25%", id="btn-25", variant="default"),
                Button("50%", id="btn-50", variant="default"),
                Button("75%", id="btn-75", variant="default"),
                Button("90%", id="btn-90", variant="default"),
                id="quick-buttons",
            ),
            Static(""),
            Button("Submit", id="submit-btn", variant="primary"),
            id="binary-input-container",
        )

    def on_mount(self) -> None:
        """Focus the input when mounted."""
        self.query_one("#probability-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-btn":
            self._submit()
        elif event.button.id and event.button.id.startswith("btn-"):
            value = event.button.id.replace("btn-", "")
            input_widget = self.query_one("#probability-input", Input)
            input_widget.value = value
            input_widget.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        if event.input.id == "probability-input":
            self._submit()

    def _submit(self) -> None:
        """Validate and submit the probability estimate."""
        input_widget = self.query_one("#probability-input", Input)
        try:
            value = float(input_widget.value)
            if 0 <= value <= 100:
                self.post_message(self.Submitted(value))
            else:
                input_widget.add_class("error")
                self.notify("Please enter a value between 0 and 100", severity="error")
        except ValueError:
            input_widget.add_class("error")
            self.notify("Please enter a valid number", severity="error")

    def set_question(self, question_text: str) -> None:
        """Update the question text."""
        self.question_text = question_text
        self.query_one("#question-text", Label).update(question_text)
        input_widget = self.query_one("#probability-input", Input)
        input_widget.value = ""
        input_widget.remove_class("error")
        input_widget.focus()
