"""SQLite database schema."""

import sqlite3
from pathlib import Path

SCHEMA = """
-- Questions (bundled + imported)
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    question_type TEXT NOT NULL CHECK (question_type IN ('binary', 'interval')),
    answer REAL NOT NULL,
    binary_answer INTEGER,
    units TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    log_scale INTEGER DEFAULT 0,
    answer_range_min REAL DEFAULT 0,
    answer_range_max REAL DEFAULT 100,
    source TEXT DEFAULT 'bundled'
);

-- User responses
CREATE TABLE IF NOT EXISTS responses (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    probability_estimate REAL,
    lower_bound REAL,
    upper_bound REAL,
    confidence_level INTEGER,
    is_correct INTEGER NOT NULL,
    score REAL NOT NULL,
    question_type TEXT NOT NULL,
    true_answer REAL NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- Interval calibration tracking
CREATE TABLE IF NOT EXISTS interval_calibration (
    confidence_level INTEGER PRIMARY KEY,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0
);

-- Binary calibration tracking (buckets: 50, 60, 70, 80, 90)
CREATE TABLE IF NOT EXISTS binary_calibration (
    bucket_start INTEGER PRIMARY KEY,
    total_predictions INTEGER DEFAULT 0,
    positive_outcomes INTEGER DEFAULT 0
);

-- Settings
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    default_session_length INTEGER DEFAULT 10,
    default_confidence_level INTEGER DEFAULT 80,
    default_mode TEXT DEFAULT 'binary',
    imported_question_files TEXT DEFAULT '',
    enabled_categories TEXT DEFAULT 'astronomy,biology,physics_chemistry,computer_science,global_health,history,geography,economics,ea_global_dev,cognitive_science,energy_environment'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_responses_session ON responses(session_id);
CREATE INDEX IF NOT EXISTS idx_responses_question ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_responses_type ON responses(question_type);
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type);
"""


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize the database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    # Initialize default settings if not exists
    cursor = conn.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        conn.execute(
            """INSERT INTO settings (id, default_session_length, default_confidence_level,
               default_mode, imported_question_files, enabled_categories)
               VALUES (1, 10, 80, 'binary', '', 'astronomy,biology,physics_chemistry,computer_science,global_health,history,geography,economics,ea_global_dev,cognitive_science,energy_environment')"""
        )

    # Initialize calibration buckets
    for level in [50, 60, 70, 80, 90]:
        conn.execute(
            "INSERT OR IGNORE INTO interval_calibration (confidence_level, total_predictions, correct_predictions) VALUES (?, 0, 0)",
            (level,),
        )
        conn.execute(
            "INSERT OR IGNORE INTO binary_calibration (bucket_start, total_predictions, positive_outcomes) VALUES (?, 0, 0)",
            (level,),
        )

    conn.commit()
    return conn
