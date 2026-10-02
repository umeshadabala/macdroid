"""
Mirror Session coordinator for MacDroid.
Orchestrates live video streaming from Android device to desktop Qt canvas.
"""

from __future__ import annotations

import os
import shutil
import time
from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from app.core.config import AppConfig
from app.core.logger import get_logger
from app.device.adb import ADBManager, AndroidDevice
from app.mirror.stream import VideoStreamWorker

log = get_logger("mirror")


class MirrorState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class MockScreenGenerator(QThread):
    """
    Generates a realistic simulated Android phone screen at 60 FPS for testing
    when no physical device is plugged in.
    """

    frame_ready = Signal(QImage)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._running = True
        self.device_width = 1080
        self.device_height = 2400
        self.touch_point: Optional[tuple[int, int]] = None
        self.touch_alpha = 0

    def set_touch(self, x: int, y: int) -> None:
        self.touch_point = (x, y)
        self.touch_alpha = 255

    def run(self) -> None:
        log.info("Mock Android screen generator started (60 FPS)")
        frame_interval = 1.0 / 60.0

        while self._running:
            start_time = time.time()

            # Render phone screen image
            img = QImage(self.device_width, self.device_height, QImage.Format.Format_RGB32)
            img.fill(QColor(18, 18, 22))  # Dark sleek OLED background

            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Wallpaper gradient / curves
            painter.setPen(QColor(0, 0, 0, 0))
            painter.setBrush(QColor(28, 32, 45))
            painter.drawRoundedRect(40, 200, 1000, 1900, 32, 32)

            # Top Status Bar
            now_str = time.strftime("%H:%M")
            painter.setPen(QColor(230, 230, 240))
            painter.setFont(QFont("-apple-system", 36, QFont.Weight.Bold))
            painter.drawText(60, 80, now_str)

            # Status icons (5G, Wifi, Battery)
            painter.setFont(QFont("-apple-system", 28))
            painter.drawText(860, 80, "5G  100%")

            # Center Clock Widget
            painter.setFont(QFont("-apple-system", 96, QFont.Weight.Light))
            painter.drawText(100, 480, now_str)
            painter.setFont(QFont("-apple-system", 34))
            date_str = time.strftime("%A, %B %d")
            painter.drawText(105, 540, date_str)

            # Search Bar Pill
            painter.setBrush(QColor(42, 46, 60))
            painter.drawRoundedRect(80, 640, 920, 100, 50, 50)
            painter.setPen(QColor(160, 165, 180))
            painter.setFont(QFont("-apple-system", 32))
            painter.drawText(150, 705, "Search apps & web...")

            # App Grid Mock Icons
            apps = [
                ("Phone", QColor(52, 199, 89)),
                ("Messages", QColor(0, 122, 255)),
                ("Chrome", QColor(255, 149, 0)),
                ("Camera", QColor(175, 82, 222)),
                ("Photos", QColor(255, 45, 85)),
                ("Settings", QColor(142, 142, 147)),
                ("Files", QColor(90, 200, 250)),
                ("Maps", QColor(88, 86, 214)),
            ]

            grid_x, grid_y = 120, 840
            col_spacing, row_spacing = 230, 240
            for idx, (name, color) in enumerate(apps):
                col = idx % 4
                row = idx // 4
                ax = grid_x + col * col_spacing
                ay = grid_y + row * row_spacing

                painter.setPen(QColor(0, 0, 0, 0))
                painter.setBrush(color)
                painter.drawRoundedRect(ax, ay, 130, 130, 36, 36)

                painter.setPen(QColor(220, 220, 230))
                painter.setFont(QFont("-apple-system", 24))
                painter.drawText(ax - 10, ay + 175, 150, 40, 0x0004, name)

            # Bottom Dock
            painter.setBrush(QColor(36, 40, 52, 200))
            painter.drawRoundedRect(60, 2100, 960, 200, 48, 48)

            dock_apps = [
                QColor(52, 199, 89),
                QColor(0, 122, 255),
                QColor(255, 45, 85),
                QColor(255, 149, 0),
            ]
            for i, col in enumerate(dock_apps):
                painter.setPen(QColor(0, 0, 0, 0))
                painter.setBrush(col)
                painter.drawRoundedRect(120 + i * 230, 2135, 130, 130, 36, 36)

            # Home Gesture Pill indicator
            painter.setBrush(QColor(255, 255, 255, 180))
            painter.drawRoundedRect(390, 2360, 300, 10, 5, 5)

            # Draw touch ripple effect if active
            if self.touch_point and self.touch_alpha > 0:
                tx, ty = self.touch_point
                painter.setPen(QColor(255, 255, 255, self.touch_alpha))
                painter.setBrush(QColor(0, 122, 255, self.touch_alpha // 2))
                painter.drawEllipse(tx - 35, ty - 35, 70, 70)
                self.touch_alpha = max(0, self.touch_alpha - 25)

            painter.end()

            self.frame_ready.emit(img)

            elapsed = time.time() - start_time
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)

    def stop(self) -> None:
        self._running = False
        self.wait(1000)


class MirrorSession(QObject):
    """Coordinates video mirroring for a selected Android device."""

    state_changed = Signal(MirrorState, str)
    frame_received = Signal(QImage)
    fps_updated = Signal(float)
    error_occurred = Signal(str)

    def __init__(self, adb: ADBManager, config: AppConfig, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.adb = adb
        self.config = config
        self.state: MirrorState = MirrorState.STOPPED
        self.current_device: Optional[AndroidDevice] = None

        self._stream_worker: Optional[VideoStreamWorker] = None
        self._mock_generator: Optional[MockScreenGenerator] = None

        # FPS metrics
        self._fps_count = 0
        self._fps_timer = time.time()
        self.current_fps = 0.0

    def start_mirroring(self, device: Optional[AndroidDevice] = None) -> bool:
        """Start mirroring for the given device or launch mock session if none available."""
        self.stop_mirroring()
        self.current_device = device

        if device is None or not device.is_ready or device.serial.startswith("MOCK"):
            log.info("Starting mock test stream engine.")
            return self._start_mock_session()

        self._set_state(MirrorState.STARTING, f"Connecting to {device.display_title} video stream...")

        # Initialize live VideoStreamWorker for real device
        self._stream_worker = VideoStreamWorker(
            adb=self.adb,
            device=device,
            max_resolution=self.config.max_resolution,
            bitrate_mbps=self.config.bitrate_mbps,
            target_fps=self.config.target_fps,
            parent=self,
        )

        self._stream_worker.frame_ready.connect(self._on_frame_received)
        self._stream_worker.fps_updated.connect(self.fps_updated)
        self._stream_worker.stream_error.connect(self._on_stream_error)
        self._stream_worker.stream_started.connect(self._on_stream_started)
        self._stream_worker.stream_stopped.connect(self._on_stream_stopped)

        self._stream_worker.start()
        return True

    def _start_mock_session(self) -> bool:
        """Start mock test stream."""
        self._set_state(MirrorState.STARTING, "Starting simulated Android test screen...")
        self._mock_generator = MockScreenGenerator(parent=self)
        self._mock_generator.frame_ready.connect(self._on_frame_received)
        self._mock_generator.start()
        self._set_state(MirrorState.RUNNING, "Simulated Android Device (Test Mode, 60 FPS)")
        return True

    def _on_stream_started(self) -> None:
        title = self.current_device.display_title if self.current_device else "Android Device"
        self._set_state(MirrorState.RUNNING, f"Mirroring {title}")

    def _on_stream_stopped(self, reason: str) -> None:
        log.info("Stream stopped: %s", reason)
        self._set_state(MirrorState.STOPPED, reason)

    def _on_stream_error(self, err: str) -> None:
        log.error("Stream error: %s", err)
        self.error_occurred.emit(err)
        self._set_state(MirrorState.ERROR, err)

    def _on_frame_received(self, img: QImage) -> None:
        self._fps_count += 1
        now = time.time()
        if now - self._fps_timer >= 1.0:
            self.current_fps = self._fps_count / (now - self._fps_timer)
            self._fps_count = 0
            self._fps_timer = now
            self.fps_updated.emit(self.current_fps)

        self.frame_received.emit(img)

    def stop_mirroring(self) -> None:
        """Stop any active mirroring session."""
        if self._stream_worker:
            log.info("Stopping video stream worker...")
            self._stream_worker.stop()
            self._stream_worker = None

        if self._mock_generator:
            log.info("Stopping mock screen generator...")
            self._mock_generator.stop()
            self._mock_generator = None

        self._set_state(MirrorState.STOPPED, "Disconnected")

    def _set_state(self, state: MirrorState, message: str) -> None:
        self.state = state
        self.state_changed.emit(state, message)

    @property
    def is_running(self) -> bool:
        return self.state == MirrorState.RUNNING
