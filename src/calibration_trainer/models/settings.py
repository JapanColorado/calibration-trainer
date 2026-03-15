"""Settings data model."""

import json
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Settings:
    """User preferences for the calibration trainer."""

    id: int = 1
    default_session_length: int = 10
    default_confidence_level: int = 80
    default_mode: Literal["binary", "interval"] = "binary"
    imported_question_files: list[str] = field(default_factory=list)
    enabled_categories: list[str] = field(default_factory=lambda: [
        "astronomy", "biology", "physics_chemistry", "computer_science",
        "global_health", "history", "geography", "economics",
        "ea_global_dev", "cognitive_science", "energy_environment",
    ])

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "default_session_length": self.default_session_length,
            "default_confidence_level": self.default_confidence_level,
            "default_mode": self.default_mode,
            "imported_question_files": json.dumps(self.imported_question_files),
            "enabled_categories": json.dumps(self.enabled_categories),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create Settings from a dictionary."""
        imported_files = data.get("imported_question_files", "")
        if isinstance(imported_files, list):
            pass  # Already a list
        elif isinstance(imported_files, str):
            if imported_files.startswith("["):
                imported_files = json.loads(imported_files)
            else:
                imported_files = [f for f in imported_files.split(",") if f]

        enabled_cats = data.get("enabled_categories", "astronomy,biology,physics_chemistry,computer_science,global_health,history,geography,economics,ea_global_dev,cognitive_science,energy_environment")
        if isinstance(enabled_cats, list):
            pass  # Already a list
        elif isinstance(enabled_cats, str):
            if enabled_cats.startswith("["):
                enabled_cats = json.loads(enabled_cats)
            else:
                enabled_cats = [c for c in enabled_cats.split(",") if c]

        return cls(
            id=data.get("id", 1),
            default_session_length=data.get("default_session_length", 10),
            default_confidence_level=data.get("default_confidence_level", 80),
            default_mode=data.get("default_mode", "binary"),
            imported_question_files=imported_files,
            enabled_categories=enabled_cats,
        )
