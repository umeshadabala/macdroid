"""
MirrorWidget for MacDroid.
Interactive video surface that renders the live Android screen, captures mouse/keyboard input,
and hosts the coordinate debug crosshair HUD.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from app.core.logger import get_logger
from app.input.coordinates import CoordinateMapper
from app.input.keyboard import KeyboardController
from app.input.mouse import MouseController
from app.mirror.renderer import FrameRenderer
from app.ui.overlay import PerformanceOverlay

log = get_logger("widget")


class MirrorWidget(QWidget):
    """Interactive screen mirroring widget with mouse and keyboard input support."""

    def __init__(
        self,
        mapper: CoordinateMapper,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.mapper = mapper
        self.renderer = FrameRenderer(mapper)
        self.overlay = PerformanceOverlay(mapper=mapper)

        self.mouse_controller: Optional[MouseController] = None
        self.keyboard_controller: Optional[KeyboardController] = None

        self._current_frame: Optional[QImage] = None
        self._status_text: str = "Connect an Android phone via USB"
        self._device_connected: bool = False

        # Visual touch ripple animations
        self._touch_ripples: List[tuple[float, float, float, int]] = []

        # Widget settings
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 560)

    def set_controllers(self, mouse: MouseController, keyboard: KeyboardController) -> None:
        self.mouse_controller = mouse
        self.keyboard_controller = keyboard

    def set_device_physical_size(self, width: int, height: int) -> None:
        """Inform mapper of phone's physical hardware touch dimensions."""
        self.mapper.update_device_physical_size(width, height)
        self.overlay.update_metrics(resolution=f"{width}×{height}")
        self.update()

    def update_frame(self, frame: QImage) -> None:
        """Receive a new decoded video frame from the mirror session."""
        self._current_frame = frame
        if frame and not frame.isNull():
            self.mapper.update_video_dimensions(frame.width(), frame.height())
        self.update()

    def set_status(self, connected: bool, message: str) -> None:
        self._device_connected = connected
        self._status_text = message
        if not connected:
            self._current_frame = None
        self.update()

    def add_touch_visual(self, wx: float, wy: float, action: str) -> None:
        """Display an immediate visual ripple and coordinate crosshair on Mac screen."""
        self._touch_ripples.append((wx, wy, 12.0, 220))
        self.overlay.trigger_crosshair(wx, wy)
        self.update()

    # --- Qt Event Handlers ---

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.mapper.update_widget_size(
            width=event.size().width(),
            height=event.size().height(),
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        self.renderer.render(
            painter=painter,
            frame=self._current_frame,
            widget_w=float(self.width()),
            widget_h=float(self.height()),
            device_connected=self._device_connected,
            status_text=self._status_text,
        )

        # Paint touch ripples if active
        if self._touch_ripples:
            next_ripples = []
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for x, y, r, a in self._touch_ripples:
                painter.setPen(QColor(56, 189, 248, a))
                painter.setBrush(QColor(56, 189, 248, a // 3))
                painter.drawEllipse(QPointF(x, y), r, r)
                if a > 30 and r < 36.0:
                    next_ripples.append((x, y, r + 4.0, a - 35))
            painter.restore()
            self._touch_ripples = next_ripples

        # Paint Diagnostic Telemetry HUD
        self.overlay.render(painter, float(self.width()), float(self.height()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if self.mouse_controller:
            self.mouse_controller.handle_mouse_press(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.mouse_controller:
            self.mouse_controller.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.mouse_controller:
            self.mouse_controller.handle_mouse_release(event)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.mouse_controller:
            self.mouse_controller.handle_mouse_double_click(event)
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.mouse_controller:
            self.mouse_controller.handle_wheel(event)
        super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        handled = False
        if self.keyboard_controller:
            handled = self.keyboard_controller.handle_key_press(event)
        if not handled:
            super().keyPressEvent(event)

