# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Calibration Trainer is a terminal UI (TUI) application for practicing probabilistic calibration. Users answer binary (true/false probability) and interval (confidence range) questions, receiving scores via proper scoring rules. Built with Python's Textual framework.

## Commands

This project uses **pixi** as its package manager. All pixi config lives in `pyproject.toml` under `[tool.pixi.*]` sections. Hatchling is the build backend.

```bash
# Install all environments (default + dev)
pixi install --all

# Run the app (default environment)
pixi run start

# Run all tests (dev environment, auto-selected)
pixi run test

# Run a single test file
pixi run -e dev pytest tests/test_scoring.py

# Run a single test class or method
pixi run -e dev pytest tests/test_scoring.py::TestBinaryLogScore::test_fifty_percent_scores_zero

# Open a shell in the dev environment
pixi shell -e dev
```

### Pixi environments

- **default**: runtime deps only (textual, textual-plotext, platformdirs). Task: `start`
- **dev**: runtime + test deps (pytest, pytest-asyncio). Task: `test`

Both environments share a solve-group so dependency versions stay consistent. Tests use pytest with `asyncio_mode = "auto"`.

## Architecture

### Layers

- **App** (`app.py`): `CalibrationApp(textual.App)` — entry point. Accepts optional `db_path` parameter for testability. Owns the `Repository` instance and manages screen navigation via Textual's screen stack (`push_screen`/`pop_screen`). Loads bundled questions on first run via `add_questions_batch()`. Closes the repository connection in `on_unmount()`.
- **Screens** (`screens/`): Full-screen views composing Textual widgets. Each screen receives the `Repository` (or data from it) via constructor injection:
  - `DashboardScreen` — main menu with stats summary, keyboard shortcuts T/S/O/Q
  - `TrainingScreen` — session loop: loads questions, reuses pre-mounted input widgets (toggled via `display`), handles scoring, shows result/summary modals
  - `StatsScreen` — displays plotext bar charts for binary and interval calibration data (uses `get_overall_stats_grouped()` for a single DB round-trip)
  - `SettingsScreen` — preferences, question import, and training data reset. Uses `VerticalScroll` (not `Container`) as the outer wrapper because `Container` silently clips overflow instead of scrolling.
  - `modals.py` — `TrainingSetupModal`, `ResultModal`, `SessionSummaryModal`, `ResetConfirmModal` (all `ModalScreen` subclasses that return typed results via `dismiss()`). `TrainingSetupModal` hides the confidence selector in binary mode.
- **Widgets** (`widgets/`): Reusable input components that communicate via Textual `Message` events:
  - `BinaryInput` — probability slider/input (0-100%), posts `Submitted(probability)`
  - `IntervalInput` — lower/upper bound inputs, posts `Submitted(lower, upper)`
  - `CalibrationChart` — extends `PlotextPlot` from `textual-plotext`, renders bar charts with actual vs ideal calibration overlay
- **Models** (`models/`): Plain dataclasses (`Question`, `Response`, `Settings`) with `to_dict()`/`from_dict()` serialization. No ORM — Repository delegates row conversion to `from_dict()`. `Question.from_dict()` handles `bool()` coercion for SQLite integers (`binary_answer`, `log_scale`). `Settings` serializes list fields as JSON (with backward-compatible comma-separated parsing).
- **Database** (`database/`): SQLite via raw `sqlite3`. `schema.py` defines all tables as a single SQL string executed on init. `Repository` is the sole data access class — all queries live here. DB stored in platform-specific user data dir via `platformdirs`. Repository provides a `transaction()` context manager, `add_questions_batch()` for atomic bulk inserts, and `reset_training_data()` which zeros calibration counters (UPDATE, not DELETE) because `init_database()` pre-populates the bucket rows.
- **Scoring** (`scoring/`): Pure functions, no side effects:
  - `binary_log.py` — log scoring rule for binary questions (50% = 0, 100% correct ~ +10)
  - `greenberg.py` — simplified Greenberg scoring rule for confidence intervals (hit/miss with width penalty). Uses `SMAX * C / (width + C)` for hits rather than the original log-based formula — see module docstring for details.
  - `calibration.py` — `calculate_c()` helper that computes the C scale parameter from answer range
- **Questions** (`questions/`): `loader.py` handles loading from bundled JSON (`questions/data/bundled_questions.json`) and imported files. Supports both `{"questions": [...]}` and bare array formats. Questions without an `id` field get a deterministic hash ID (`sha256(text|type|answer)[:16]`) to prevent duplicates on re-import.

### Key Data Flow

1. `TrainingScreen` loads questions from `Repository`, shuffles, and slices to session length
2. User input comes through widget `Message` events (`BinaryInput.Submitted` / `IntervalInput.Submitted`)
3. `TrainingScreen` calls scoring functions, creates `Response` objects, persists via `Repository.add_response()`
4. `TrainingScreen` then explicitly calls `Repository.update_calibration(response)` to update calibration tracking tables — these are separate operations
5. `StatsScreen` reads calibration buckets from Repository and renders plotext charts
6. `DashboardScreen.on_screen_resume()` refreshes stats from DB whenever the user returns to it (e.g., after resetting data in settings)

### Database Schema (5 tables)

- `questions` — question bank (bundled + imported)
- `responses` — every user answer with score
- `binary_calibration` — bucketed (50-90%) prediction tracking
- `interval_calibration` — per-confidence-level hit rate tracking
- `settings` — single-row user preferences

### Scoring Algorithms

Key points:
- Binary: log scoring rule, scaled so 50% = 0 and 100% correct ~ +10
- Interval: Greenberg scoring rule with linear/log modes, parameterized by C (derived from answer range)
- Binary calibration buckets reflect probabilities < 50% (e.g., 30% true → 70% false)

## Conventions

- Textual CSS lives in `styles/app.tcss`, referenced by `CSS_PATH` in the App class. Layouts use `width: 80-90%; max-width: N` for responsive sizing.
- **Use `VerticalScroll` (not `Container`) for scrollable screens.** Textual's `Container` silently clips overflow — it does not scroll even with `overflow-y: auto` in CSS. Use `VerticalScroll` with an inner `Vertical` for centering when content may exceed the viewport.
- **Labels need `width: 100%`** to wrap long text. Without an explicit width, Textual's `Label` widget truncates instead of wrapping.
- Widget-to-screen communication uses Textual's `Message`/`post_message` pattern
- Screen results use `ModalScreen[T]` with `dismiss(value)` callbacks
- All models use `@dataclass` with `to_dict()`/`from_dict()` for serialization. `from_dict()` is the single mapping path (used by both JSON loading and DB row conversion).
- Question IDs are deterministic content hashes (SHA-256) for deduplication; questions with an explicit `id` field in JSON keep that ID
- Python >=3.10, uses `X | Y` union syntax

## Testing

Tests use pytest with `asyncio_mode = "auto"`. Test files:

- `tests/test_models.py` — model dataclass round-trips, Settings JSON/legacy format handling
- `tests/test_scoring.py` — binary log score, Greenberg score, C parameter calculation
- `tests/test_repository.py` — integration tests with `tmp_path` fixture: question CRUD, response + calibration tracking, stats queries, batch inserts, settings persistence, Brier score, category filtering, response filters, edge cases, reset feature
- `tests/test_screens.py` — Textual pilot tests for screen navigation, stats rendering, reset button presence (requires `CSS_PATH` override since tests resolve relative to subclass module)
- `tests/test_widgets.py` — isolated widget tests using minimal App subclasses that mount individual widgets
