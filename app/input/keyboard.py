"""
Keyboard controller for MacDroid.
Translates Mac/Qt key events to Android keycodes, text inputs, and optional
simulated media swipes for short-form video feeds.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from app.core.config import AppConfig
from app.core.logger import get_logger
from app.device.adb import ADBManager
from app.input.coordinates import CoordinateMapper

log = get_logger("keyboard")

# Standard Android Keycodes
KEYCODE_HOME = 3
KEYCODE_BACK = 4
KEYCODE_DPAD_UP = 19
KEYCODE_DPAD_DOWN = 20
KEYCODE_DPAD_LEFT = 21
KEYCODE_DPAD_RIGHT = 22
KEYCODE_DPAD_CENTER = 23
KEYCODE_VOLUME_UP = 24
KEYCODE_VOLUME_DOWN = 25
KEYCODE_POWER = 26
KEYCODE_TAB = 61
KEYCODE_SPACE = 62
KEYCODE_ENTER = 66
KEYCODE_DEL = 67  # Backspace
KEYCODE_ESCAPE = 111
KEYCODE_FORWARD_DEL = 112  # Delete
KEYCODE_MOVE_HOME = 122
KEYCODE_MOVE_END = 123
KEYCODE_PAGE_UP = 92
KEYCODE_PAGE_DOWN = 93
KEYCODE_VOLUME_MUTE = 164
KEYCODE_APP_SWITCH = 187  # Recent apps

QT_TO_ANDROID_KEY: Dict[int, int] = {
    Qt.Key.Key_Return: KEYCODE_ENTER,
    Qt.Key.Key_Enter: KEYCODE_ENTER,
    Qt.Key.Key_Backspace: KEYCODE_DEL,
    Qt.Key.Key_Tab: KEYCODE_TAB,
    Qt.Key.Key_Back: KEYCODE_BACK,
    Qt.Key.Key_Escape: KEYCODE_BACK,
    Qt.Key.Key_Space: KEYCODE_SPACE,
    Qt.Key.Key_Delete: KEYCODE_FORWARD_DEL,
    Qt.Key.Key_Home: KEYCODE_MOVE_HOME,
    Qt.Key.Key_End: KEYCODE_MOVE_END,
    Qt.Key.Key_Left: KEYCODE_DPAD_LEFT,
    Qt.Key.Key_Right: KEYCODE_DPAD_RIGHT,
    Qt.Key.Key_Up: KEYCODE_DPAD_UP,
    Qt.Key.Key_Down: KEYCODE_DPAD_DOWN,
    Qt.Key.Key_PageUp: KEYCODE_PAGE_UP,
    Qt.Key.Key_PageDown: KEYCODE_PAGE_DOWN,
    Qt.Key.Key_VolumeUp: KEYCODE_VOLUME_UP,
    Qt.Key.Key_VolumeDown: KEYCODE_VOLUME_DOWN,
    Qt.Key.Key_VolumeMute: KEYCODE_VOLUME_MUTE,
}


class KeyboardController:
    """Translates desktop keyboard events into Android input events."""

    def __init__(
        self,
        adb: ADBManager,
        serial_getter: Callable[[], Optional[str]],
        config: Optional[AppConfig] = None,
        mapper: Optional[CoordinateMapper] = None,
    ) -> None:
        self.adb = adb
        self.serial_getter = serial_getter
        self.config = config
        self.mapper = mapper

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle Qt key press. Returns True if event was consumed."""
        serial = self.serial_getter()
        if not serial:
            return False

        key = event.key()
        modifiers = event.modifiers()
        text = event.text()

        # Handle Mac Shortcuts (Cmd+C, Cmd+V, Cmd+A, Cmd+Z)
        is_cmd = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))

        if is_cmd:
            if key == Qt.Key.Key_C:
                log.debug("Cmd+C -> Keycode Copy")
                self.adb.inject_keyevent(serial, 278)  # KEYCODE_COPY
                return True
            elif key == Qt.Key.Key_V:
                log.debug("Cmd+V -> Keycode Paste")
                self.adb.inject_keyevent(serial, 279)  # KEYCODE_PASTE
                return True
            elif key == Qt.Key.Key_A:
                log.debug("Cmd+A -> Select All")
                self.adb.inject_keyevent(serial, 29)  # KEYCODE_A
                return True
            elif key == Qt.Key.Key_Z:
                log.debug("Cmd+Z -> Undo")
                self.adb.inject_keyevent(serial, 54)  # KEYCODE_Z
                return True
            elif key == Qt.Key.Key_Backspace:
                self.adb.inject_keyevent(serial, KEYCODE_DEL)
                return True


        # Standard Android Keycodes
        if key in QT_TO_ANDROID_KEY:
            android_keycode = QT_TO_ANDROID_KEY[key]
            log.debug("Mapped key %s -> Android keycode %d", key, android_keycode)
            self.adb.inject_keyevent(serial, android_keycode)
            return True

        # Printable character input
        if text and text.isprintable():
            log.debug("Injecting text character: %s", repr(text))
            self.adb.inject_text(serial, text)
            return True

        return False
