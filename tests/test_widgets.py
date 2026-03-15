"""Unit tests for custom widgets."""

import pytest

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Input

from calibration_trainer.widgets import BinaryInput, IntervalInput


class BinaryInputApp(App):
    """Minimal app for testing BinaryInput."""

    def __init__(self, question: str = "Is the sky blue?"):
        super().__init__()
        self.question = question
        self.submitted_values: list[float] = []

    def compose(self) -> ComposeResult:
        yield Container(BinaryInput(self.question, id="binary"))

    def on_binary_input_submitted(self, event: BinaryInput.Submitted) -> None:
        self.submitted_values.append(event.probability)


class IntervalInputApp(App):
    """Minimal app for testing IntervalInput."""

    def __init__(self, question: str = "What year?", units: str = "year"):
        super().__init__()
        self.question = question
        self.units = units
        self.submitted_values: list[tuple[float, float]] = []

    def compose(self) -> ComposeResult:
        yield Container(IntervalInput(self.question, self.units, 80, id="interval"))

    def on_interval_input_submitted(self, event: IntervalInput.Submitted) -> None:
        self.submitted_values.append((event.lower, event.upper))


class TestBinaryInput:
    """Tests for the BinaryInput widget."""

    async def test_valid_submission(self):
        app = BinaryInputApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#probability-input", Input)
            input_widget.value = "75"
            await pilot.press("enter")
            assert len(app.submitted_values) == 1
            assert app.submitted_values[0] == 75.0

    async def test_quick_select_sets_value(self):
        app = BinaryInputApp()
        async with app.run_test() as pilot:
            await pilot.click("#btn-50")
            input_widget = app.query_one("#probability-input", Input)
            assert input_widget.value == "50"

    async def test_out_of_range_rejected(self):
        app = BinaryInputApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#probability-input", Input)
            input_widget.value = "150"
            await pilot.click("#submit-btn")
            assert len(app.submitted_values) == 0

    async def test_set_question_updates_display(self):
        app = BinaryInputApp()
        async with app.run_test() as pilot:
            widget = app.query_one(BinaryInput)
            widget.set_question("New question?")
            assert widget.question_text == "New question?"


class TestIntervalInput:
    """Tests for the IntervalInput widget."""

    async def test_valid_submission(self):
        app = IntervalInputApp()
        async with app.run_test() as pilot:
            lower = app.query_one("#lower-input", Input)
            upper = app.query_one("#upper-input", Input)
            lower.value = "1950"
            upper.value = "1980"
            await pilot.click("#submit-btn")
            assert len(app.submitted_values) == 1
            assert app.submitted_values[0] == (1950.0, 1980.0)

    async def test_lower_greater_than_upper_rejected(self):
        app = IntervalInputApp()
        async with app.run_test() as pilot:
            lower = app.query_one("#lower-input", Input)
            upper = app.query_one("#upper-input", Input)
            lower.value = "2000"
            upper.value = "1950"
            await pilot.click("#submit-btn")
            assert len(app.submitted_values) == 0

    async def test_enter_on_lower_focuses_upper(self):
        app = IntervalInputApp()
        async with app.run_test() as pilot:
            lower = app.query_one("#lower-input", Input)
            lower.value = "1950"
            lower.focus()
            await pilot.press("enter")
            upper = app.query_one("#upper-input", Input)
            assert upper.has_focus

    async def test_set_question_clears_inputs(self):
        app = IntervalInputApp()
        async with app.run_test() as pilot:
            lower = app.query_one("#lower-input", Input)
            lower.value = "1950"
            widget = app.query_one(IntervalInput)
            widget.set_question("New Q", "kg", 90)
            assert lower.value == ""
            assert widget.confidence_level == 90
