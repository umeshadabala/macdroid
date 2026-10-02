# MacDroid — Android on your Mac

<p align="center">
  <b>Lightweight, low-latency Android screen mirroring and desktop control for macOS.</b>
</p>

<p align="center">
  <a href="https://github.com/umeshadabala/macdroid"><img src="https://img.shields.io/badge/macOS-Sequoia%20%7C%20Tahoe-blue?style=flat-square" alt="macOS" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11%2B-green?style=flat-square" alt="Python" /></a>
  <a href="https://pypi.org/project/PySide6/"><img src="https://img.shields.io/badge/PySide6-6.6%2B-brightgreen?style=flat-square" alt="PySide6" /></a>
  <a href="https://ffmpeg.org/"><img src="https://img.shields.io/badge/Decoding-Hardware%20H.264-purple?style=flat-square" alt="Decoding" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-orange?style=flat-square" alt="License" /></a>
</p>

---

## Overview

**MacDroid** brings an Apple-like iPhone Mirroring experience to Android devices on macOS. Connect your Android phone to your Mac via USB and operate it smoothly using your Mac's trackpad, mouse, and keyboard directly from a native macOS window.

### Key Features

* **Live 60 FPS Video Streaming**: Hardware-accelerated H.264 video decoding via `libavcodec` (PyAV) for minimal frame latency.
* **Pixel-Accurate Touch & Mouse Control**:
  * Tap, double-tap, and long-press touch simulation.
  * Natural click-and-drag swiping.
  * **Normalized Trackpad Scrolling**: Custom inertia damping prevents trackpad scrolling from violently skipping through social media feeds, YouTube Shorts, or Reels.
  * Right-click mapped to Android Back.
  * Responsive coordinate mapping that maintains pixel accuracy across window resizing, maximize, and phone orientation changes.
* **Seamless Mac Keyboard Integration**:
  * Direct text entry in any Android app or search box.
  * Full support for Enter, Backspace, Delete, Tab, Space, Escape, and Arrow keys.
  * Mac shortcut mapping: `Cmd+C` (Copy), `Cmd+V` (Paste), `Cmd+A` (Select All), `Cmd+Z` (Undo).
* **Essential Android Navigation Toolbar**:
  * Dedicated `[ Back ]`, `[ Home ]`, and `[ Recents ]` buttons.
  * `[ Wake ]` button to wake the phone display without compromising lock-screen security.
  * `[ Screenshot ]` captures actual native Android resolution directly to `~/Pictures/MacDroid/`.
* **Zero Bloat & Professional UI**:
  * Native macOS Sequoia dark aesthetic.
  * Clean, fit-to-content buttons and clear status indicators.
  * Real-time performance HUD and coordinate diagnostic crosshairs for developers.

---

## Quick Install (One-Line Command)

Open your Mac Terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/umeshadabala/macdroid/main/install.sh | bash
```

The installer will:
1. Check for Homebrew, ADB, and FFmpeg (installing them automatically if missing).
2. Configure a clean Python virtual environment.
3. Install all required dependencies.
4. Create a global `macdroid` command in your terminal.

---

## Android Phone Setup (Step-by-Step from A to Z)

To use MacDroid, you only need to enable **USB Debugging** once on your Android phone.

### Step 1: Enable Developer Options
1. Open **Settings** on your Android phone.
2. Scroll to the bottom and tap **About Phone** (or **About Device**).
3. Find **Build Number** (on some devices like Xiaomi or Samsung, it may be under *Software Information*).
4. **Tap "Build Number" 7 times in a row.** You will see a notification saying: *"You are now a developer!"*

### Step 2: Enable USB Debugging
1. Go back to the main **Settings** menu.
2. Tap **System** > **Developer Options** (on some devices, found under *Additional Settings* or at the bottom of *Settings*).
3. Scroll down to the **Debugging** section.
4. Toggle **USB Debugging** to **ON**.
5. Tap **OK** on the confirmation dialog.

### Step 3: OEM-Specific Settings (If applicable)
* **Xiaomi / Redmi / POCO (MIUI / HyperOS)**:
  * Enable **USB Debugging (Security settings)** to allow MacDroid to send mouse and keyboard inputs. (Requires a Mi Account login).
* **OPPO / Realme / OnePlus (ColorOS / OxygenOS)**:
  * If touch events are blocked, ensure **Disable permission monitoring** is enabled in Developer Options.
* **Samsung Galaxy (One UI)**:
  * Standard USB Debugging works out of the box. If a USB mode popup appears, select **Transferring files / Android Auto**.

### Step 4: Connect Phone to Mac & Authorize
1. Connect your Android phone to your Mac using a USB-C or USB-A to USB-C cable.
2. Unlock your phone screen.
3. A popup prompt will appear on your phone: **"Allow USB debugging?"**
4. Check the box **"Always allow from this computer"** and tap **Allow**.

---

## Manual Installation & Running from Source

If you prefer to clone the repository and run manually:

### 1. Prerequisites
Ensure you have Homebrew and native tools installed:

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ADB and FFmpeg
brew install android-platform-tools ffmpeg python@3.11
```

