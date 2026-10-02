"""
Main Application Window for MacDroid.
Assembles GUI layout, hardware buttons, device selector, status bar, and connects all subsystems.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig, ConfigManager
from app.core.logger import get_logger
from app.core.process import process_manager
from app.device.adb import ADBManager, AndroidDevice
from app.device.detector import DeviceDetector
from app.device.session import DeviceSession, SessionState
from app.input.coordinates import CoordinateMapper
from app.input.keyboard import KEYCODE_APP_SWITCH, KEYCODE_BACK, KEYCODE_HOME, KeyboardController
from app.input.mouse import MouseController
from app.mirror.session import MirrorSession, MirrorState
from app.ui.device_selector import DeviceSelector
from app.ui.mirror_widget import MirrorWidget
from app.ui.settings_dialog import SettingsDialog
from app.ui.status_bar import StatusBar

log = get_logger("ui.main")


class MainWindow(QMainWindow):
    """Primary macOS desktop window for MacDroid."""

    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.config

        # 1. Initialize Subsystems
        self.adb = ADBManager(custom_path=self.config.adb_path)
        self.detector = DeviceDetector(self.adb, parent=self)
        self.session = DeviceSession(self.adb, parent=self)
        self.mapper = CoordinateMapper(
            widget_width=380,
            widget_height=780,
            video_width=720,
            video_height=1600,
            device_physical_width=720,
            device_physical_height=1604,
        )
        self.mirror = MirrorSession(self.adb, self.config, parent=self)

        # 2. Input Controllers
        self.mouse_controller = MouseController(
            adb=self.adb,
            mapper=self.mapper,
            serial_getter=self._get_active_serial,
            on_touch_visual=self._on_touch_visual,
        )
        self.keyboard_controller = KeyboardController(
            adb=self.adb,
            serial_getter=self._get_active_serial,
            config=self.config,
            mapper=self.mapper,
        )

        # 3. Setup User Interface
        self._last_screenshot_path: Optional[str] = None
        self._init_ui()
        self._wire_signals()

        # 4. Start background detection
        self.detector.start()

    def _get_active_serial(self) -> Optional[str]:
        if self.session.device:
            return self.session.device.serial
        return None

    def _on_touch_visual(self, wx: float, wy: float, action: str) -> None:
        self.mirror_widget.add_touch_visual(wx, wy, action)

    def _init_ui(self) -> None:
        self.setWindowTitle("MacDroid")
        self.resize(500, 840)
        self.setMinimumSize(360, 520)

        # Central Container
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Header Bar ---
        header_bar = QWidget()
        header_bar.setStyleSheet("background-color: #18181b; border-bottom: 1px solid #27272a;")
        h_layout = QHBoxLayout(header_bar)
        h_layout.setContentsMargins(14, 8, 14, 8)
        h_layout.setSpacing(10)

        # App Brand
        lbl_brand = QLabel("MacDroid")
        lbl_brand.setStyleSheet("font-weight: 700; font-size: 14px; color: #f4f4f5;")
        h_layout.addWidget(lbl_brand)

        h_layout.addStretch(1)

        # Device Selector Dropdown
        self.device_selector = DeviceSelector(self)
        self.device_selector.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.device_selector.update_devices([])
        h_layout.addWidget(self.device_selector)

        # Mirror / Stop Toggle Button
        self.btn_mirror = QPushButton("Mirror")
        self.btn_mirror.setObjectName("primaryBtn")
        self.btn_mirror.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mirror.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_mirror.setFixedHeight(32)
        self.btn_mirror.clicked.connect(self._toggle_mirroring)
        h_layout.addWidget(self.btn_mirror)

        # Debug HUD Toggle
        self.btn_hud = QPushButton("HUD")
        self.btn_hud.setToolTip("Toggle Performance & Coordinate HUD")
        self.btn_hud.setCheckable(True)
        self.btn_hud.setChecked(self.config.debug_overlay)
        self.btn_hud.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_hud.setFixedHeight(32)
        self.btn_hud.clicked.connect(self._toggle_hud)
        h_layout.addWidget(self.btn_hud)

        # Settings Button
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_settings.setFixedHeight(32)
        self.btn_settings.clicked.connect(self._open_settings)
        h_layout.addWidget(self.btn_settings)

        main_layout.addWidget(header_bar)

        # --- Live Phone Mirror View ---
        self.mirror_widget = MirrorWidget(self.mapper, parent=self)
        self.mirror_widget.set_controllers(self.mouse_controller, self.keyboard_controller)
        self.mirror_widget.overlay.enabled = self.config.debug_overlay
        self.mirror_widget.overlay.crosshair_enabled = self.config.coord_overlay
        main_layout.addWidget(self.mirror_widget, 1)

        # --- Bottom Navigation & Control Toolbar ---
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet("background-color: #18181b; border-top: 1px solid #27272a;")
        t_layout = QHBoxLayout(toolbar_container)
        t_layout.setContentsMargins(14, 8, 14, 8)
        t_layout.setSpacing(10)
        t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def _make_tool_btn(text: str, tooltip: str) -> QPushButton:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(34)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            return btn

        self.btn_back = _make_tool_btn("Back", "Back")
        self.btn_back.clicked.connect(lambda: self._inject_key(KEYCODE_BACK))
        t_layout.addWidget(self.btn_back)

        self.btn_home = _make_tool_btn("Home", "Home")
        self.btn_home.clicked.connect(lambda: self._inject_key(KEYCODE_HOME))
        t_layout.addWidget(self.btn_home)

        self.btn_recents = _make_tool_btn("Recents", "Recent Apps")
        self.btn_recents.clicked.connect(lambda: self._inject_key(KEYCODE_APP_SWITCH))
        t_layout.addWidget(self.btn_recents)

        self.btn_screenshot = _make_tool_btn("Screenshot", "Take Screenshot")
        self.btn_screenshot.clicked.connect(self._on_take_screenshot)
        t_layout.addWidget(self.btn_screenshot)

        self.btn_wake = _make_tool_btn("Wake", "Wake Screen")
        self.btn_wake.clicked.connect(self._wake_phone)
        t_layout.addWidget(self.btn_wake)

        main_layout.addWidget(toolbar_container)

        # --- Bottom Status Bar ---
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)

    def _wire_signals(self) -> None:
        # Device Detector signals
        self.detector.devices_updated.connect(self._on_devices_updated)
        self.detector.device_connected.connect(self._on_device_connected)
        self.detector.device_disconnected.connect(self._on_device_disconnected)
        self.detector.adb_status_changed.connect(self._on_adb_status_changed)

        # Device Selector signal
        self.device_selector.device_selected.connect(self._on_device_selected)

        # Session signals
        self.session.state_changed.connect(self._on_session_state_changed)

        # Mirror Session signals
        self.mirror.state_changed.connect(self._on_mirror_state_changed)
        self.mirror.frame_received.connect(self.mirror_widget.update_frame)
        self.mirror.fps_updated.connect(self._on_fps_updated)
        self.mirror.error_occurred.connect(self.status_bar.show_toast)

    # --- Slots & Actions ---

    def _inject_key(self, keycode: int) -> None:
        serial = self._get_active_serial()
        if serial:
            self.adb.inject_keyevent(serial, keycode)
        elif self.mirror.is_running:
            self.status_bar.show_toast(f"Test action triggered (Key {keycode})")

    def _on_take_screenshot(self) -> None:
        serial = self._get_active_serial()
        if not serial:
            self.status_bar.show_toast("No active phone connected")
            return

        dest_dir = str(Path.home() / "Pictures" / "MacDroid")
        ok, path_or_err = self.adb.take_screenshot(serial, dest_dir)
        if ok:
            filename = os.path.basename(path_or_err)
            self._last_screenshot_path = path_or_err
            log.info("Native screenshot saved: %s", path_or_err)
            self.status_bar.show_toast("Screenshot saved", duration_ms=4000)
        else:
            self.status_bar.show_toast(f"Screenshot failed: {path_or_err}", duration_ms=4000)

    def _open_last_screenshot_in_finder(self) -> None:
        """Reveal the latest screenshot in macOS Finder."""
        import subprocess
        target = self._last_screenshot_path
        if target and os.path.exists(target):
            subprocess.run(["open", "-R", target])
        else:
            dest_dir = str(Path.home() / "Pictures" / "MacDroid")
            os.makedirs(dest_dir, exist_ok=True)
            subprocess.run(["open", dest_dir])

    def _wake_phone(self) -> None:
        """Wake up phone screen (KEYCODE_WAKEUP = 224)."""
        serial = self._get_active_serial()
        if not serial:
            self.status_bar.show_toast("No active phone connected")
            return

        ok = self.adb.wake_device(serial)
        if ok:
            self.status_bar.show_toast("Phone screen awake")
            if not self.mirror.is_running and self.session.device and self.session.device.is_ready:
                self.mirror.start_mirroring(self.session.device)
        else:
            self.status_bar.show_toast("Failed to wake phone")

    def _toggle_hud(self) -> None:
        enabled = self.btn_hud.isChecked()
        self.mirror_widget.overlay.enabled = enabled
        self.mirror_widget.update()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config_manager, self)
        if dlg.exec():
            self.mirror_widget.overlay.enabled = self.config.debug_overlay
            self.mirror_widget.overlay.crosshair_enabled = self.config.coord_overlay
            self.btn_hud.setChecked(self.config.debug_overlay)
            self.mouse_controller.set_scroll_sensitivity(self.config.scroll_sensitivity)
            self.keyboard_controller.config = self.config
            self.status_bar.show_toast("Settings saved")

    def _toggle_mirroring(self) -> None:
        if self.mirror.is_running:
            self.mirror.stop_mirroring()
        else:
            dev = self.device_selector.get_selected_device()
            self.mirror.start_mirroring(dev)

    def _on_devices_updated(self, devices: List[AndroidDevice]) -> None:
        active_serial = self.session.device.serial if self.session.device else None
        self.device_selector.update_devices(devices, active_serial)

        # Auto-attach if a ready device is found and no session is active
        if not self.session.device and devices:
            ready = next((d for d in devices if d.is_ready), None)
            if ready:
                self.session.attach(ready)
                self.mirror_widget.set_device_physical_size(ready.screen_width, ready.screen_height)
                if not self.mirror.is_running:
                    self.mirror.start_mirroring(ready)

    def _on_device_connected(self, device: AndroidDevice) -> None:
        log.info("Device connected: %s", device.display_title)
        self.status_bar.show_toast("Android connected")
        if not self.session.device and device.is_ready:
            self.session.attach(device)
            self.mirror_widget.set_device_physical_size(device.screen_width, device.screen_height)
            if not self.mirror.is_running:
                self.mirror.start_mirroring(device)

    def _on_device_disconnected(self, serial: str) -> None:
        if self.session.device and self.session.device.serial == serial:
            log.info("Active device disconnected: %s", serial)
            self.status_bar.show_toast("Phone disconnected")
            self.mirror.stop_mirroring()
            self.session.detach()
            self.status_bar.set_connected(False)
            self.mirror_widget.set_status(False, "Phone disconnected - Reconnect USB cable")

    def _on_adb_status_changed(self, available: bool, msg: str) -> None:
        if not available:
            self.status_bar.show_toast(msg, duration_ms=5000)

    def _on_device_selected(self, device: Optional[AndroidDevice]) -> None:
        if device:
            self.session.attach(device)
            self.mirror_widget.set_device_physical_size(device.screen_width, device.screen_height)
            self.mirror_widget.overlay.update_metrics(
                device_name=device.model,
                resolution=f"{device.screen_width}×{device.screen_height}",
            )
        else:
            self.session.detach()

    def _on_session_state_changed(self, state: SessionState, message: str) -> None:
        connected = state in (SessionState.CONNECTED, SessionState.STREAMING)
        dev_name = self.session.device.model if self.session.device else ""
        transport = self.session.device.connection_type if self.session.device else "USB"

        self.status_bar.set_connected(connected, dev_name, transport)
        self.mirror_widget.set_status(connected, message)

        if state == SessionState.UNAUTHORIZED:
            self.status_bar.show_toast("Please unlock phone and allow USB debugging", 6000)

    def _on_mirror_state_changed(self, state: MirrorState, message: str) -> None:
        if state == MirrorState.RUNNING:
            self.btn_mirror.setText("Stop")
            self.btn_mirror.setStyleSheet("background-color: #dc2626; color: white;")
            self.status_bar.show_toast("Mirroring active")
        else:
            self.btn_mirror.setText("Mirror")
            self.btn_mirror.setStyleSheet("")
            self.status_bar.show_toast(message)

    def _on_fps_updated(self, fps: float) -> None:
        self.status_bar.set_fps(fps)
        self.mirror_widget.overlay.update_metrics(fps=fps)

    def closeEvent(self, event) -> None:
        """Cleanly terminate all background threads and processes upon window close."""
        log.info("Application closing - stopping processes and threads...")
        self.detector.stop()
        self.mirror.stop_mirroring()
        process_manager.stop_all()
        super().closeEvent(event)
