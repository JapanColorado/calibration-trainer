# Calibration Trainer

A terminal-based application for improving your probabilistic calibration skills through practice with binary and confidence interval questions.

## What is Calibration?

Calibration is the ability to accurately assess the probability of being correct. A well-calibrated person who says they're 80% confident about something should be right about 80% of the time.

This app helps you practice and track your calibration through two types of questions:

- **Binary Questions**: Estimate the probability (0-100%) that a statement is true
- **Interval Questions**: Provide a confidence interval that should contain the true answer X% of the time

## Installation

```bash
pip install -e .
```

## Usage

Run the application:

```bash
calibration-trainer
```

### Navigation

- **Dashboard**: Press `T` to train, `S` for stats, `O` for settings, `Q` to quit
- **Training**: Answer questions, press `Escape` or `Ctrl+C` to end session early
- **Stats**: View your calibration charts showing predicted vs actual rates

### Training Modes

#### Binary Mode
You'll see a statement and estimate the probability (0-100%) that it's true:
- 50% means you're completely uncertain
- Higher values mean more confident it's true
- Lower values mean more confident it's false

#### Interval Mode
You'll provide a confidence interval for a numerical answer:
- Choose a confidence level (50%, 60%, 70%, 80%, 90%)
- Provide lower and upper bounds
- If you use 80% confidence, about 80% of your intervals should contain the true answer

## Scoring

### Binary (Log Scoring)
- 50% always scores 0
- Correct predictions with high confidence score positive (up to +10)
- Incorrect predictions with high confidence score negative

### Interval (Greenberg Scoring)
- Hitting the interval with a tight range scores high
- Missing the interval penalizes based on distance and confidence level
- Higher confidence means higher penalties for misses

## Importing Questions

You can import your own questions from a JSON file:

```json
{
  "questions": [
    {
      "text": "What year was the Eiffel Tower completed?",
      "question_type": "interval",
      "answer": 1889,
      "units": "",
      "category": "history",
      "log_scale": false,
      "answer_range_min": 1800,
      "answer_range_max": 1950
    },
    {
      "text": "Is the Great Wall of China visible from space?",
      "question_type": "binary",
      "answer": 0,
      "binary_answer": false,
      "units": "",
      "category": "trivia"
    }
  ]
}
```

Required fields:
- `text`: The question text
- `question_type`: "binary" or "interval"
- `answer`: The correct answer (numeric value or 0/1 for binary)
- `binary_answer`: For binary questions, `true` or `false`

Optional fields:
- `units`: Display units for interval questions
- `category`: Question category for filtering
- `log_scale`: Use logarithmic scoring (for quantities spanning orders of magnitude)
- `answer_range_min`, `answer_range_max`: Plausible range for the answer

## Data Storage

Your training data is stored locally using SQLite in your user data directory:
- Linux: `~/.local/share/calibration-trainer/`
- macOS: `~/Library/Application Support/calibration-trainer/`
- Windows: `C:\Users\<user>\AppData\Local\calibration-trainer\`

## Development

This project uses [pixi](https://pixi.sh) as its package manager.

```bash
# Install all environments
pixi install --all

# Run the app
pixi run start

# Run tests
pixi run test

# Run a single test file
pixi run -e dev pytest tests/test_scoring.py

# Open a dev shell
pixi shell -e dev
```

## License

MIT
