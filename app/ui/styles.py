"""
Styles and design system for MacDroid.
Provides a native Apple macOS Sequoia / Tahoe dark aesthetic.
"""

DARK_THEME_QSS = """
/* Base Window & Global Fonts */
QMainWindow {
    background-color: #121215;
    color: #e4e4e7;
    font-family: ".AppleSystemUIFont", "Helvetica Neue", Arial;
}

QWidget {
    color: #e4e4e7;
    font-family: ".AppleSystemUIFont", "Helvetica Neue", Arial;
    font-size: 13px;
}

/* ToolBar & Header */
QToolBar {
    background-color: #18181b;
    border-bottom: 1px solid #27272a;
    padding: 6px 12px;
    spacing: 8px;
}

QToolBar QLabel {
    color: #f4f4f5;
    font-weight: 600;
    font-size: 14px;
}

/* Standard Buttons */
QPushButton {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #3f3f46;
    border-color: #52525b;
}

QPushButton:pressed {
    background-color: #18181b;
    border-color: #27272a;
}

QPushButton:disabled {
    background-color: #18181b;
    color: #71717a;
    border-color: #27272a;
}

/* Primary Action Button */
QPushButton#primaryBtn {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #0369a1;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #0369a1;
}

QPushButton#primaryBtn:pressed {
    background-color: #075985;
}

/* Combo Box (Device Selector) */
QComboBox {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 5px 12px;
    min-width: 150px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #52525b;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1f1f23;
    color: #f4f4f5;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    outline: none;
    padding: 4px;
}

/* Status Bar */
QStatusBar {
    background-color: #18181b;
    color: #a1a1aa;
    border-top: 1px solid #27272a;
    font-size: 12px;
    padding: 4px 10px;
}

QStatusBar QLabel {
    color: #a1a1aa;
    font-size: 12px;
}

/* Settings Dialog Window */
QDialog {
    background-color: #141417;
    color: #e4e4e7;
}

/* Section Header Labels */
QLabel.sectionHeader {
    color: #38bdf8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-left: 2px;
}

/* Modern Card Panels */
QFrame.settingsCard {
    background-color: #1c1c21;
    border: 1px solid #2d2d35;
    border-radius: 10px;
}

/* Card Separator Lines */
QFrame.cardSeparator {
    background-color: #27272e;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

/* Radio Buttons */
QRadioButton {
    spacing: 10px;
    color: #f4f4f5;
    font-size: 13px;
    min-height: 24px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #52525b;
    background-color: #27272a;
}

QRadioButton::indicator:hover {
    border-color: #38bdf8;
}

QRadioButton::indicator:checked {
    background-color: #0284c7;
    border: 3px solid #ffffff;
}

/* Checkboxes */
QCheckBox {
    spacing: 10px;
    color: #f4f4f5;
    font-size: 13px;
    min-height: 24px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #52525b;
    border-radius: 4px;
    background-color: #27272a;
}

QCheckBox::indicator:hover {
    border-color: #38bdf8;
}

QCheckBox::indicator:checked {
    background-color: #0284c7;
    border-color: #0284c7;
}

/* Horizontal Slider */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background-color: #2a2a30;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #0284c7;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 1px solid #94a3b8;
    width: 18px;
    height: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #ffffff;
    border-color: #38bdf8;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #27272e;
    background-color: #141417;
    border-radius: 8px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #1e1e24;
    color: #a1a1aa;
    padding: 8px 22px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #141417;
    color: #f4f4f5;
    border: 1px solid #27272e;
    border-bottom: 2px solid #0284c7;
}

QTabBar::tab:hover {
    color: #ffffff;
}

/* ScrollBar */
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3f3f46;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #52525b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
