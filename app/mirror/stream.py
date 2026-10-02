"""
Video Stream worker for MacDroid.
Streams real-time H.264 video from an Android device via ADB USB transport and
decodes frames natively off the UI thread into QImage instances.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage

from app.core.logger import get_logger
from app.device.adb import ADBManager, AndroidDevice
from app.mirror.decoder import NativeVideoDecoder

log = get_logger("stream")


class VideoStreamWorker(QThread):
    """Background worker thread that receives and decodes the Android H.264 stream."""

    frame_ready = Signal(QImage)
    fps_updated = Signal(float)
    stream_started = Signal()
    stream_stopped = Signal(str)
    stream_error = Signal(str)

    def __init__(
        self,
        adb: ADBManager,
        device: AndroidDevice,
        max_resolution: int = 1080,
        bitrate_mbps: int = 8,
        target_fps: int = 60,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.adb = adb
        self.device = device
        self.max_resolution = max_resolution
        self.bitrate_mbps = bitrate_mbps
        self.target_fps = target_fps
        self._running = True
        self._proc: Optional[subprocess.Popen] = None
        self.decoder = NativeVideoDecoder()

    def run(self) -> None:
        if not self.adb.adb_path:
            self.stream_error.emit("ADB not available")
            return

        serial = self.device.serial
        log.info("Starting live video stream worker for device: %s", serial)

        # Compute resolution preserving aspect ratio
        orig_w = self.device.screen_width or 720
        orig_h = self.device.screen_height or 1600

        # Scale down if height exceeds max_resolution
        scale = min(1.0, self.max_resolution / max(orig_w, orig_h))
        target_w = int(orig_w * scale)
        target_h = int(orig_h * scale)
        # Dimensions must be divisible by 2 for H.264
        target_w = target_w - (target_w % 2)
        target_h = target_h - (target_h % 2)

        bitrate = int(self.bitrate_mbps * 1_000_000)

        cmd = [
            self.adb.adb_path,
            "-s", serial,
            "exec-out",
            "screenrecord",
            "--output-format=h264",
            f"--size={target_w}x{target_h}",
            f"--bit-rate={bitrate}",
            "-",
        ]

        log.info("Launching stream process: %s", " ".join(cmd))
        env = os.environ.copy()

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                env=env,
            )

            self.stream_started.emit()

            last_fps_emit = time.time()

            def on_frame(qimg: QImage) -> None:
                nonlocal last_fps_emit
                if self._running and not qimg.isNull():
                    self.frame_ready.emit(qimg)
                    now = time.time()
                    if now - last_fps_emit >= 0.5:
                        self.fps_updated.emit(self.decoder.current_fps)
                        last_fps_emit = now

            def is_running() -> bool:
                return self._running and self._proc is not None and self._proc.poll() is None

            # Stream loop with native libavcodec decoding
            if self._proc.stdout:
                self.decoder.decode_stream(
                    stream_io=self._proc.stdout,
                    on_frame=on_frame,
                    is_running=is_running,
                )

        except Exception as e:
            log.error("Exception in video stream worker: %s", e)
            if self._running:
                self.stream_error.emit(str(e))
        finally:
            self._cleanup_process()
            self.stream_stopped.emit("Stream terminated")

    def _cleanup_process(self) -> None:
        if self._proc:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
                    self._proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    def stop(self) -> None:
        """Gracefully stop stream and wait for background thread."""
        self._running = False
        self._cleanup_process()
        self.wait(1500)
        log.info("Video stream worker stopped.")
