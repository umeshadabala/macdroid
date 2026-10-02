"""
ADB Manager for PhoneConnect.
Locates ADB, manages commands, and communicates with connected Android devices.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.logger import get_logger

log = get_logger("adb")


@dataclass
class AndroidDevice:
    serial: str
    state: str  # "device", "unauthorized", "offline", "connecting", "no permissions"
    model: str = "Android Device"
    product: str = ""
    device_name: str = ""
    transport_id: str = ""
    connection_type: str = "usb"  # "usb" or "tcpip"
    screen_width: int = 1080
    screen_height: int = 2400

    @property
    def is_ready(self) -> bool:
        return self.state == "device"

    @property
    def display_title(self) -> str:
        if self.model and self.model != "unknown":
            # Clean up underscores often present in model strings
            clean_model = self.model.replace("_", " ")
            return f"{clean_model} ({self.connection_type.upper()})"
        return f"{self.serial} ({self.connection_type.upper()})"

    @property
    def status_message(self) -> str:
        if self.state == "device":
            return f"Connected: {self.display_title}"
        elif self.state == "unauthorized":
            return "Please unlock your Android phone and allow USB debugging."
        elif self.state == "offline":
            return "Device is offline. Please reconnect USB cable."
        elif self.state == "no permissions":
            return "No permissions to access USB device. Check udev / macOS permissions."


class ADBManager:
    """Provides an interface to the Android Debug Bridge executable."""

    KNOWN_PATHS = [
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
        str(Path.home() / "Library/Android/sdk/platform-tools/adb"),
    ]

    def __init__(self, custom_path: Optional[str] = None) -> None:
        self.custom_path = custom_path
        self.adb_path = self.locate_adb()

    def locate_adb(self) -> Optional[str]:
        """Find the ADB executable on the host system."""
        # 1. User specified custom path
        if self.custom_path and os.path.isfile(self.custom_path) and os.access(self.custom_path, os.X_OK):
            log.info("Using custom configured ADB: %s", self.custom_path)
            return self.custom_path

        # 2. PATH resolution
        which_adb = shutil.which("adb")
        if which_adb and os.access(which_adb, os.X_OK):
            log.info("Found ADB in PATH: %s", which_adb)
            return which_adb

        # 3. Environment variables (ANDROID_HOME, ANDROID_SDK_ROOT)
        for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
            val = os.getenv(env_var)
            if val:
                candidate = Path(val) / "platform-tools" / "adb"
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    log.info("Found ADB from %s: %s", env_var, candidate)
                    return str(candidate)

        # 4. Standard known directories
        for path in self.KNOWN_PATHS:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                log.info("Found ADB in known path: %s", path)
                return path

        log.warning("ADB executable was not found on the system.")
        return None

    def is_available(self) -> bool:
        """Check if a valid ADB executable is available."""
        if not self.adb_path:
            self.adb_path = self.locate_adb()
        return self.adb_path is not None

    def run_command(self, args: List[str], timeout: float = 10.0) -> Tuple[int, str, str]:
        """Execute an ADB command synchronously."""
        if not self.is_available() or not self.adb_path:
            return -1, "", "ADB was not found. Please install Android Platform Tools."

        cmd = [self.adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            log.error("ADB command timed out: %s", " ".join(cmd))
            return -1, "", f"Command timed out: {' '.join(cmd)}"
        except Exception as e:
            log.error("Failed to execute ADB command (%s): %s", " ".join(cmd), e)
            return -1, "", str(e)

    def get_version(self) -> Optional[str]:
        """Get the installed ADB version string."""
        code, out, _ = self.run_command(["version"])
        if code == 0 and out:
            lines = out.splitlines()
            return lines[0] if lines else out
        return None

    def list_devices(self) -> List[AndroidDevice]:
        """List all currently detected Android devices via `adb devices -l`."""
        code, out, err = self.run_command(["devices", "-l"])
        if code != 0:
            log.error("adb devices failed: %s", err)
            return []

        devices: List[AndroidDevice] = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices attached") or line.startswith("*"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            state = parts[1]

            # Parse key-values like product:redfin model:Pixel_5 device:redfin transport_id:1
            details: Dict[str, str] = {}
            for item in parts[2:]:
                if ":" in item:
                    k, v = item.split(":", 1)
                    details[k] = v

            connection_type = "tcpip" if ":" in serial and "." in serial else "usb"
            model = details.get("model", "Android Device")
            product = details.get("product", "")
            device_name = details.get("device", "")
            transport_id = details.get("transport_id", "")

            dev = AndroidDevice(
                serial=serial,
                state=state,
                model=model,
                product=product,
                device_name=device_name,
                transport_id=transport_id,
                connection_type=connection_type,
            )

            # If device is ready and model wasn't provided in the line, fetch details
            if dev.is_ready and (dev.model == "Android Device" or dev.model == "unknown"):
                props = self.get_device_props(dev.serial)
                if "ro.product.model" in props:
                    dev.model = props["ro.product.model"]

            # Query resolution
            if dev.is_ready:
                w, h = self.get_device_resolution(dev.serial)
                if w > 0 and h > 0:
                    dev.screen_width = w
                    dev.screen_height = h

            devices.append(dev)

        return devices

    def get_device_props(self, serial: str) -> Dict[str, str]:
        """Retrieve key Android build properties."""
        code, out, _ = self.run_command(["-s", serial, "shell", "getprop"], timeout=4.0)
        if code != 0 or not out:
            return {}

        props = {}
        for line in out.splitlines():
            m = re.match(r"\[(.*?)\]:\s*\[(.*?)\]", line.strip())
            if m:
                props[m.group(1)] = m.group(2)
        return props

    def get_device_resolution(self, serial: str) -> Tuple[int, int]:
        """Fetch physical screen dimensions via `wm size`."""
        code, out, _ = self.run_command(["-s", serial, "shell", "wm", "size"], timeout=3.0)
        if code == 0 and out:
            # Output format: "Physical size: 1080x2400" or with "Override size: ..."
            m = re.search(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", out)
            if m:
                return int(m.group(1)), int(m.group(2))
        return 1080, 2400

    def wake_device(self, serial: str) -> bool:
        """Wake up device screen (KEYCODE_WAKEUP = 224)."""
        code, _, _ = self.run_command(["-s", serial, "shell", "input", "keyevent", "224"])
        return code == 0

    def unlock_device(self, serial: str) -> bool:
        """Dismiss keyguard (KEYCODE_MENU = 82)."""
        code, _, _ = self.run_command(["-s", serial, "shell", "input", "keyevent", "82"])
        return code == 0

    def push_file(self, serial: str, local_path: str, remote_dest: str = "/sdcard/Download/") -> Tuple[bool, str]:
        """Push a file to the Android device."""
        if not os.path.exists(local_path):
            return False, f"File does not exist: {local_path}"

        filename = os.path.basename(local_path)
        target = remote_dest.rstrip("/") + "/" + filename
        code, out, err = self.run_command(["-s", serial, "push", local_path, target], timeout=60.0)
        if code == 0:
            return True, target
        return False, err or out

    def install_apk(self, serial: str, apk_path: str) -> Tuple[bool, str]:
        """Install an APK onto the connected device."""
        code, out, err = self.run_command(["-s", serial, "install", "-r", apk_path], timeout=90.0)
        if code == 0 and "Success" in out:
            return True, "APK successfully installed"
        return False, err or out

    def inject_keyevent(self, serial: str, keycode: int) -> bool:
        """Inject an Android keycode (e.g. 4 for BACK, 3 for HOME)."""
        code, _, _ = self.run_command(["-s", serial, "shell", "input", "keyevent", str(keycode)], timeout=2.0)
        return code == 0

    def inject_text(self, serial: str, text: str) -> bool:
        """Inject textual input via `input text`."""
        # Escape spaces and shell-sensitive characters
        escaped = text.replace(" ", "%s").replace("&", "\\&").replace("'", "\\'").replace('"', '\\"')
        code, _, _ = self.run_command(["-s", serial, "shell", "input", "text", escaped], timeout=2.0)
        return code == 0

    def inject_tap(self, serial: str, x: int, y: int) -> bool:
        """Simulate a touch tap at (x, y)."""
        code, _, _ = self.run_command(["-s", serial, "shell", "input", "tap", str(x), str(y)], timeout=2.0)
        return code == 0

    def inject_swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> bool:
        """Simulate a swipe from (x1, y1) to (x2, y2)."""
        code, _, _ = self.run_command(
            ["-s", serial, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
            timeout=3.0
        )
        return code == 0

    def take_screenshot(self, serial: str, dest_dir: Optional[str] = None) -> Tuple[bool, str]:
        """Take native-resolution screenshot on device and save directly to Mac."""
        if not dest_dir:
            dest_dir = str(Path.home() / "Pictures" / "MacDroid")

        os.makedirs(dest_dir, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"MacDroid_{timestamp}.png"
        target_path = os.path.join(dest_dir, filename)

        # Avoid collision
        counter = 1
        base, ext = os.path.splitext(target_path)
        while os.path.exists(target_path):
            target_path = f"{base}_{counter}{ext}"
            counter += 1

        try:
            with open(target_path, "wb") as f:
                cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
                res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=10.0)
            if res.returncode == 0 and os.path.getsize(target_path) > 1000:
                return True, target_path
            return False, res.stderr.decode("utf-8", errors="replace")
        except Exception as e:
            return False, str(e)

    def is_screen_awake(self, serial: str) -> bool:
        """Check if phone screen is awake (not sleeping/off)."""
        code, out, _ = self.run_command(["-s", serial, "shell", "dumpsys", "power"], timeout=2.0)
        if code == 0 and out:
            if "mWakefulness=Awake" in out or "Display Power: state=ON" in out:
                return True
            if "mWakefulness=Asleep" in out or "Display Power: state=OFF" in out:
                return False
        return True

    def get_battery_info(self, serial: str) -> Dict[str, str]:
        """Query battery percentage and charging status."""
        code, out, _ = self.run_command(["-s", serial, "shell", "dumpsys", "battery"], timeout=3.0)
        info = {"level": "Unknown", "status": "Unknown", "temperature": "Unknown"}
        if code == 0 and out:
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("level:"):
                    info["level"] = line.split(":", 1)[1].strip() + "%"
                elif line.startswith("status:"):
                    status_code = line.split(":", 1)[1].strip()
                    info["status"] = "Charging" if status_code == "2" else "Discharging"
                elif line.startswith("temperature:"):
                    raw_temp = line.split(":", 1)[1].strip()
                    try:
                        info["temperature"] = f"{float(raw_temp)/10.0:.1f}°C"
                    except Exception:
                        pass
        return info


