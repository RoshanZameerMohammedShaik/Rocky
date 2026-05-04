#!/bin/bash
# Rocky.Ai Installer
# Checks prerequisites, installs everything needed, configures Rocky.
# Usage: ./install.sh  or  curl -sSL <url> | bash
# After install, just type: Rocky

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

ok()   { echo -e "  ${GREEN}\xE2\x9C\x94${NC} $1"; }
warn() { echo -e "  ${YELLOW}\xE2\x9A\xA0${NC} $1"; }
fail() { echo -e "  ${RED}\xE2\x9C\x98${NC} $1"; }
info() { echo -e "  ${CYAN}\xE2\x84\xB9${NC} $1"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
    case "$OSTYPE" in
        darwin*)  echo "macos" ;;
        linux*)   echo "linux" ;;
        msys*|cygwin*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

detect_ram() {
    if [[ "$(detect_os)" == "macos" ]]; then
        sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024/1024)}'
    else
        free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "8"
    fi
}

echo ""
echo -e "${CYAN}${BOLD}"
echo "  ____            _            _    ___"
echo " |  _ \\ ___   ___| | ___   _  / \\  |_ _|"
echo " | |_) / _ \\ / __| |/ / | | |/ _ \\  | |"
echo " |  _ < (_) | (__|   <| |_| / ___ \\ | |"
echo " |_| \\_\\___/ \\___|_|\\_\\\\__, /_/   \\_\\___|"
echo "                       |___/"
echo -e "${NC}"
echo -e "  ${BOLD}Rocky.Ai Installer${NC}"
echo -e "  ${DIM}Fully local AI \u2022 Zero external apps \u2022 One command to run${NC}"
echo ""
echo -e "  ${DIM}\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80${NC}"
echo ""

OS=$(detect_os)
RAM=$(detect_ram)
ERRORS=0

echo -e "  ${BOLD}Checking prerequisites...${NC}"
echo ""

# 1) Python 3.10+
if command_exists python3; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
        ok "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION found, but 3.10+ required"
        ERRORS=$((ERRORS + 1))
    fi
elif command_exists python; then
    PY_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
        ok "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION found, but 3.10+ required"
        ERRORS=$((ERRORS + 1))
    fi
else
    fail "Python not found. Install Python 3.10+ from https://python.org"
    ERRORS=$((ERRORS + 1))
fi

# 2) pip
if command_exists pip3 || command_exists pip; then
    ok "pip"
else
    fail "pip not found. Install pip: python3 -m ensurepip"
    ERRORS=$((ERRORS + 1))
fi

# 3) C compiler (needed for llama-cpp-python)
if command_exists gcc || command_exists cc || command_exists clang; then
    COMPILER=$(command -v clang || command -v gcc || command -v cc)
    ok "C compiler ($(basename "$COMPILER"))"
else
    if [[ "$OS" == "macos" ]]; then
        warn "No C compiler found. Installing Xcode Command Line Tools..."
        xcode-select --install 2>/dev/null || true
        info "Run this installer again after Xcode tools finish installing"
        exit 1
    else
        fail "No C compiler found. Install: sudo apt install build-essential (Ubuntu) or equivalent"
        ERRORS=$((ERRORS + 1))
    fi
fi

# 4) git (optional but recommended)
if command_exists git; then
    ok "git"
else
    warn "git not found (optional, needed for source install)"
fi

# 5) FFmpeg (optional)
if command_exists ffmpeg; then
    ok "FFmpeg (video/audio processing available)"
else
    warn "FFmpeg not found (optional, for video/audio)"
    if [[ "$OS" == "macos" ]]; then
        info "Install with: brew install ffmpeg"
    elif [[ "$OS" == "linux" ]]; then
        info "Install with: sudo apt install ffmpeg"
    fi
fi

# 6) RAM check
if [[ "$RAM" -ge 8 ]]; then
    ok "RAM: ${RAM}GB"
else
    warn "RAM: ${RAM}GB (8GB+ recommended, will use lightweight model)"
fi

echo ""

# Abort if critical prerequisites missing
if [[ $ERRORS -gt 0 ]]; then
    fail "Missing $ERRORS required prerequisite(s). Fix the issues above and re-run."
    exit 1
fi

echo -e "  ${BOLD}Installing Rocky.Ai...${NC}"
echo ""

# Detect if we're inside the Rocky repo (has pyproject.toml)
if [[ -f "pyproject.toml" ]] && grep -q "rocky-ai" pyproject.toml 2>/dev/null; then
    info "Installing from local source..."
    PIP_CMD=$(command -v pip3 || command -v pip)
    $PIP_CMD install -e . 2>&1 | tail -3
else
    info "Installing from GitHub..."
    PIP_CMD=$(command -v pip3 || command -v pip)
    $PIP_CMD install git+https://github.com/RoshanZameerMohammedShaik/Rocky.git 2>&1 | tail -3
fi

echo ""

# Verify installation
if command_exists Rocky; then
    ok "Rocky installed successfully!"
elif command_exists rocky; then
    ok "Rocky installed (as 'rocky')"
else
    ROCKY_PATH=$(python3 -c "import site; print(site.getusersitepackages().replace('lib/python','bin/Rocky'))" 2>/dev/null || echo "")
    if [[ -f "$ROCKY_PATH" ]]; then
        ok "Rocky installed (you may need to add ~/.local/bin to PATH)"
    else
        warn "Rocky installed but not in PATH. Try: python3 -m rocky.cli"
    fi
fi

# Step 4: Download AI model based on system hardware
echo ""
echo -e "  ${BOLD}Detecting hardware and downloading AI model...${NC}"
echo ""
PYTHON_CMD=$(command -v python3 || command -v python)
$PYTHON_CMD -m rocky.setup_model

echo ""
echo -e "  ${DIM}\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80${NC}"
echo ""
echo -e "  ${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo -e "  To start Rocky, just type:"
echo -e "    ${BOLD}Rocky${NC}"
echo ""
echo -e "  ${DIM}First run downloads the AI model (~2.2GB). After that, fully offline.${NC}"
echo ""
