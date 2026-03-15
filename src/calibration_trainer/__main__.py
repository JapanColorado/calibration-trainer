"""Entry point for the calibration trainer application."""

from calibration_trainer.app import CalibrationApp


def main() -> None:
    """Run the calibration trainer application."""
    app = CalibrationApp()
    app.run()


if __name__ == "__main__":
    main()
