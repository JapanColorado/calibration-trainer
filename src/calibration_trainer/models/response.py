"""Response data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4


@dataclass
class Response:
    """Represents a user's response to a question."""

    question_id: str
    session_id: str
    question_type: Literal["binary", "interval"]
    true_answer: float
    is_correct: bool
    score: float
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    probability_estimate: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    confidence_level: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "question_id": self.question_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "probability_estimate": self.probability_estimate,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "confidence_level": self.confidence_level,
            "is_correct": self.is_correct,
            "score": self.score,
            "question_type": self.question_type,
            "true_answer": self.true_answer,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Response":
        """Create a Response from a dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data["id"],
            question_id=data["question_id"],
            session_id=data["session_id"],
            timestamp=timestamp,
            probability_estimate=data.get("probability_estimate"),
            lower_bound=data.get("lower_bound"),
            upper_bound=data.get("upper_bound"),
            confidence_level=data.get("confidence_level"),
            is_correct=data["is_correct"],
            score=data["score"],
            question_type=data["question_type"],
            true_answer=data["true_answer"],
        )
