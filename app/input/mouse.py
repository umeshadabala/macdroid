"""
Mouse and Trackpad controller for MacDroid.
Translates desktop mouse actions and high-resolution Mac trackpad gestures into
natural, controlled, phone-like touch and scroll events without aggressive skipping.
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from app.core.logger import get_logger
from app.device.adb import ADBManager
from app.input.coordinates import CoordinateMapper

log = get_logger("mouse")


class ScrollNormalizer:
    """
    Accumulates and normalizes high-frequency macOS trackpad wheel events.
    Applies non-linear sensitivity scaling and cooldown gating to prevent
    violent multi-video skips in short-form video feeds (YouTube Shorts, Reels).
    """

    def __init__(self, sensitivity: float = 0.35) -> None:
        self.sensitivity = max(0.05, min(1.0, sensitivity))
        self._accum_dx = 0.0
        self._accum_dy = 0.0
        self._last_event_time = 0.0
        self._last_gesture_time = 0.0
        self._gesture_cooldown = 0.28  # Minimum seconds between swipe gestures to absorb momentum

    def set_sensitivity(self, sensitivity: float) -> None:
        self.sensitivity = max(0.05, min(1.0, sensitivity))

    def process_wheel(
        self,
        event: QWheelEvent,
        device_w: int,
        device_h: int,
    ) -> Optional[Tuple[str, int, int]]:
        """
        Process a wheel event. Returns (axis, displacement_pixels, duration_ms)
        when a gesture threshold is met, or None if still accumulating or cooling down.
        """
        now = time.time()

        # Reset accumulator if user stopped scrolling for more than 200ms
        if now - self._last_event_time > 0.20:
            self._accum_dx = 0.0
            self._accum_dy = 0.0

        self._last_event_time = now

        # Read high-res pixelDelta if available, fallback to angleDelta
        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()

        dy = pixel_delta.y() if not pixel_delta.isNull() else angle_delta.y() / 4.0
        dx = pixel_delta.x() if not pixel_delta.isNull() else angle_delta.x() / 4.0

        self._accum_dy += dy
        self._accum_dx += dx

        # If we are within cooldown window from last triggered gesture, discard inertia
        if now - self._last_gesture_time < self._gesture_cooldown:
            return None

        # Activation threshold inversely proportional to sensitivity:
        # High (1.0) -> ~25px; Normal (0.35) -> ~70px; Low (0.1) -> ~88px
        threshold = max(20.0, 95.0 - 70.0 * self.sensitivity)

        abs_y = abs(self._accum_dy)
        abs_x = abs(self._accum_dx)

        # 1. Horizontal Scroll Check
        if abs_x > abs_y * 1.3 and abs_x >= threshold:
            self._last_gesture_time = now
            sign = 1 if self._accum_dx > 0 else -1
            ratio = min(2.5, abs_x / threshold)
            self._accum_dx = 0.0
            self._accum_dy = 0.0

            # Scale horizontal distance naturally: small: ~16%, medium: ~30%, large: ~45% max
            dist_ratio = min(0.48, 0.15 + 0.15 * ratio * (0.5 + 0.5 * self.sensitivity))
            dist = int(device_w * dist_ratio) * sign
            duration = int(max(140, min(240, 180 + 25 * ratio)))
            return ("horizontal", dist, duration)

        # 2. Vertical Scroll Check
        if abs_y >= threshold:
            self._last_gesture_time = now
            sign = 1 if self._accum_dy > 0 else -1
            ratio = min(2.2, abs_y / threshold)
            self._accum_dy = 0.0
            self._accum_dx = 0.0

            # Compute natural phone swipe distance:
            # small: ~20%, medium: ~35-40% (1 Short/Reel), large: ~50% max
            dist_ratio = min(0.52, 0.18 + 0.18 * ratio * (0.6 + 0.4 * self.sensitivity))
            dist = int(device_h * dist_ratio) * sign
            duration = int(max(150, min(230, 170 + 25 * ratio)))
            return ("vertical", dist, duration)

        return None


class MouseController:
    """Handles pointer interaction from the MirrorWidget and transmits touch actions to Android."""

    def __init__(
        self,
        adb: ADBManager,
        mapper: CoordinateMapper,
        serial_getter: Callable[[], Optional[str]],
        on_touch_visual: Optional[Callable[[float, float, str], None]] = None,
        scroll_sensitivity: float = 0.35,
    ) -> None:
        self.adb = adb
        self.mapper = mapper
        self.serial_getter = serial_getter
        self.on_touch_visual = on_touch_visual

        self.scroll_normalizer = ScrollNormalizer(sensitivity=scroll_sensitivity)

        self._is_dragging = False
        self._drag_start_time = 0.0
        self._drag_start_pos: Optional[Tuple[int, int]] = None
        self._last_drag_pos: Optional[Tuple[int, int]] = None

    def set_scroll_sensitivity(self, sensitivity: float) -> None:
        self.scroll_normalizer.set_sensitivity(sensitivity)

    def handle_mouse_press(self, event: QMouseEvent) -> None:
        """Handle mouse button down."""
        serial = self.serial_getter()
        if not serial:
            return

        pos = event.position()
        mapped = self.mapper.widget_to_device(pos.x(), pos.y())
        if not mapped:
            return

        dx, dy = mapped

        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_time = time.time()
            self._drag_start_pos = (dx, dy)
            self._last_drag_pos = (dx, dy)
            if self.on_touch_visual:
                self.on_touch_visual(pos.x(), pos.y(), "down")

        elif event.button() == Qt.MouseButton.RightButton:
            # Right-Click maps directly to Android BACK key
            log.info("Right-click -> Android BACK key")
            self.adb.inject_keyevent(serial, 4)

    def handle_mouse_move(self, event: QMouseEvent) -> None:
        """Handle mouse motion (tracking drags when left button is held)."""
        pos = event.position()

        # Update coordinate debug info for hover
        self.mapper.widget_to_device(pos.x(), pos.y())

        if not self._is_dragging or not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        mapped = self.mapper.widget_to_device(pos.x(), pos.y())
        if not mapped:
            return

        self._last_drag_pos = mapped
        if self.on_touch_visual:
            self.on_touch_visual(pos.x(), pos.y(), "move")

    def handle_mouse_release(self, event: QMouseEvent) -> None:
        """Handle mouse button release (completes tap, long press, or swipe/drag)."""
        serial = self.serial_getter()
        if not serial or not self._is_dragging:
            self._is_dragging = False
            return

        pos = event.position()
        mapped = self.mapper.widget_to_device(pos.x(), pos.y())
        self._is_dragging = False

        if not self._drag_start_pos:
            return

        start_x, start_y = self._drag_start_pos
        end_x, end_y = mapped if mapped else (self._last_drag_pos or (start_x, start_y))

        elapsed_ms = int((time.time() - self._drag_start_time) * 1000)
        dist_sq = (end_x - start_x) ** 2 + (end_y - start_y) ** 2

        # 250 px squared threshold (~15 pixels displacement on a 1080p screen)
        if dist_sq < 250:
            if elapsed_ms > 500:
                # Long press -> Send long swipe in place (500ms+)
                log.debug("Long press at (%d, %d) [%dms]", start_x, start_y, elapsed_ms)
                self.adb.inject_swipe(serial, start_x, start_y, start_x, start_y, duration_ms=elapsed_ms)
            else:
                # Instant pixel-accurate tap at mouse-down location
                log.debug("Tap at (%d, %d)", start_x, start_y)
                self.adb.inject_tap(serial, start_x, start_y)
        else:
            # Deliberate Drag / Swipe gesture
            duration = max(100, min(600, elapsed_ms))
            log.debug("Swipe from (%d, %d) to (%d, %d) [%dms]", start_x, start_y, end_x, end_y, duration)
            self.adb.inject_swipe(serial, start_x, start_y, end_x, end_y, duration_ms=duration)

        if self.on_touch_visual:
            self.on_touch_visual(pos.x(), pos.y(), "up")

    def handle_mouse_double_click(self, event: QMouseEvent) -> None:
        """Handle double-click (two quick taps)."""
        serial = self.serial_getter()
        if not serial:
            return

        pos = event.position()
        mapped = self.mapper.widget_to_device(pos.x(), pos.y())
        if not mapped:
            return

        dx, dy = mapped
        log.debug("Double tap at (%d, %d)", dx, dy)
        self.adb.inject_tap(serial, dx, dy)
        time.sleep(0.04)
        self.adb.inject_tap(serial, dx, dy)

    def handle_wheel(self, event: QWheelEvent) -> None:
        """Handle normalized trackpad scroll events."""
        serial = self.serial_getter()
        if not serial:
            return

        pos = event.position()
        mapped = self.mapper.widget_to_device(pos.x(), pos.y())
        if not mapped:
            return

        dx, dy = mapped
        touch_w, touch_h = self.mapper.get_active_touch_bounds()

        result = self.scroll_normalizer.process_wheel(event, touch_w, touch_h)
        if not result:
            return

        axis, dist, duration = result

        if axis == "vertical":
            # Natural scrolling: scrolling down (negative delta) swipes UP (reveals lower items)
            # dist > 0 means scroll up -> swipe down
            if dist > 0:
                y1 = max(80, dy - abs(dist) // 2)
                y2 = min(touch_h - 80, y1 + abs(dist))
                log.debug("Controlled scroll up: (%d, %d) -> (%d, %d)", dx, y1, dx, y2)
                self.adb.inject_swipe(serial, dx, y1, dx, y2, duration_ms=duration)
            else:
                y1 = min(touch_h - 80, dy + abs(dist) // 2)
                y2 = max(80, y1 - abs(dist))
                log.debug("Controlled scroll down: (%d, %d) -> (%d, %d)", dx, y1, dx, y2)
                self.adb.inject_swipe(serial, dx, y1, dx, y2, duration_ms=duration)

        elif axis == "horizontal":
            if dist > 0:
                # Scroll right -> swipe left
                x1 = min(touch_w - 80, dx + abs(dist) // 2)
                x2 = max(80, x1 - abs(dist))
                self.adb.inject_swipe(serial, x1, dy, x2, dy, duration_ms=duration)
            else:
                # Scroll left -> swipe right
                x1 = max(80, dx - abs(dist) // 2)
                x2 = min(touch_w - 80, x1 + abs(dist))
                self.adb.inject_swipe(serial, x1, dy, x2, dy, duration_ms=duration)
