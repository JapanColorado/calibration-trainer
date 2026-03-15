"""Question data model."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class Question:
    """Represents a calibration question."""

    id: str
    text: str
    question_type: Literal["binary", "interval"]
    answer: float
    units: str
    category: str
    log_scale: bool
    answer_range_min: float
    answer_range_max: float
    binary_answer: bool | None = None
    source: str = "bundled"

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "text": self.text,
            "question_type": self.question_type,
            "answer": self.answer,
            "binary_answer": self.binary_answer,
            "units": self.units,
            "category": self.category,
            "log_scale": self.log_scale,
            "answer_range_min": self.answer_range_min,
            "answer_range_max": self.answer_range_max,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        """Create a Question from a dictionary."""
        binary_answer = data.get("binary_answer")
        if binary_answer is not None:
            binary_answer = bool(binary_answer)

        return cls(
            id=data["id"],
            text=data["text"],
            question_type=data["question_type"],
            answer=data["answer"],
            binary_answer=binary_answer,
            units=data.get("units", ""),
            category=data.get("category", "general"),
            log_scale=bool(data.get("log_scale", False)),
            answer_range_min=data.get("answer_range_min", 0),
            answer_range_max=data.get("answer_range_max", 100),
            source=data.get("source", "bundled"),
        )
