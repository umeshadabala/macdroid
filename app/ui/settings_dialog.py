"""
Settings and About dialog for MacDroid.
Configures Display, Input, and Diagnostic options in a spacious, modern card-based layout,
and highlights developer Umesh Adabala.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig, ConfigManager


class SettingsDialog(QDialog):
    """Spacious, modern Settings and About dialog."""

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config_manager.config

        self.setWindowTitle("MacDroid Settings")
        self.resize(640, 720)
        self.setMinimumSize(600, 680)
        self._init_ui()

    def _create_card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("class", "settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)
        return card, layout

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setProperty("class", "cardSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # Tab Widget
        tabs = QTabWidget(self)

        # ----------------------------------------------------
        # TAB 1: PREFERENCES
        # ----------------------------------------------------
        pref_scroll = QScrollArea()
        pref_scroll.setWidgetResizable(True)
        pref_scroll.setFrameShape(QFrame.Shape.NoFrame)
        pref_scroll.setStyleSheet("background-color: transparent;")

        pref_content = QWidget()
        pref_layout = QVBoxLayout(pref_content)
        pref_layout.setContentsMargins(14, 14, 14, 14)
        pref_layout.setSpacing(14)

        # === 1. DISPLAY SECTION ===
        lbl_sec_display = QLabel("DISPLAY")
        lbl_sec_display.setProperty("class", "sectionHeader")
        pref_layout.addWidget(lbl_sec_display)

        card_display, d_layout = self._create_card()

        # Framerate
        lbl_fps_title = QLabel("Target Framerate")
        lbl_fps_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #f4f4f5;")
        d_layout.addWidget(lbl_fps_title)

        fps_row = QHBoxLayout()
        fps_row.setSpacing(24)
        self.radio_fps_60 = QRadioButton("60 FPS (Ultra Smooth)")
        self.radio_fps_30 = QRadioButton("30 FPS (Standard)")
        self.group_fps = QButtonGroup(self)
        self.group_fps.addButton(self.radio_fps_60)
        self.group_fps.addButton(self.radio_fps_30)

        if self.config.target_fps == 30:
            self.radio_fps_30.setChecked(True)
        else:
            self.radio_fps_60.setChecked(True)

        fps_row.addWidget(self.radio_fps_60)
        fps_row.addWidget(self.radio_fps_30)
        fps_row.addStretch(1)
        d_layout.addLayout(fps_row)

        d_layout.addWidget(self._create_separator())

        # Quality Preset
        lbl_qual_title = QLabel("Quality Preset")
        lbl_qual_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #f4f4f5;")
        d_layout.addWidget(lbl_qual_title)

        qual_row = QHBoxLayout()
        qual_row.setSpacing(24)
        self.radio_q_low = QRadioButton("Low (720p)")
        self.radio_q_bal = QRadioButton("Balanced (1080p)")
        self.radio_q_high = QRadioButton("High (1440p)")
        self.group_qual = QButtonGroup(self)
        self.group_qual.addButton(self.radio_q_low)
        self.group_qual.addButton(self.radio_q_bal)
        self.group_qual.addButton(self.radio_q_high)

        preset = self.config.quality_preset or "Balanced"
        if preset == "Low" or self.config.max_resolution <= 720:
            self.radio_q_low.setChecked(True)
        elif preset == "High" or self.config.max_resolution >= 1440:
            self.radio_q_high.setChecked(True)
        else:
            self.radio_q_bal.setChecked(True)

        qual_row.addWidget(self.radio_q_low)
        qual_row.addWidget(self.radio_q_bal)
        qual_row.addWidget(self.radio_q_high)
        qual_row.addStretch(1)
        d_layout.addLayout(qual_row)

        pref_layout.addWidget(card_display)

        # === 2. INPUT & GESTURES SECTION ===
        lbl_sec_input = QLabel("INPUT AND GESTURES")
        lbl_sec_input.setProperty("class", "sectionHeader")
        pref_layout.addWidget(lbl_sec_input)

        card_input, i_layout = self._create_card()

        lbl_sens_title = QLabel("Trackpad Scroll Sensitivity")
        lbl_sens_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #f4f4f5;")
        i_layout.addWidget(lbl_sens_title)

        lbl_sens_desc = QLabel("Controls scroll momentum dampening to prevent skipping feeds or videos.")
        lbl_sens_desc.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        i_layout.addWidget(lbl_sens_desc)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(14)
        lbl_low = QLabel("Low")
        lbl_low.setStyleSheet("color: #71717a; font-size: 12px; font-weight: 500;")
        slider_row.addWidget(lbl_low)

        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(10, 100)
        curr_val = int(self.config.scroll_sensitivity * 100)
        self.slider_sens.setValue(max(10, min(100, curr_val)))
        slider_row.addWidget(self.slider_sens, 1)

        lbl_high = QLabel("High")
        lbl_high.setStyleSheet("color: #71717a; font-size: 12px; font-weight: 500;")
        slider_row.addWidget(lbl_high)
        i_layout.addLayout(slider_row)

        self.lbl_sens_val = QLabel(f"Current Value: {self.slider_sens.value()}%  (Recommended: 35%)")
        self.lbl_sens_val.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 500;")
        self.slider_sens.valueChanged.connect(self._on_sens_changed)
        i_layout.addWidget(self.lbl_sens_val)

        pref_layout.addWidget(card_input)

        # === 3. DIAGNOSTICS & OVERLAYS SECTION ===
        lbl_sec_debug = QLabel("DIAGNOSTICS AND OVERLAYS")
        lbl_sec_debug.setProperty("class", "sectionHeader")
        pref_layout.addWidget(lbl_sec_debug)

        card_debug, deb_layout = self._create_card()

        self.chk_perf_overlay = QCheckBox("Show real-time performance overlay (FPS, stream health, latency)")
        self.chk_perf_overlay.setChecked(self.config.debug_overlay)
        deb_layout.addWidget(self.chk_perf_overlay)

        deb_layout.addWidget(self._create_separator())

        self.chk_coord_overlay = QCheckBox("Show touch coordinate crosshair HUD (X, Y mapping verification)")
        self.chk_coord_overlay.setChecked(self.config.coord_overlay)
        deb_layout.addWidget(self.chk_coord_overlay)

        pref_layout.addWidget(card_debug)
        pref_layout.addStretch(1)

        pref_scroll.setWidget(pref_content)
        tabs.addTab(pref_scroll, "Preferences")

        # ----------------------------------------------------
        # TAB 2: ABOUT DEVELOPER
        # ----------------------------------------------------
        about_scroll = QScrollArea()
        about_scroll.setWidgetResizable(True)
        about_scroll.setFrameShape(QFrame.Shape.NoFrame)
        about_scroll.setStyleSheet("background-color: transparent;")

        about_content = QWidget()
        about_layout = QVBoxLayout(about_content)
        about_layout.setContentsMargins(16, 18, 16, 18)
        about_layout.setSpacing(18)

        # App Overview Card
        card_app, ca_layout = self._create_card()

        header_row = QHBoxLayout()
        lbl_app_name = QLabel("MacDroid")
        lbl_app_name.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")
        header_row.addWidget(lbl_app_name)

        lbl_badge = QLabel("  v1.0.0 (Production Core)  ")
        lbl_badge.setStyleSheet(
            "background-color: #0369a1; color: #ffffff; font-size: 11px; "
            "font-weight: 600; border-radius: 4px; padding: 3px 6px;"
        )
        header_row.addWidget(lbl_badge)
        header_row.addStretch(1)
        ca_layout.addLayout(header_row)

        lbl_app_desc = QLabel(
            "Lightweight, low-latency Android screen mirroring and desktop control companion for macOS. "
            "Built with Python, PySide6, and native hardware video acceleration."
        )
        lbl_app_desc.setStyleSheet("color: #a1a1aa; font-size: 13px; line-height: 1.5;")
        lbl_app_desc.setWordWrap(True)
        ca_layout.addWidget(lbl_app_desc)

        about_layout.addWidget(card_app)

        # Developer Section Header
        lbl_sec_dev = QLabel("DEVELOPER")
        lbl_sec_dev.setProperty("class", "sectionHeader")
        about_layout.addWidget(lbl_sec_dev)

        # Developer Info Card
        card_dev, cd_layout = self._create_card()

        lbl_dev_name = QLabel("Umesh Adabala")
        lbl_dev_name.setStyleSheet("font-size: 18px; font-weight: 700; color: #f4f4f5;")
        cd_layout.addWidget(lbl_dev_name)

        lbl_dev_role = QLabel("Founder, Builder & Developer")
        lbl_dev_role.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 600;")
        cd_layout.addWidget(lbl_dev_role)

        lbl_dev_bio = QLabel(
            "Passionate about creating technology and native utilities that solve real-world problems. "
            "Crafting clean, reliable, and high-performance software for developers and everyday users."
        )
        lbl_dev_bio.setStyleSheet("color: #d4d4d8; font-size: 13px; line-height: 1.5;")
        lbl_dev_bio.setWordWrap(True)
        cd_layout.addWidget(lbl_dev_bio)

        cd_layout.addWidget(self._create_separator())

        # Action Links Row
        links_layout = QHBoxLayout()
        links_layout.setSpacing(14)

        btn_portfolio = QPushButton("Personal Website")
        btn_portfolio.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_portfolio.setFixedHeight(36)
        btn_portfolio.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://umeshadabala.github.io")))
        links_layout.addWidget(btn_portfolio)

        btn_github = QPushButton("GitHub Profile")
        btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_github.setFixedHeight(36)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/umeshadabala")))
        links_layout.addWidget(btn_github)

        btn_repo = QPushButton("MacDroid Repository")
        btn_repo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_repo.setFixedHeight(36)
        btn_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/umeshadabala/macdroid")))
        links_layout.addWidget(btn_repo)

        links_layout.addStretch(1)
        cd_layout.addLayout(links_layout)

        about_layout.addWidget(card_dev)
        about_layout.addStretch(1)

        about_scroll.setWidget(about_content)
        tabs.addTab(about_scroll, "About")

        main_layout.addWidget(tabs, 1)

        # Dialog Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.addStretch(1)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Changes")
        btn_save.setObjectName("primaryBtn")
        btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self._save_and_close)
        btn_box.addWidget(btn_save)

        main_layout.addLayout(btn_box)

    def _on_sens_changed(self, value: int) -> None:
        self.lbl_sens_val.setText(f"Current Value: {value}%  (Recommended: 35%)")

    def _save_and_close(self) -> None:
        # Input
        self.config.scroll_sensitivity = round(self.slider_sens.value() / 100.0, 2)

        # Mirroring FPS
        self.config.target_fps = 30 if self.radio_fps_30.isChecked() else 60

        # Mirroring Quality
        if self.radio_q_low.isChecked():
            self.config.quality_preset = "Low"
            self.config.max_resolution = 720
            self.config.bitrate_mbps = 4
        elif self.radio_q_high.isChecked():
            self.config.quality_preset = "High"
            self.config.max_resolution = 1440
            self.config.bitrate_mbps = 12
        else:
            self.config.quality_preset = "Balanced"
            self.config.max_resolution = 1080
            self.config.bitrate_mbps = 8

        # Debug
        self.config.debug_overlay = self.chk_perf_overlay.isChecked()
        self.config.coord_overlay = self.chk_coord_overlay.isChecked()

        self.config_manager.save(self.config)
        self.accept()
