"""
Device Selector dropdown widget for PhoneConnect.
Displays available Android devices, status badges, and selection signals.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from app.core.logger import get_logger
from app.device.adb import AndroidDevice

log = get_logger("ui.selector")


class DeviceSelector(QComboBox):
    """Dropdown for choosing between connected Android phones."""

    device_selected = Signal(object)  # AndroidDevice or None

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._devices: List[AndroidDevice] = []
        self.currentIndexChanged.connect(self._on_index_changed)
        self.setToolTip("Select connected Android device")

    def update_devices(self, devices: List[AndroidDevice], active_serial: Optional[str] = None) -> None:
        """Update available devices list preserving selection."""
        self.blockSignals(True)
        self.clear()
        self._devices = devices

        if not devices:
            self.addItem("No Device", None)
            self.addItem("Simulated Phone (Test Mode)", "MOCK")
        else:
            for dev in devices:
                label = dev.model if dev.model and dev.model != "unknown" else dev.serial
                if not dev.is_ready:
                    if dev.state == "unauthorized":
                        label += " (Unauthorized)"
                    elif dev.state == "offline":
                        label += " (Offline)"
                    else:
                        label += f" ({dev.state})"
                self.addItem(label, dev.serial)

            self.addItem("Simulated Phone (Test Mode)", "MOCK")

        # Restore active selection
        index_to_select = 0
        if active_serial:
            for idx in range(self.count()):
                if self.itemData(idx) == active_serial:
                    index_to_select = idx
                    break

        self.setCurrentIndex(index_to_select)
        self.blockSignals(False)

    def _on_index_changed(self, index: int) -> None:
        if index < 0:
            return
        data = self.itemData(index)
        if data == "MOCK":
            # Return synthetic mock device
            mock_dev = AndroidDevice(
                serial="MOCK_DEVICE",
                state="device",
                model="Simulated Pixel 9",
                connection_type="usb",
                screen_width=1080,
                screen_height=2400,
            )
            self.device_selected.emit(mock_dev)
        elif data:
            match = next((d for d in self._devices if d.serial == data), None)
            self.device_selected.emit(match)
        else:
            self.device_selected.emit(None)

    def get_selected_device(self) -> Optional[AndroidDevice]:
        idx = self.currentIndex()
        if idx < 0:
            return None
        data = self.itemData(idx)
        if data == "MOCK":
            return AndroidDevice(
                serial="MOCK_DEVICE",
                state="device",
                model="Simulated Pixel 9",
                connection_type="usb",
                screen_width=1080,
                screen_height=2400,
            )
        return next((d for d in self._devices if d.serial == data), None)
