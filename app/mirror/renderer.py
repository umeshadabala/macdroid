"""
Frame Renderer for PhoneConnect.
Draws video frames with hardware acceleration, high-DPI Retina scaling,
aspect ratio preservation, letterbox centering, and rounded OLED bezel corners.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen

from app.input.coordinates import CoordinateMapper


class FrameRenderer:
    """Renders video frames and phone bezels onto a QPainter canvas."""

    def __init__(self, mapper: CoordinateMapper) -> None:
        self.mapper = mapper
        self.corner_radius = 24.0  # Smooth iPhone/Android rounded display corners

    def render(
        self,
        painter: QPainter,
        frame: Optional[QImage],
        widget_w: float,
        widget_h: float,
        device_connected: bool = True,
        status_text: str = "",
    ) -> None:
        """Render frame or placeholder onto the painter surface."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 1. Fill entire widget background with sleek matte dark
        painter.fillRect(QRectF(0, 0, widget_w, widget_h), QColor(15, 15, 18))

        # 2. Compute viewport
        vp = self.mapper.get_viewport()
        video_rect = QRectF(vp.offset_x, vp.offset_y, vp.width, vp.height)

        if frame and not frame.isNull():
            # Create rounded phone screen clipping path
            clip_path = QPainterPath()
            clip_path.addRoundedRect(video_rect, self.corner_radius, self.corner_radius)

            painter.save()
            painter.setClipPath(clip_path)

            # Draw the video frame scaled to viewport
            painter.drawImage(video_rect, frame)

            painter.restore()

            # Draw subtle phone bezel stroke
            painter.save()
            bezel_pen = QPen(QColor(50, 50, 60, 180), 2.0)
            painter.setPen(bezel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(video_rect, self.corner_radius, self.corner_radius)
            painter.restore()

        else:
            # Placeholder when disconnected or waiting for stream
            self._render_placeholder(painter, video_rect, device_connected, status_text)

    def _render_placeholder(
        self,
        painter: QPainter,
        rect: QRectF,
        device_connected: bool,
        status_text: str,
    ) -> None:
        # Phone frame outline
        painter.save()
        painter.setPen(QPen(QColor(40, 40, 50), 2))
        painter.setBrush(QColor(24, 24, 28))
        painter.drawRoundedRect(rect, self.corner_radius, self.corner_radius)

        # Phone speaker notch pill at top
        pill_w, pill_h = 100.0, 6.0
        pill_x = rect.x() + (rect.width() - pill_w) / 2.0
        pill_y = rect.y() + 16.0
        painter.setBrush(QColor(45, 45, 55))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), 3, 3)

        # Status icon / text in center
        painter.setPen(QColor(160, 160, 175))
        font = painter.font()
        font.setPointSize(14)
        font.setWeight(font.Weight.Medium)
        painter.setFont(font)

        msg = status_text or ("Connect an Android phone via USB" if not device_connected else "Starting stream...")
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)

        painter.restore()
