#!/bin/bash
# Rocky.AI Installation Script
# Installs Rocky.AI with embedded local LLM — no Ollama, no external apps

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# ASCII Art
echo -e "${CYAN}"
cat << 'EOF'
██████╗  ██████╗  ██████╗██╗  ██╗██╗   ██╗     █████╗ ██╗
██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝╚██╗ ██╔╝    ██╔══██╗██║
██████╔╝██║   ██║██║     █████╔╝  ╚████╔╝     ███████║██║
██╔══██╗██║   ██║██║     ██╔═██╗   ╚██╔╝      ██╔══██║██║
██║  ██║╚██████╔╝╚██████╗██║  ██╗   ██║    ██╗██║  ██║██║
╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═╝╚═╝  ╚═╝╚═╝
EOF
echo -e "${NC}"
echo -e "${BOLD}Rocky.AI Installer${NC} — Fully local AI, zero external apps"
echo ""

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Detect RAM
detect_ram() {
    if [[ "$(detect_os)" == "macos" ]]; then
        sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}'
    else
        free -g | awk '/^Mem:/{print $2}'
    fi
}

# Check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print helpers
print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${CYAN}ℹ${NC} $1"; }

main() {
    OS=$(detect_os)
    RAM=$(detect_ram)

    echo "Detecting system..."
    echo -e "  OS: ${BOLD}$OS${NC}"
    echo -e "  RAM: ${BOLD}${RAM}GB${NC}"

    if [[ "$RAM" -lt 8 ]]; then
        print_warning "Rocky.AI works best with 8GB+ RAM. You have ${RAM}GB."
        print_info "Will use the lightweight 1.7B model for your system."
        echo ""
    fi

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "Installation Steps"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Step 1: Python
    echo -e "${BOLD}[1/3] Checking Python...${NC}"
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        if [[ "$PYTHON_MAJOR" -ge 3 && "$PYTHON_MINOR" -ge 10 ]]; then
            print_status "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.10+ required. Found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.10 or later."
        exit 1
    fi

    # Step 2: FFmpeg (optional)
    echo ""
    echo -e "${BOLD}[2/3] Checking FFmpeg (optional)...${NC}"
    if command_exists ffmpeg; then
        print_status "FFmpeg found — video/audio processing available"
    else
        print_warning "FFmpeg not found. Video processing will be limited."
        if [[ "$OS" == "macos" ]]; then
            print_info "Install with: brew install ffmpeg"
        elif [[ "$OS" == "linux" ]]; then
            print_info "Install with: sudo apt install ffmpeg"
        fi
    fi

    # Step 3: Rocky.AI
    echo ""
    echo -e "${BOLD}[3/3] Installing Rocky.AI...${NC}"
    print_info "This installs Rocky.AI with its embedded AI engine."
    print_info "No external AI applications will be installed."
    echo ""

    pip3 install --user rocky-ai 2>/dev/null || pip3 install --user -e . 2>/dev/null || {
        print_info "Installing from source..."
        pip3 install --user llama-cpp-python httpx rich prompt-toolkit pyyaml beautifulsoup4
        print_status "Dependencies installed"
    }
    print_status "Rocky.AI installed"

    # Done
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${GREEN}${BOLD}Installation Complete!${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "To start Rocky.AI, run:"
    echo -e "  ${BOLD}Rocky${NC}"
    echo ""
    echo "On first run, Rocky.AI will download its AI model (~3GB)."
    echo "Everything runs locally — no cloud, no external apps."
    echo ""
}

main "$@"
