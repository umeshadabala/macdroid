"""
Configuration management for PhoneConnect.
Persists settings in ~/.phoneconnect/config.json.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict

from app.core.logger import get_app_dir, get_logger

log = get_logger("config")
CONFIG_FILE_NAME = "config.json"


@dataclass
class AppConfig:
    # Mirroring Settings
    max_resolution: int = 1080  # Max dimension (e.g. 1080, 720, 1440)
    target_fps: int = 60        # 30 or 60
    bitrate_mbps: int = 8       # 4, 8, 12, 16 Mbps
    buffer_ms: int = 0          # 0 = lowest latency

    # Input Settings
    scroll_sensitivity: float = 0.35  # 0.1 (low) to 1.0 (high)

    # Telemetry & UI Settings
    debug_overlay: bool = False
    coord_overlay: bool = False
    quality_preset: str = "Balanced"  # "Low", "Balanced", "High"
    stay_awake: bool = True
    turn_screen_off: bool = False
    engine_mode: str = "auto"   # "auto", "native_scrcpy", "in_app"

    # Paths
    adb_path: str = ""          # Optional manual override

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class ConfigManager:
    """Manages reading and writing application settings."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or (get_app_dir() / CONFIG_FILE_NAME)
        self.config = self.load()

    def load(self) -> AppConfig:
        """Load configuration from disk or create default."""
        if not self.config_path.exists():
            log.info("No existing configuration found. Creating defaults.")
            config = AppConfig()
            self.save(config)
            return config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            config = AppConfig.from_dict(data)
            log.info("Loaded configuration from %s", self.config_path)
            return config
        except Exception as e:
            log.warning("Failed to parse config file (%s). Falling back to defaults.", e)
            return AppConfig()

    def save(self, config: AppConfig | None = None) -> None:
        """Save configuration to disk."""
        if config is not None:
            self.config = config
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            log.info("Saved configuration to %s", self.config_path)
        except Exception as e:
            log.error("Failed to save configuration: %s", e)
