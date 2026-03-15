"""Question loading utilities."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from calibration_trainer.models import Question


def load_bundled_questions() -> list[Question]:
    """Load the bundled questions from the package data."""
    data_path = Path(__file__).parent / "data" / "bundled_questions.json"

    if not data_path.exists():
        return []

    return load_questions_from_file(data_path, source="bundled")


def load_questions_from_file(file_path: Path | str, source: str = "imported") -> list[Question]:
    """
    Load questions from a JSON file.

    Args:
        file_path: Path to the JSON file
        source: Source identifier for the questions

    Returns:
        List of Question objects
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Question file not found: {file_path}")

    with open(file_path) as f:
        data = json.load(f)

    questions = []

    # Handle both array format and object with "questions" key
    if isinstance(data, dict) and "questions" in data:
        question_list = data["questions"]
    elif isinstance(data, list):
        question_list = data
    else:
        raise ValueError("Invalid question file format")

    for item in question_list:
        # Generate deterministic ID if not present, based on content hash
        # This prevents duplicates when re-importing the same file
        if "id" not in item:
            content_key = f"{item['text']}|{item['question_type']}|{item['answer']}"
            item["id"] = hashlib.sha256(content_key.encode()).hexdigest()[:16]

        item["source"] = source

        # Set defaults
        item.setdefault("units", "")
        item.setdefault("category", "general")
        item.setdefault("log_scale", False)
        item.setdefault("answer_range_min", 0)
        item.setdefault("answer_range_max", 100)

        questions.append(Question.from_dict(item))

    return questions


def validate_question_file(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate a question file format.

    Args:
        file_path: Path to the JSON file

    Returns:
        Tuple of (is_valid, error_message)
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return False, f"File not found: {file_path}"

    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

    # Handle both formats
    if isinstance(data, dict) and "questions" in data:
        question_list = data["questions"]
    elif isinstance(data, list):
        question_list = data
    else:
        return False, "File must contain a JSON array or object with 'questions' key"

    if not question_list:
        return False, "No questions found in file"

    required_fields = {"text", "question_type", "answer"}

    for i, item in enumerate(question_list):
        if not isinstance(item, dict):
            return False, f"Question {i + 1} is not a valid object"

        missing = required_fields - set(item.keys())
        if missing:
            return False, f"Question {i + 1} missing required fields: {missing}"

        if item["question_type"] not in ("binary", "interval"):
            return False, f"Question {i + 1} has invalid question_type: {item['question_type']}"

        if item["question_type"] == "binary" and "binary_answer" not in item:
            return False, f"Question {i + 1} is binary but missing 'binary_answer' field"

    return True, f"Valid file with {len(question_list)} questions"
