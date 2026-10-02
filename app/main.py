"""
Main entry point for MacDroid application.
"""

from __future__ import annotations

import os
import signal
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core.config import ConfigManager
from app.core.logger import get_logger, logger
from app.ui.main_window import MainWindow
from app.ui.styles import DARK_THEME_QSS

log = get_logger("main")


def main() -> int:
    """Launch MacDroid."""
    log.info("Starting MacDroid on macOS...")

    # Enable native high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MacDroid")
    app.setApplicationDisplayName("MacDroid — Android on your Mac")
    app.setOrganizationName("MacDroid")
    app.setOrganizationDomain("macdroid.local")

    # Apply Dark Theme
    app.setStyleSheet(DARK_THEME_QSS)

    # Allow clean exit on SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    # Configuration & Main Window
    config_mgr = ConfigManager()
    window = MainWindow(config_mgr)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
