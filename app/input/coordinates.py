"""
Coordinate Mapping Layer for MacDroid.
Provides a mathematically sound, 3-space coordinate transformation:
1. Qt Widget Coordinates (logical pixels)
2. Displayed Video Rectangle (aspect-ratio preserved viewport)
3. Android Physical Touchscreen Coordinates (exact sensor dimensions)

Supports arbitrary resolutions, orientations (portrait/landscape), window resizing,
letterboxing/pillarboxing, and high-DPI / Retina displays without device-specific hacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Viewport:
    offset_x: float
    offset_y: float
    width: float
    height: float
    scale: float


@dataclass
class CoordinateDebugInfo:
    widget_x: float = 0.0
    widget_y: float = 0.0
    video_rect_x: float = 0.0
    video_rect_y: float = 0.0
    video_rect_w: float = 0.0
    video_rect_h: float = 0.0
    scale: float = 1.0
    android_x: int = 0
    android_y: int = 0
    android_res_w: int = 1080
    android_res_h: int = 2400
    is_inside: bool = False


class CoordinateMapper:
    """Translates 2D coordinates between desktop Qt widget space and Android touch space."""

    def __init__(
        self,
        widget_width: float = 1.0,
        widget_height: float = 1.0,
        video_width: int = 1080,
        video_height: int = 2400,
        device_physical_width: Optional[int] = None,
        device_physical_height: Optional[int] = None,
        device_width: Optional[int] = None,
        device_height: Optional[int] = None,
    ) -> None:
        self.widget_width = max(1.0, float(widget_width))
        self.widget_height = max(1.0, float(widget_height))
        self.video_width = max(1, int(video_width))
        self.video_height = max(1, int(video_height))

        # Support both device_physical_width and legacy device_width
        phys_w = device_physical_width or device_width or video_width
        phys_h = device_physical_height or device_height or video_height
        self.device_physical_width = max(1, int(phys_w))
        self.device_physical_height = max(1, int(phys_h))

        # Cached debug telemetry
        self.last_debug_info = CoordinateDebugInfo()

    @property
    def device_width(self) -> int:
        return self.device_physical_width

    @device_width.setter
    def device_width(self, val: int) -> None:
        self.device_physical_width = max(1, int(val))

    @property
    def device_height(self) -> int:
        return self.device_physical_height

    @device_height.setter
    def device_height(self, val: int) -> None:
        self.device_physical_height = max(1, int(val))

    def update_widget_size(self, width: float, height: float) -> None:
        """Update Qt widget logical dimensions upon resize."""
        self.widget_width = max(1.0, float(width))
        self.widget_height = max(1.0, float(height))

    def update_video_dimensions(self, width: int, height: int) -> None:
        """Update video stream resolution when incoming frames change."""
        if width > 0 and height > 0:
            self.video_width = int(width)
            self.video_height = int(height)

    def update_device_physical_size(self, width: int, height: int) -> None:
        """Update device physical touchscreen resolution (from adb shell wm size)."""
        if width > 0 and height > 0:
            self.device_physical_width = int(width)
            self.device_physical_height = int(height)

    def is_landscape(self) -> bool:
        """True if the active video stream is in landscape orientation."""
        return self.video_width > self.video_height

    def get_active_touch_bounds(self) -> Tuple[int, int]:
        """
        Return the physical touch coordinate range based on current stream orientation.
        If video is landscape, width is max(physical_w, physical_h), height is min.
        If video is portrait, width is min(physical_w, physical_h), height is max.
        """
        min_dim = min(self.device_physical_width, self.device_physical_height)
        max_dim = max(self.device_physical_width, self.device_physical_height)

        if self.is_landscape():
            return max_dim, min_dim
        else:
            return min_dim, max_dim

    def get_viewport(self) -> Viewport:
        """
        Compute the rendered video rectangle centered in the widget with aspect ratio preserved.
        Uses uniform scaling: scale = min(avail_w / video_w, avail_h / video_h).
        """
        scale = min(
            self.widget_width / self.video_width,
            self.widget_height / self.video_height,
        )

        disp_w = self.video_width * scale
        disp_h = self.video_height * scale

        offset_x = (self.widget_width - disp_w) / 2.0
        offset_y = (self.widget_height - disp_h) / 2.0

        return Viewport(
            offset_x=offset_x,
            offset_y=offset_y,
            width=disp_w,
            height=disp_h,
            scale=scale,
        )

    def widget_to_device(self, wx: float, wy: float) -> Optional[Tuple[int, int]]:
        """
        Transform a Qt widget point (wx, wy) into exact Android physical touch coordinates (dx, dy).
        Returns None if (wx, wy) falls outside the visible video area (letterbox margin).
        """
        vp = self.get_viewport()
        touch_w, touch_h = self.get_active_touch_bounds()

        # Check if click is inside the displayed video rectangle
        is_inside = (
            vp.offset_x <= wx <= vp.offset_x + vp.width
            and vp.offset_y <= wy <= vp.offset_y + vp.height
        )

        if not is_inside:
            self.last_debug_info = CoordinateDebugInfo(
                widget_x=wx,
                widget_y=wy,
                video_rect_x=vp.offset_x,
                video_rect_y=vp.offset_y,
                video_rect_w=vp.width,
                video_rect_h=vp.height,
                scale=vp.scale,
                android_x=0,
                android_y=0,
                android_res_w=touch_w,
                android_res_h=touch_h,
                is_inside=False,
            )
            return None

        # Normalized coordinates [0.0, 1.0] across the video
        norm_x = (wx - vp.offset_x) / vp.width
        norm_y = (wy - vp.offset_y) / vp.height
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Scale to physical touchscreen resolution
        dx = int(round(norm_x * (touch_w - 1)))
        dy = int(round(norm_y * (touch_h - 1)))

        # Clamp bounds
        dx = max(0, min(touch_w - 1, dx))
        dy = max(0, min(touch_h - 1, dy))

        self.last_debug_info = CoordinateDebugInfo(
            widget_x=wx,
            widget_y=wy,
            video_rect_x=vp.offset_x,
            video_rect_y=vp.offset_y,
            video_rect_w=vp.width,
            video_rect_h=vp.height,
            scale=vp.scale,
            android_x=dx,
            android_y=dy,
            android_res_w=touch_w,
            android_res_h=touch_h,
            is_inside=True,
        )

        return dx, dy

    def device_to_widget(self, dx: int, dy: int) -> Tuple[float, float]:
        """Reverse transformation: map Android physical touch coordinates back to widget pixels."""
        vp = self.get_viewport()
        touch_w, touch_h = self.get_active_touch_bounds()

        norm_x = dx / max(1, touch_w - 1)
        norm_y = dy / max(1, touch_h - 1)

        wx = vp.offset_x + norm_x * vp.width
        wy = vp.offset_y + norm_y * vp.height
        return wx, wy
