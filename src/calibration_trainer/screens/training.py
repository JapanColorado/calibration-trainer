"""Training session screen."""

import random
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from calibration_trainer.database import Repository
from calibration_trainer.models import Question, Response
from calibration_trainer.scoring import binary_log_score, greenberg_score
from calibration_trainer.scoring.binary_log import binary_score_with_details
from calibration_trainer.screens.modals import ResultModal, SessionSummaryModal
from calibration_trainer.widgets import BinaryInput, IntervalInput


class TrainingScreen(Screen):
    """Screen for training sessions."""

    BINDINGS = [
        ("escape", "end_session", "End Session"),
        ("ctrl+c", "end_session", "End Session"),
    ]

    def __init__(
        self,
        repo: Repository,
        mode: Literal["binary", "interval"] = "binary",
        session_length: int = 10,
        confidence_level: int = 80,
        question_filter: str = "all",
        categories: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.repo = repo
        self.mode = mode
        self.session_length = session_length
        self.confidence_level = confidence_level
        self.question_filter = question_filter
        self.categories = categories

        self.session_id = repo.generate_session_id()
        self.questions: list[Question] = []
        self.current_index = 0
        self.current_question: Question | None = None
        self.responses: list[Response] = []

    def compose(self) -> ComposeResult:
        yield Header()
        binary_widget = BinaryInput(id="binary-widget")
        binary_widget.display = self.mode == "binary"
        interval_widget = IntervalInput(id="interval-widget")
        interval_widget.display = self.mode == "interval"
        yield Container(
            Vertical(
                Static("", id="progress-label"),
                Static("", id="progress-pct"),
                Static(""),
                Container(
                    binary_widget,
                    interval_widget,
                    id="question-container",
                ),
                id="training-content",
            ),
            id="training-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the training session."""
        self._load_questions()
        if self.questions:
            self._show_next_question()

    def _load_questions(self) -> None:
        """Load questions for the session."""
        if self.question_filter == "wrong":
            wrong_ids = self.repo.get_incorrectly_answered_questions(self.mode)
            if wrong_ids:
                all_questions = self.repo.get_questions(
                    question_type=self.mode, categories=self.categories
                )
                self.questions = [q for q in all_questions if q.id in wrong_ids]
            else:
                self.questions = self.repo.get_questions(
                    question_type=self.mode, categories=self.categories
                )
        else:
            self.questions = self.repo.get_questions(
                question_type=self.mode, categories=self.categories
            )

        random.shuffle(self.questions)

        if len(self.questions) > self.session_length:
            self.questions = self.questions[: self.session_length]

        if not self.questions:
            self.notify("No questions available for this configuration", severity="warning")
            self.call_later(self.app.pop_screen)
            return

    def _show_next_question(self) -> None:
        """Display the next question."""
        if self.current_index >= len(self.questions):
            self._show_session_summary()
            return

        self.current_question = self.questions[self.current_index]
        self._update_progress()

        if self.mode == "binary":
            widget = self.query_one("#binary-widget", BinaryInput)
            widget.set_question(self.current_question.text)
        else:
            widget = self.query_one("#interval-widget", IntervalInput)
            widget.set_question(
                self.current_question.text,
                self.current_question.units,
                self.confidence_level,
            )

    def _update_progress(self) -> None:
        """Update progress display."""
        pct = int(self.current_index / len(self.questions) * 100)
        self.query_one("#progress-pct", Static).update(f"{pct}%")

        label = self.query_one("#progress-label", Static)
        label.update(f"Question {self.current_index + 1} of {len(self.questions)}")

    def on_binary_input_submitted(self, event: BinaryInput.Submitted) -> None:
        """Handle binary input submission."""
        if self.current_question is None:
            return

        probability = event.probability
        outcome = self.current_question.binary_answer or False

        details = binary_score_with_details(probability, outcome)
        score = details["score"]
        is_correct = details["is_correct"]

        response = Response(
            question_id=self.current_question.id,
            session_id=self.session_id,
            question_type="binary",
            true_answer=1.0 if outcome else 0.0,
            is_correct=is_correct,
            score=score,
            probability_estimate=probability,
        )

        self.repo.add_response(response)
        self.repo.update_calibration(response)
        self.responses.append(response)

        true_str = "TRUE" if outcome else "FALSE"
        user_str = f"{probability:.0f}% probability of TRUE"

        self._show_result(is_correct, score, true_str, user_str)

    def on_interval_input_submitted(self, event: IntervalInput.Submitted) -> None:
        """Handle interval input submission."""
        if self.current_question is None:
            return

        lower = event.lower
        upper = event.upper
        true_value = self.current_question.answer

        score, is_hit = greenberg_score(
            lower=lower,
            upper=upper,
            true_value=true_value,
            confidence_level=self.confidence_level,
            range_min=self.current_question.answer_range_min,
            range_max=self.current_question.answer_range_max,
            log_scale=self.current_question.log_scale,
        )

        response = Response(
            question_id=self.current_question.id,
            session_id=self.session_id,
            question_type="interval",
            true_answer=true_value,
            is_correct=is_hit,
            score=score,
            lower_bound=lower,
            upper_bound=upper,
            confidence_level=self.confidence_level,
        )

        self.repo.add_response(response)
        self.repo.update_calibration(response)
        self.responses.append(response)

        units = self.current_question.units
        units_str = f" {units}" if units else ""
        true_str = f"{true_value:,.2f}{units_str}"
        user_str = f"[{lower:,.2f}, {upper:,.2f}]{units_str}"

        status = "Hit!" if is_hit else "Miss"
        explanation = f"Interval {status.lower()} - the true value was {'inside' if is_hit else 'outside'} your range."

        self._show_result(is_hit, score, true_str, user_str, explanation)

    def _show_result(
        self,
        is_correct: bool,
        score: float,
        true_answer: str,
        user_answer: str,
        explanation: str = "",
    ) -> None:
        """Show the result modal."""

        def on_result_closed(_: None) -> None:
            self.current_index += 1
            self._show_next_question()

        modal = ResultModal(is_correct, score, true_answer, user_answer, explanation)
        self.app.push_screen(modal, on_result_closed)

    def _show_session_summary(self) -> None:
        """Show the session summary."""
        stats = self.repo.get_session_stats(self.session_id)

        def on_summary_closed(_: None) -> None:
            self.app.pop_screen()

        modal = SessionSummaryModal(
            total=stats["total"],
            correct=stats["correct"],
            avg_score=stats["avg_score"],
            total_score=stats["total_score"],
        )
        self.app.push_screen(modal, on_summary_closed)

    def action_end_session(self) -> None:
        """End the session early."""
        if self.responses:
            self._show_session_summary()
        else:
            self.app.pop_screen()
