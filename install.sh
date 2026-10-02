#!/usr/bin/env bash
# ==============================================================================
# MacDroid Installer
# Android Screen Mirroring & Control for macOS
# Created by Umesh Adabala (https://github.com/umeshadabala)
# ==============================================================================

set -e

# Colors for terminal output
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${BLUE}${BOLD}"
echo "  __  __            _____             _     _ "
echo " |  \/  |          |  __ \           (_)   | |"
echo " | \  / | __ _  ___| |  | |_ __ ___   _  __| |"
echo " | |\/| |/ _\` |/ __| |  | | '__/ _ \ | |/ _\` |"
echo " | |  | | (_| | (__| |__| | | | (_) || | (_| |"
echo " |_|  |_|\__,_|\___|_____/|_|  \___/ |_|\__,_|"
echo -e "${RESET}"
echo -e "${CYAN}Android Screen Mirroring & Desktop Control for macOS${RESET}"
echo -e "Created by ${BOLD}Umesh Adabala${RESET} (https://umeshadabala.github.io)\n"

# 1. Verify macOS
OS="$(uname -s)"
if [ "$OS" != "Darwin" ]; then
    echo -e "${RED}Error: MacDroid is currently tailored for macOS. Detected: $OS${RESET}"
    exit 1
fi

# 2. Check Homebrew
if ! command -v brew &>/dev/null; then
    echo -e "${YELLOW}Warning: Homebrew not found. Please install Homebrew from https://brew.sh to automatically install dependencies.${RESET}"
fi

# 3. Check / Install ADB
if ! command -v adb &>/dev/null; then
    echo -e "${YELLOW}Android Debug Bridge (adb) not found.${RESET}"
    if command -v brew &>/dev/null; then
        echo -e "${BLUE}Installing android-platform-tools via Homebrew...${RESET}"
        brew install android-platform-tools
    else
        echo -e "${RED}Please install adb (Android platform tools) and ensure it is in your PATH.${RESET}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ ADB found:${RESET} $(command -v adb)"
fi

# 4. Check / Install FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo -e "${YELLOW}FFmpeg not found.${RESET}"
    if command -v brew &>/dev/null; then
        echo -e "${BLUE}Installing ffmpeg via Homebrew...${RESET}"
        brew install ffmpeg
    else
        echo -e "${RED}Please install ffmpeg (brew install ffmpeg).${RESET}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ FFmpeg found:${RESET} $(command -v ffmpeg)"
fi

# 5. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: Python 3 is required. Please install Python 3.11+ using 'brew install python'.${RESET}"
    exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo -e "${GREEN}✓ Python found:${RESET} $(python3 --version)"

# 6. Target Directory Setup
INSTALL_DIR="$HOME/.macdroid"
REPO_URL="https://github.com/umeshadabala/macdroid.git"

if [ -f "./run.py" ] && [ -d "./app" ]; then
    # Running from within the cloned repository
    APP_DIR="$(pwd)"
    echo -e "${BLUE}Installing from current directory:${RESET} $APP_DIR"
else
    # Running via curl | bash
    echo -e "${BLUE}Cloning MacDroid into:${RESET} $INSTALL_DIR"
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Updating existing installation...${RESET}"
        git -C "$INSTALL_DIR" pull --rebase || true
    else
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    APP_DIR="$INSTALL_DIR"
fi

cd "$APP_DIR"

# 7. Virtual Environment Setup
VENV_DIR="$APP_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}Creating Python virtual environment in .venv...${RESET}"
    python3 -m venv "$VENV_DIR"
fi

echo -e "${BLUE}Installing dependencies from requirements.txt...${RESET}"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements.txt --quiet

# 8. Create CLI Launcher command
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
LAUNCHER="$BIN_DIR/macdroid"

cat << 'EOF' > "$LAUNCHER"
#!/usr/bin/env bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")"
APP_DIR="${HOME}/.macdroid"
if [ ! -d "$APP_DIR" ]; then
    APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/run.py" "$@"
EOF

# Ensure real path resolution for macOS
cat << EOF > "$LAUNCHER"
#!/usr/bin/env bash
APP_DIR="$APP_DIR"
exec "\$APP_DIR/.venv/bin/python" "\$APP_DIR/run.py" "\$@"
EOF

chmod +x "$LAUNCHER"

# Add ~/.local/bin to PATH if not already present
SHELL_RC=""
case "$SHELL" in
    */zsh) SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="$HOME/.bash_profile" ;;
esac

if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    fi
fi

# 9. Success Output
echo ""
echo -e "${GREEN}${BOLD}======================================================${RESET}"
echo -e "${GREEN}${BOLD}         MacDroid Installed Successfully!             ${RESET}"
echo -e "${GREEN}${BOLD}======================================================${RESET}"
echo ""
echo -e "To start MacDroid right now, run:"
echo -e "  ${CYAN}${BOLD}$APP_DIR/.venv/bin/python $APP_DIR/run.py${RESET}"
echo ""
echo -e "Or simply run:"
echo -e "  ${CYAN}${BOLD}macdroid${RESET}"
echo ""
echo -e "${YELLOW}Next Steps on your Android Device:${RESET}"
echo -e "  1. Connect your phone via USB."
echo -e "  2. Enable Developer Options & USB Debugging."
echo -e "  3. Accept the 'Allow USB debugging' prompt on your phone screen."
echo ""
echo -e "Developer: ${BOLD}Umesh Adabala${RESET} (https://umeshadabala.github.io)"
echo -e "GitHub:    ${BOLD}https://github.com/umeshadabala/macdroid${RESET}\n"
