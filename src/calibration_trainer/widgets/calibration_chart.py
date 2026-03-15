"""Calibration chart widget using textual-plotext."""

from textual_plotext import PlotextPlot


class CalibrationChart(PlotextPlot):
    """Widget for displaying calibration deviation charts using plotext."""

    MIN_DATA_POINTS = 3  # Minimum predictions per bucket to show data

    def __init__(
        self,
        data: list[dict] | None = None,
        chart_type: str = "binary",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.data = data or []
        self.chart_type = chart_type

    def on_mount(self) -> None:
        """Render the chart when mounted."""
        self.refresh_chart()

    def refresh_chart(self) -> None:
        """Refresh the chart display."""
        self.plt.clear_figure()
        self.plt.clear_data()

        if not self.data:
            self.plt.title("No calibration data yet")
            self.refresh()
            return

        has_enough_data = any(
            d.get("total", 0) >= self.MIN_DATA_POINTS for d in self.data
        )

        if not has_enough_data:
            self.plt.title(f"Need {self.MIN_DATA_POINTS}+ predictions per bucket")
            self.refresh()
            return

        if self.chart_type == "binary":
            self._render_binary_chart()
        else:
            self._render_interval_chart()

        self.refresh()

    def _render_deviation_chart(
        self, labels: list[str], deviations: list[float | None]
    ) -> None:
        """Render a deviation-from-perfect-calibration bar chart.

        Grey squares mark zero at each bucket. Colored bars show only
        the deviation: green above (under-confident), red below (over-confident).
        """
        x = list(range(len(labels)))
        green_vals = []
        red_vals = []

        for dev in deviations:
            if dev is None:
                green_vals.append(0)
                red_vals.append(0)
            elif dev >= 0:
                green_vals.append(dev)
                red_vals.append(0)
            else:
                green_vals.append(0)
                red_vals.append(dev)  # negative → bar extends downward

        # Colored deviation bars (numeric x so scatter can share the axis)
        self.plt.bar(x, green_vals, width=0.6, color="green+")
        self.plt.bar(x, red_vals, width=0.6, color="red+")

        # Grey zero line: hline for gaps between bars, dense scatter to
        # overwrite colored bar pixels at y=0 with grey
        self.plt.hline(0, color="gray")
        bar_half = 0.3
        scatter_x = []
        for xi in x:
            offset = -bar_half
            while offset <= bar_half:
                scatter_x.append(xi + offset)
                offset += 0.02
        self.plt.scatter(scatter_x, [0] * len(scatter_x), color="gray", marker="sd")

        self.plt.xticks([float(i) for i in x], labels)

        # Symmetric y-axis with clean round tick marks (step of 10 to
        # avoid bunching in a 16-row chart)
        max_abs = max(
            (abs(d) for d in deviations if d is not None),
            default=10,
        )
        y_limit = max(((int(max_abs) // 10) + 1) * 10, 10)
        self.plt.ylim(-y_limit, y_limit)

        ticks = list(range(-y_limit, y_limit + 1, 10))
        tick_labels = [f"{t:+d}" if t != 0 else " 0" for t in ticks]

        self.plt.yticks([float(t) for t in ticks], tick_labels)

    def _render_binary_chart(self) -> None:
        """Render a binary calibration deviation chart."""
        labels = []
        deviations: list[float | None] = []

        for d in self.data:
            bucket = d.get("bucket", 0)
            total = d.get("total", 0)
            rate = d.get("rate")

            labels.append(f"{bucket}%")
            if total >= self.MIN_DATA_POINTS and rate is not None:
                deviations.append((rate * 100) - bucket)
            else:
                deviations.append(None)

        self._render_deviation_chart(labels, deviations)

    def _render_interval_chart(self) -> None:
        """Render an interval calibration deviation chart."""
        labels = []
        deviations: list[float | None] = []

        for d in self.data:
            conf = d.get("confidence", 0)
            total = d.get("total", 0)
            rate = d.get("rate")

            labels.append(f"{conf}%")
            if total >= self.MIN_DATA_POINTS and rate is not None:
                deviations.append((rate * 100) - conf)
            else:
                deviations.append(None)

        self._render_deviation_chart(labels, deviations)

    def set_data(self, data: list[dict], chart_type: str = "binary") -> None:
        """Update the chart data."""
        self.data = data
        self.chart_type = chart_type
        self.refresh_chart()
