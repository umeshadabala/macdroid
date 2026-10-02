"""
Status Bar for PhoneConnect.
Displays connection indicators, active device info, transport mode, FPS, and notifications.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStatusBar, QWidget


class StatusBar(QStatusBar):
    """Bottom status bar showing real-time connectivity and stream health."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Connection status label
        self.lbl_status = QLabel("○ Disconnected")
        self.lbl_status.setStyleSheet("font-weight: 500; color: #71717a;")
        self.addWidget(self.lbl_status, 1)

        # FPS Counter
        self.lbl_fps = QLabel("60 FPS")
        self.lbl_fps.setStyleSheet("color: #a1a1aa; font-weight: 500; font-size: 11px;")
        self.lbl_fps.hide()
        self.addPermanentWidget(self.lbl_fps)

        # Notification Toast Timer
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._clear_toast)

    def set_connected(self, connected: bool, device_name: str = "", transport: str = "USB") -> None:
        if connected:
            mode_str = "USB" if transport.lower() != "tcpip" else "Wi-Fi"
            self.lbl_status.setText(f"● Connected via {mode_str}")
            self.lbl_status.setStyleSheet("font-weight: 500; color: #22c55e;")
            self.lbl_fps.show()
        else:
            self.lbl_status.setText("○ Disconnected")
            self.lbl_status.setStyleSheet("font-weight: 500; color: #71717a;")
            self.lbl_fps.hide()

    def set_fps(self, fps: float) -> None:
        self.lbl_fps.setText(f"{fps:.0f} FPS")

    def show_toast(self, message: str, duration_ms: int = 3500) -> None:
        """Display a temporary toast notification in the status bar."""
        self.showMessage(message, duration_ms)
        self._toast_timer.start(duration_ms)

    def _clear_toast(self) -> None:
        self.clearMessage()
