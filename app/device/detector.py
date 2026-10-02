"""
Device Detector for PhoneConnect.
Monitors ADB in a non-blocking background worker and emits Qt signals upon state changes.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from app.core.logger import get_logger
from app.device.adb import ADBManager, AndroidDevice

log = get_logger("detector")


class DeviceDetectorWorker(QThread):
    """Background polling thread for USB/network device detection."""

    devices_updated = Signal(list)  # List[AndroidDevice]
    device_connected = Signal(object)  # AndroidDevice
    device_disconnected = Signal(str)  # serial
    adb_status_changed = Signal(bool, str)  # is_available, message

    def __init__(self, adb: ADBManager, poll_interval: float = 1.5, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.adb = adb
        self.poll_interval = poll_interval
        self._running = True
        self._known_devices: Dict[str, AndroidDevice] = {}
        self._last_adb_state: Optional[bool] = None

    def run(self) -> None:
        log.info("Device detector thread started (interval=%.1fs)", self.poll_interval)
        while self._running:
            try:
                # 1. Verify ADB availability
                is_available = self.adb.is_available()
                if is_available != self._last_adb_state:
                    self._last_adb_state = is_available
                    msg = "ADB ready" if is_available else "ADB was not found. Please install Android Platform Tools."
                    self.adb_status_changed.emit(is_available, msg)

                if not is_available:
                    time.sleep(self.poll_interval * 2)
                    continue

                # 2. Query devices
                current_devices = self.adb.list_devices()
                current_map = {d.serial: d for d in current_devices}

                # Check for newly connected devices or state changes
                for serial, dev in current_map.items():
                    if serial not in self._known_devices:
                        log.info("New device detected: %s [%s]", dev.display_title, dev.state)
                        self.device_connected.emit(dev)
                    else:
                        old_dev = self._known_devices[serial]
                        if old_dev.state != dev.state:
                            log.info("Device state change: %s -> %s", serial, dev.state)

                # Check for disconnected devices
                for serial in list(self._known_devices.keys()):
                    if serial not in current_map:
                        log.info("Device disconnected: %s", serial)
                        self.device_disconnected.emit(serial)

                self._known_devices = current_map
                self.devices_updated.emit(current_devices)

            except Exception as e:
                log.error("Exception during device polling: %s", e)

            # Sleep between polls
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Signal thread to stop and wait for completion."""
        self._running = False
        self.wait(2000)
        log.info("Device detector thread stopped.")


class DeviceDetector(QObject):
    """Facade for device detection and management in UI."""

    devices_updated = Signal(list)
    device_connected = Signal(object)
    device_disconnected = Signal(str)
    adb_status_changed = Signal(bool, str)

    def __init__(self, adb: ADBManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.adb = adb
        self.worker = DeviceDetectorWorker(adb, parent=self)
        self.worker.devices_updated.connect(self.devices_updated)
        self.worker.device_connected.connect(self.device_connected)
        self.worker.device_disconnected.connect(self.device_disconnected)
        self.worker.adb_status_changed.connect(self.adb_status_changed)

    def start(self) -> None:
        if not self.worker.isRunning():
            self.worker.start()

    def stop(self) -> None:
        if self.worker.isRunning():
            self.worker.stop()
