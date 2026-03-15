"""Data access layer for the calibration trainer."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from platformdirs import user_data_dir

from calibration_trainer.database.schema import init_database
from calibration_trainer.models import Question, Response, Settings


class Repository:
    """Repository for all database operations."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            data_dir = Path(user_data_dir("calibration-trainer", "calibration-trainer"))
            db_path = data_dir / "calibration.db"
        self.db_path = db_path
        self.conn = init_database(db_path)

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    @contextmanager
    def transaction(self):
        """Context manager for batching operations in a single transaction."""
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # Questions
    def add_question(self, question: Question) -> None:
        """Add a question to the database."""
        self.conn.execute(
            """INSERT OR REPLACE INTO questions
               (id, text, question_type, answer, binary_answer, units, category,
                log_scale, answer_range_min, answer_range_max, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                question.id,
                question.text,
                question.question_type,
                question.answer,
                question.binary_answer,
                question.units,
                question.category,
                question.log_scale,
                question.answer_range_min,
                question.answer_range_max,
                question.source,
            ),
        )
        self.conn.commit()

    def add_questions_batch(self, questions: list[Question]) -> None:
        """Add multiple questions in a single transaction."""
        with self.transaction():
            for question in questions:
                self.conn.execute(
                    """INSERT OR REPLACE INTO questions
                       (id, text, question_type, answer, binary_answer, units, category,
                        log_scale, answer_range_min, answer_range_max, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        question.id,
                        question.text,
                        question.question_type,
                        question.answer,
                        question.binary_answer,
                        question.units,
                        question.category,
                        question.log_scale,
                        question.answer_range_min,
                        question.answer_range_max,
                        question.source,
                    ),
                )

    def get_question(self, question_id: str) -> Question | None:
        """Get a question by ID."""
        cursor = self.conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_question(row)
        return None

    def get_questions(
        self,
        question_type: Literal["binary", "interval"] | None = None,
        category: str | None = None,
        categories: list[str] | None = None,
        exclude_ids: list[str] | None = None,
    ) -> list[Question]:
        """Get questions with optional filters.

        If both `category` (singular) and `categories` (plural) are provided,
        `category` takes precedence for backward compatibility.
        """
        query = "SELECT * FROM questions WHERE 1=1"
        params: list = []

        if question_type:
            query += " AND question_type = ?"
            params.append(question_type)

        if category:
            query += " AND category = ?"
            params.append(category)
        elif categories:
            placeholders = ",".join("?" * len(categories))
            query += f" AND category IN ({placeholders})"
            params.extend(categories)

        if exclude_ids:
            placeholders = ",".join("?" * len(exclude_ids))
            query += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_ids)

        cursor = self.conn.execute(query, params)
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def get_question_count(self, question_type: Literal["binary", "interval"] | None = None) -> int:
        """Get the count of questions."""
        if question_type:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM questions WHERE question_type = ?", (question_type,)
            )
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM questions")
        return cursor.fetchone()[0]

    def get_categories(self) -> list[str]:
        """Get all unique categories."""
        cursor = self.conn.execute("SELECT DISTINCT category FROM questions")
        return [row[0] for row in cursor.fetchall()]

    def _row_to_question(self, row: sqlite3.Row) -> Question:
        """Convert a database row to a Question object."""
        return Question.from_dict(dict(row))

    # Responses
    def add_response(self, response: Response) -> None:
        """Add a response to the database."""
        self.conn.execute(
            """INSERT INTO responses
               (id, question_id, session_id, timestamp, probability_estimate,
                lower_bound, upper_bound, confidence_level, is_correct, score,
                question_type, true_answer)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                response.id,
                response.question_id,
                response.session_id,
                response.timestamp.isoformat(),
                response.probability_estimate,
                response.lower_bound,
                response.upper_bound,
                response.confidence_level,
                response.is_correct,
                response.score,
                response.question_type,
                response.true_answer,
            ),
        )
        self.conn.commit()

    def update_calibration(self, response: Response) -> None:
        """Update calibration tracking tables based on a response."""
        if response.question_type == "binary" and response.probability_estimate is not None:
            self._update_binary_calibration(response.probability_estimate, response.is_correct)
        elif response.question_type == "interval" and response.confidence_level is not None:
            self._update_interval_calibration(response.confidence_level, response.is_correct)

    def _update_binary_calibration(self, probability: float, outcome: bool) -> None:
        """Update binary calibration tracking."""
        # Map probability to bucket (50-59 -> 50, 60-69 -> 60, etc.)
        # Probabilities below 50% are reflected (30% predicting yes = 70% predicting no)
        if probability < 50:
            probability = 100 - probability
            outcome = not outcome

        bucket = min(90, (int(probability) // 10) * 10)
        if bucket < 50:
            bucket = 50

        self.conn.execute(
            """UPDATE binary_calibration
               SET total_predictions = total_predictions + 1,
                   positive_outcomes = positive_outcomes + ?
               WHERE bucket_start = ?""",
            (1 if outcome else 0, bucket),
        )
        self.conn.commit()

    def _update_interval_calibration(self, confidence_level: int, is_correct: bool) -> None:
        """Update interval calibration tracking."""
        self.conn.execute(
            """UPDATE interval_calibration
               SET total_predictions = total_predictions + 1,
                   correct_predictions = correct_predictions + ?
               WHERE confidence_level = ?""",
            (1 if is_correct else 0, confidence_level),
        )
        self.conn.commit()

    def get_responses(
        self,
        session_id: str | None = None,
        question_type: Literal["binary", "interval"] | None = None,
        limit: int | None = None,
    ) -> list[Response]:
        """Get responses with optional filters."""
        query = "SELECT * FROM responses WHERE 1=1"
        params: list = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if question_type:
            query += " AND question_type = ?"
            params.append(question_type)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.execute(query, params)
        return [self._row_to_response(row) for row in cursor.fetchall()]

    def get_session_stats(self, session_id: str) -> dict:
        """Get statistics for a session."""
        cursor = self.conn.execute(
            """SELECT COUNT(*) as total, SUM(is_correct) as correct,
                      AVG(score) as avg_score, SUM(score) as total_score
               FROM responses WHERE session_id = ?""",
            (session_id,),
        )
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "correct": row["correct"] or 0,
            "avg_score": row["avg_score"] or 0,
            "total_score": row["total_score"] or 0,
        }

    def get_overall_stats(self, question_type: Literal["binary", "interval"] | None = None) -> dict:
        """Get overall statistics."""
        query = "SELECT COUNT(*) as total, SUM(is_correct) as correct, AVG(score) as avg_score FROM responses"
        params: list = []

        if question_type:
            query += " WHERE question_type = ?"
            params.append(question_type)

        cursor = self.conn.execute(query, params)
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "correct": row["correct"] or 0,
            "avg_score": row["avg_score"] or 0,
        }

    def get_overall_stats_grouped(self) -> dict[str, dict]:
        """Get overall statistics grouped by question type in a single query.

        Returns a dict with keys 'overall', 'binary', and 'interval', each
        containing 'total', 'correct', 'avg_score', and 'total_score'.
        """
        cursor = self.conn.execute(
            """SELECT question_type,
                      COUNT(*) as total,
                      SUM(is_correct) as correct,
                      AVG(score) as avg_score,
                      SUM(score) as total_score
               FROM responses
               GROUP BY question_type"""
        )
        empty = {"total": 0, "correct": 0, "avg_score": 0, "total_score": 0}
        result = {
            "overall": dict(empty),
            "binary": dict(empty),
            "interval": dict(empty),
        }
        total_count = 0
        total_correct = 0
        total_score_sum = 0.0
        total_points = 0.0
        for row in cursor.fetchall():
            qtype = row["question_type"]
            count = row["total"] or 0
            correct = row["correct"] or 0
            avg = row["avg_score"] or 0
            points = row["total_score"] or 0
            if qtype in result:
                result[qtype] = {
                    "total": count,
                    "correct": correct,
                    "avg_score": avg,
                    "total_score": points,
                }
            total_count += count
            total_correct += correct
            total_score_sum += avg * count
            total_points += points
        result["overall"] = {
            "total": total_count,
            "correct": total_correct,
            "avg_score": total_score_sum / total_count if total_count > 0 else 0,
            "total_score": total_points,
        }
        return result

    def get_binary_brier_score(self) -> float | None:
        """Compute Brier score for binary questions.

        Brier score = mean of (forecast - outcome)², where forecast is the
        probability estimate (0-1) and outcome is 0 or 1. Lower is better;
        0 = perfect, 0.25 = random guessing at 50%.

        Returns None if there are no binary responses.
        """
        cursor = self.conn.execute(
            """SELECT AVG(
                   (probability_estimate / 100.0 - CAST(is_correct AS REAL))
                   * (probability_estimate / 100.0 - CAST(is_correct AS REAL))
               ) as brier
               FROM responses
               WHERE question_type = 'binary'
                 AND probability_estimate IS NOT NULL"""
        )
        row = cursor.fetchone()
        return row["brier"] if row and row["brier"] is not None else None

    def _row_to_response(self, row: sqlite3.Row) -> Response:
        """Convert a database row to a Response object."""
        from datetime import datetime

        return Response(
            id=row["id"],
            question_id=row["question_id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            probability_estimate=row["probability_estimate"],
            lower_bound=row["lower_bound"],
            upper_bound=row["upper_bound"],
            confidence_level=row["confidence_level"],
            is_correct=bool(row["is_correct"]),
            score=row["score"],
            question_type=row["question_type"],
            true_answer=row["true_answer"],
        )

    # Calibration data
    def get_binary_calibration(self) -> list[dict]:
        """Get binary calibration data."""
        cursor = self.conn.execute(
            "SELECT * FROM binary_calibration ORDER BY bucket_start"
        )
        return [
            {
                "bucket": row["bucket_start"],
                "total": row["total_predictions"],
                "positive": row["positive_outcomes"],
                "rate": row["positive_outcomes"] / row["total_predictions"]
                if row["total_predictions"] > 0
                else None,
            }
            for row in cursor.fetchall()
        ]

    def get_interval_calibration(self) -> list[dict]:
        """Get interval calibration data."""
        cursor = self.conn.execute(
            "SELECT * FROM interval_calibration ORDER BY confidence_level"
        )
        return [
            {
                "confidence": row["confidence_level"],
                "total": row["total_predictions"],
                "correct": row["correct_predictions"],
                "rate": row["correct_predictions"] / row["total_predictions"]
                if row["total_predictions"] > 0
                else None,
            }
            for row in cursor.fetchall()
        ]

    # Settings
    def get_settings(self) -> Settings:
        """Get user settings."""
        cursor = self.conn.execute("SELECT * FROM settings WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return Settings.from_dict(dict(row))
        return Settings()

    def save_settings(self, settings: Settings) -> None:
        """Save user settings."""
        data = settings.to_dict()
        self.conn.execute(
            """UPDATE settings SET
               default_session_length = ?,
               default_confidence_level = ?,
               default_mode = ?,
               imported_question_files = ?,
               enabled_categories = ?
               WHERE id = 1""",
            (
                data["default_session_length"],
                data["default_confidence_level"],
                data["default_mode"],
                data["imported_question_files"],
                data["enabled_categories"],
            ),
        )
        self.conn.commit()

    def reset_training_data(self) -> None:
        """Clear all responses and calibration data, preserving questions and settings."""
        with self.transaction():
            self.conn.execute("DELETE FROM responses")
            self.conn.execute(
                "UPDATE binary_calibration SET total_predictions = 0, positive_outcomes = 0"
            )
            self.conn.execute(
                "UPDATE interval_calibration SET total_predictions = 0, correct_predictions = 0"
            )

    def generate_session_id(self) -> str:
        """Generate a new session ID."""
        return str(uuid4())

    def get_incorrectly_answered_questions(
        self, question_type: Literal["binary", "interval"] | None = None
    ) -> list[str]:
        """Get IDs of questions that were answered incorrectly."""
        query = """
            SELECT DISTINCT question_id FROM responses
            WHERE is_correct = 0
        """
        params: list = []
        if question_type:
            query += " AND question_type = ?"
            params.append(question_type)

        cursor = self.conn.execute(query, params)
        return [row[0] for row in cursor.fetchall()]
