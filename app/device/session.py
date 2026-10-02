"""
Device Session management for PhoneConnect.
Maintains state, lifecycle, and recovery for a connected Android device.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.core.logger import get_logger
from app.device.adb import ADBManager, AndroidDevice

log = get_logger("session")


class SessionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"


class DeviceSession(QObject):
    """Tracks the active session for an Android device."""

    state_changed = Signal(SessionState, str)  # (new_state, message)
    device_updated = Signal(object)  # AndroidDevice

    def __init__(self, adb: ADBManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.adb = adb
        self.device: Optional[AndroidDevice] = None
        self.state: SessionState = SessionState.DISCONNECTED
        self._last_error: str = ""

    def attach(self, device: AndroidDevice) -> None:
        """Attach session to a device and update state."""
        self.device = device
        log.info("Attaching session to device: %s [%s]", device.serial, device.state)

        if device.state == "device":
            self.set_state(SessionState.CONNECTED, f"Connected to {device.display_title}")
        elif device.state == "unauthorized":
            self.set_state(SessionState.UNAUTHORIZED, "Please unlock your Android phone and allow USB debugging.")
        elif device.state == "offline":
            self.set_state(SessionState.OFFLINE, "Device is offline. Please reconnect.")
        else:
            self.set_state(SessionState.ERROR, f"Device state: {device.state}")

        self.device_updated.emit(device)

    def detach(self) -> None:
        """Detach from current device."""
        if self.device:
            log.info("Detaching session from %s", self.device.serial)
            self.device = None
            self.set_state(SessionState.DISCONNECTED, "No device connected")

    def set_state(self, new_state: SessionState, message: str = "") -> None:
        """Transition session to a new state."""
        if self.state != new_state or self._last_error != message:
            old_state = self.state
            self.state = new_state
            self._last_error = message
            log.info("Session state: %s -> %s (%s)", old_state.value, new_state.value, message)
            self.state_changed.emit(new_state, message)

    def wake(self) -> bool:
        """Wake up device screen if attached."""
        if not self.device or not self.device.is_ready:
            return False
        return self.adb.wake_device(self.device.serial)

    def unlock(self) -> bool:
        """Dismiss keyguard on attached device."""
        if not self.device or not self.device.is_ready:
            return False
        return self.adb.unlock_device(self.device.serial)

    @property
    def is_active(self) -> bool:
        return self.device is not None and self.state in (SessionState.CONNECTED, SessionState.STREAMING)
