"""
Centralized logging system for PhoneConnect.
Logs to ~/.phoneconnect/phoneconnect.log and console with structured formatting.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

APP_DIR_NAME = ".macdroid"
LOG_FILE_NAME = "macdroid.log"


def get_app_dir() -> Path:
    """Return ~/.macdroid directory, creating it if necessary."""
    app_dir = Path.home() / APP_DIR_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def setup_logger(name: str = "macdroid", level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root MacDroid logger."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)  # Capture all, handlers will filter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (~/.phoneconnect/phoneconnect.log)
    try:
        log_file = get_app_dir() / LOG_FILE_NAME
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[PhoneConnect] Warning: Could not create log file: {e}", file=sys.stderr)

    return logger


logger = setup_logger()


def get_logger(subsystem: str) -> logging.Logger:
    """Return a child logger for a specific subsystem."""
    return logging.getLogger(f"phoneconnect.{subsystem}")
