"""
Performance telemetry and coordinate debug HUD overlay for MacDroid.
Renders real-time stream diagnostics and pixel-accurate touch crosshair indicators.
"""

from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from app.input.coordinates import CoordinateDebugInfo, CoordinateMapper


class PerformanceOverlay:
    """Renders semi-transparent diagnostic HUD and touch crosshairs on the mirrored display."""

    def __init__(self, mapper: Optional[CoordinateMapper] = None) -> None:
        self.mapper = mapper
        self.enabled = False
        self.fps = 0.0
        self.bitrate_mbps = 8.0
        self.resolution = "1080×2400"
        self.device_name = "Android Device"
        self.decoder_status = "Hardware (libavcodec)"
        self.latency_ms = 12.0

        # Crosshair debug coordinates
        self.crosshair_enabled = True
        self.crosshair_point: Optional[QPointF] = None
        self.crosshair_alpha = 0

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def update_metrics(
        self,
        fps: Optional[float] = None,
        bitrate_mbps: Optional[float] = None,
        resolution: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> None:
        if fps is not None:
            self.fps = fps
        if bitrate_mbps is not None:
            self.bitrate_mbps = bitrate_mbps
        if resolution is not None:
            self.resolution = resolution
        if device_name is not None:
            self.device_name = device_name

    def trigger_crosshair(self, wx: float, wy: float) -> None:
        """Trigger temporary touch crosshair indicator."""
        self.crosshair_point = QPointF(wx, wy)
        self.crosshair_alpha = 255

    def render(self, painter: QPainter, widget_width: float, widget_height: float) -> None:
        # Draw interactive touch crosshair if active (even when HUD is closed, gives visual feedback)
        if self.crosshair_enabled and self.crosshair_point and self.crosshair_alpha > 0:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            cx = self.crosshair_point.x()
            cy = self.crosshair_point.y()
            pen = QPen(QColor(56, 189, 248, self.crosshair_alpha), 2.0)
            painter.setPen(pen)

            # Draw crosshair '+'
            line_len = 14.0
            painter.drawLine(QPointF(cx - line_len, cy), QPointF(cx + line_len, cy))
            painter.drawLine(QPointF(cx, cy - line_len), QPointF(cx, cy + line_len))

            # Small target circle
            painter.setBrush(QColor(56, 189, 248, self.crosshair_alpha // 4))
            painter.drawEllipse(QPointF(cx, cy), 6.0, 6.0)

            painter.restore()
            self.crosshair_alpha = max(0, self.crosshair_alpha - 20)

        if not self.enabled:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Coordinate Debug Telemetry Box (Top-Left)
        panel_x, panel_y = 16.0, 16.0
        panel_w, panel_h = 280.0, 230.0

        # Dark frosted panel background
        painter.setBrush(QColor(15, 15, 20, 225))
        painter.setPen(QColor(56, 189, 248, 180))
        painter.drawRoundedRect(QRectF(panel_x, panel_y, panel_w, panel_h), 8.0, 8.0)

        # Title
        painter.setPen(QColor(56, 189, 248))
        font_title = QFont("-apple-system", 11, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.drawText(QPointF(panel_x + 12, panel_y + 22), "MACDROID COORDINATE DEBUG")

        # Telemetry Data
        debug_info = self.mapper.last_debug_info if self.mapper else CoordinateDebugInfo()

        font_label = QFont("-apple-system", 10, QFont.Weight.Normal)
        font_val = QFont("-apple-system", 10, QFont.Weight.DemiBold)

        metrics = [
            ("Mouse Widget:", f"{debug_info.widget_x:.0f}, {debug_info.widget_y:.0f}"),
            (
                "Video Rect:",
                f"{debug_info.video_rect_x:.0f}, {debug_info.video_rect_y:.0f} → {debug_info.video_rect_x + debug_info.video_rect_w:.0f}, {debug_info.video_rect_y + debug_info.video_rect_h:.0f}",
            ),
            ("Scale Factor:", f"{debug_info.scale:.3f}"),
            (
                "Android Touch:",
                f"{debug_info.android_x}, {debug_info.android_y}" if debug_info.is_inside else "[Outside Margin]",
            ),
            ("Android Screen:", f"{debug_info.android_res_w} × {debug_info.android_res_h}"),
            ("Stream FPS:", f"{self.fps:.1f} FPS"),
            ("Stream Bitrate:", f"{self.bitrate_mbps:.1f} Mbps"),
            ("Decoder:", self.decoder_status),
        ]

        start_y = panel_y + 44
        line_height = 21.0
        for idx, (label, val) in enumerate(metrics):
            y = start_y + idx * line_height
            painter.setFont(font_label)
            painter.setPen(QColor(161, 161, 170))
            painter.drawText(QPointF(panel_x + 12, y), label)

            painter.setFont(font_val)
            color = QColor(244, 244, 245)
            if "Android Touch:" in label and not debug_info.is_inside:
                color = QColor(239, 68, 68)  # Red warning
            elif "Android Touch:" in label:
                color = QColor(34, 197, 94)  # Green active
            painter.setPen(color)
            painter.drawText(QPointF(panel_x + 120, y), val)

        painter.restore()