### 2. Clone Repository
```bash
git clone https://github.com/umeshadabala/macdroid.git
cd macdroid
```

### 3. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Launch MacDroid
```bash
python run.py
```

---

## How to Use MacDroid

### Controlling your Phone
| Action | Mac Gesture / Input | Android Result |
| :--- | :--- | :--- |
| **Tap / Select** | Left Click | Touch / Tap |
| **Back** | Right Click or `Esc` or `[ Back ]` | Android Back (`KEYCODE_BACK`) |
| **Swipe / Drag** | Click and Drag | Touch Drag / Swipe Gesture |
| **Scroll Feeds** | Two-finger Trackpad Swipe | Smooth, controlled scroll without skipping videos |
| **Go Home** | `[ Home ]` button | Android Home (`KEYCODE_HOME`) |
| **App Switcher** | `[ Recents ]` button | Recent Apps overview (`KEYCODE_APP_SWITCH`) |
| **Type Text** | Type on Mac Keyboard | Enters text directly in focused input |
| **Copy / Paste** | `Cmd+C` / `Cmd+V` | Triggers Android Copy & Paste |
| **Select All** | `Cmd+A` | Selects all text in active Android input |
| **Undo** | `Cmd+Z` | Android Undo action |
| **Wake Display** | `[ Wake ]` button | Wakes phone screen (`KEYCODE_WAKEUP`) |
| **Take Screenshot** | `[ Screenshot ]` button | Captures native Android display to `~/Pictures/MacDroid/` |

---

## Settings & Customization

Click the **Settings** button in the top header to configure:

* **Display**:
  * **Target Framerate**: `30 FPS` or `60 FPS (Ultra Smooth)`.
  * **Quality Preset**: `Low (720p)`, `Balanced (1080p)`, or `High (1440p)`.
* **Input & Gestures**:
  * **Trackpad Scroll Sensitivity**: Adjust slider from `Low` to `High` to match your personal scrolling preference.
* **Diagnostics & Overlays**:
  * **Performance Overlay**: View real-time FPS and stream health metrics.
  * **Coordinate Crosshair HUD**: Inspect precise touch coordinates and visual tap feedback.
* **About Tab**:
  * View developer information, version details, and quick links to the project repository and creator profile.

---

## Architecture

```text
                  MacDroid (macOS)
                         │
          ┌──────────────┴──────────────┐
          │                             │
    USER INPUTS                    STREAM DECODER
 (Mouse / Keyboard)              (PyAV / libavcodec)
          │                             │
          ▼                             ▼
     ADB Protocol                  H.264 Stream
          │                             │
          └──────────────┬──────────────┘
                         │
                    USB Cable
                         │
                         ▼
                   Android Device
```

---

## Troubleshooting

### 1. "No Device" shown in header
* Ensure your USB cable supports data transfer (some cheap cables are charging-only).
* Open Mac Terminal and run `adb devices`. If the list is empty, reconnect the cable.
* Re-verify that **USB Debugging** is toggled ON in Developer Options.

### 2. Device says "Unauthorized"
* Unlock your phone screen.
* Disconnect and reconnect the USB cable.
* Tap **Allow** on the **"Allow USB debugging?"** prompt on your phone screen.

### 3. Screen stays black or phone is asleep
* Click the **[ Wake ]** button on the MacDroid toolbar, or press the physical power button on your phone.
* If your phone has a PIN/Pattern/Biometric lock, unlock it on the phone to allow display streaming.

### 4. Touch clicks not registering (Xiaomi / HyperOS)
* On Xiaomi devices, you must enable **USB debugging (Security settings)** in Developer Options.

---

## About the Developer

**MacDroid** is created and maintained by **Umesh Adabala**.

* **Website**: [umeshadabala.github.io](https://umeshadabala.github.io)
* **GitHub**: [@umeshadabala](https://github.com/umeshadabala)
* **Project Repository**: [github.com/umeshadabala/macdroid](https://github.com/umeshadabala/macdroid)

---

## License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute.
