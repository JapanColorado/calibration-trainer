"""Statistics screen with calibration charts."""

import math

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Rule, Static

from calibration_trainer.database import Repository
from calibration_trainer.widgets import CalibrationChart

# z-score for 90% confidence interval (two-tailed)
_Z_90 = 1.645

# Below this width, chart and table stack vertically
_NARROW_THRESHOLD = 90


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    """Compute Wilson score 90% confidence interval for a proportion.

    Returns (lower, upper) as percentages (0-100).
    Handles edge cases (n=0) by returning (0, 100).
    """
    if total == 0:
        return (0.0, 100.0)

    n = total
    p = successes / n
    z2 = _Z_90**2

    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (_Z_90 * math.sqrt(p * (1 - p) / n + z2 / (4 * n**2))) / denom

    lower = max(0.0, center - margin) * 100
    upper = min(1.0, center + margin) * 100
    return (lower, upper)


def _build_calibration_table(
    data: list[dict], chart_type: str = "binary", min_points: int = 3
) -> Table:
    """Build a Rich table showing target, actual, diff, answer count, and 90% CI.

    A vertical separator visually divides the percentage columns (Target,
    Actual, Diff) from the sample-size and CI columns.
    """
    table = Table(box=None, padding=(0, 1), expand=False)
    table.add_column("Target", style="bold", justify="right")
    table.add_column("Actual", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("\u2502", style="dim", justify="center", width=1)
    table.add_column("# Answers", justify="right")
    table.add_column("90% CI", justify="right")

    bucket_key = "bucket" if chart_type == "binary" else "confidence"
    hits_key = "positive" if chart_type == "binary" else "correct"
    sep = Text("\u2502", style="dim")

    for d in data:
        bucket = d.get(bucket_key, 0)
        total = d.get("total", 0)
        hits = d.get(hits_key, 0)
        rate = d.get("rate")

        target_text = f"{bucket}%"
        n_text = str(total)

        if total >= min_points and rate is not None:
            actual_pct = rate * 100
            deviation = actual_pct - bucket

            actual_text = f"{actual_pct:.1f}%"

            sign = "+" if deviation >= 0 else ""
            color = "green" if deviation >= 0 else "red"
            diff_text = Text(f"{sign}{deviation:.1f}", style=color)

            lo, hi = _wilson_interval(hits, total)
            ci_text = Text(f"{lo:.0f}\u2013{hi:.0f}%", style="dim")
        else:
            actual_text = Text("\u2013", style="dim")
            diff_text = Text("\u2013", style="dim")
            ci_text = Text("\u2013", style="dim")

        table.add_row(target_text, actual_text, diff_text, sep, n_text, ci_text)

    return table


_LEGEND = (
    "[green]Above zero[/] = under-confident\n"
    "[red]Below zero[/] = over-confident\n"
    "CI = Wilson score 90% interval"
)


class StatsScreen(Screen):
    """Screen for viewing calibration statistics."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("b", "back", "Back"),
    ]

    def __init__(self, repo: Repository) -> None:
        super().__init__()
        self.repo = repo

    def compose(self) -> ComposeResult:
        binary_data = self.repo.get_binary_calibration()
        interval_data = self.repo.get_interval_calibration()

        yield Header()
        yield VerticalScroll(
            Label("Calibration Statistics", id="stats-title"),
            Static(""),
            self._overall_stats_widget(),
            Static(""),
            Rule(),
            Static(""),
            Label("Binary Calibration", id="binary-section-title"),
            Horizontal(
                CalibrationChart(binary_data, chart_type="binary", id="binary-chart"),
                Vertical(
                    Static(
                        _build_calibration_table(binary_data, "binary"),
                        id="binary-table",
                    ),
                    Static(_LEGEND, classes="cal-legend"),
                    classes="cal-table-side",
                ),
                id="binary-panel",
                classes="cal-panel",
            ),
            Static(""),
            Rule(),
            Static(""),
            Label("Interval Calibration", id="interval-section-title"),
            Horizontal(
                CalibrationChart(
                    interval_data, chart_type="interval", id="interval-chart"
                ),
                Vertical(
                    Static(
                        _build_calibration_table(interval_data, "interval"),
                        id="interval-table",
                    ),
                    Static(_LEGEND, classes="cal-legend"),
                    classes="cal-table-side",
                ),
                id="interval-panel",
                classes="cal-panel",
            ),
            Static(""),
            Button("Back [B]", id="back-btn", variant="default"),
            id="stats-content",
        )
        yield Footer()

    def on_resize(self, event: Resize) -> None:
        """Toggle narrow layout when terminal is too small for side-by-side."""
        is_narrow = event.size.width < _NARROW_THRESHOLD
        for panel in self.query(".cal-panel"):
            panel.set_class(is_narrow, "narrow")

    def _overall_stats_widget(self) -> Static:
        """Create overall statistics display."""
        grouped = self.repo.get_overall_stats_grouped()
        overall = grouped["overall"]
        binary = grouped["binary"]
        interval = grouped["interval"]
        brier = self.repo.get_binary_brier_score()

        total = overall["total"]
        total_pts = overall["total_score"]
        b_total = binary["total"]
        b_pts = binary["total_score"]
        i_total = interval["total"]
        i_pts = interval["total_score"]

        brier_str = f"[bold]{brier:.3f}[/]" if brier is not None else "[dim]\u2013[/]"

        lines = [
            f"[bold]{total}[/] questions answered    "
            f"[bold]{total_pts:.1f}[/] total points    "
            f"Brier score: {brier_str}",
            "",
            f"[dim]Binary:[/] {b_total} answered, [bold]{b_pts:.1f}[/] pts    "
            f"[dim]Interval:[/] {i_total} answered, [bold]{i_pts:.1f}[/] pts",
        ]

        return Static("\n".join(lines), id="overall-stats")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back-btn":
            self.action_back()

    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()
