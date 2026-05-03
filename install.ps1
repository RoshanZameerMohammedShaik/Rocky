# Rocky.AI Installation Script for Windows
# Installs Rocky.AI with embedded local LLM — no Ollama, no external apps

$ErrorActionPreference = "Stop"

Write-Host @"

██████╗  ██████╗  ██████╗██╗  ██╗██╗   ██╗     █████╗ ██╗
██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝╚██╗ ██╔╝    ██╔══██╗██║
██████╔╝██║   ██║██║     █████╔╝  ╚████╔╝     ███████║██║
██╔══██╗██║   ██║██║     ██╔═██╗   ╚██╔╝      ██╔══██║██║
██║  ██║╚██████╔╝╚██████╗██║  ██╗   ██║    ██╗██║  ██║██║
╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═╝╚═╝  ╚═╝╚═╝

"@ -ForegroundColor Cyan

Write-Host "Rocky.AI Installer — Fully local AI, zero external apps" -ForegroundColor White
Write-Host ""

# Detect RAM
$RAM = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)

Write-Host "Detecting system..."
Write-Host "  OS: Windows"
Write-Host "  RAM: ${RAM}GB"
Write-Host ""

if ($RAM -lt 8) {
    Write-Host "Rocky.AI works best with 8GB+ RAM. You have ${RAM}GB." -ForegroundColor Yellow
    Write-Host "Will use the lightweight 1.7B model for your system." -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "==========================================================="
Write-Host "Installation Steps"
Write-Host "==========================================================="
Write-Host ""

# Step 1: Python
Write-Host "[1/3] Checking Python..." -ForegroundColor White
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  $pythonVersion found" -ForegroundColor Green
} catch {
    Write-Host "  Python not found." -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}

# Step 2: FFmpeg (optional)
Write-Host ""
Write-Host "[2/3] Checking FFmpeg (optional)..." -ForegroundColor White
$ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegPath) {
    Write-Host "  FFmpeg found — video/audio processing available" -ForegroundColor Green
} else {
    Write-Host "  FFmpeg not found. Video processing will be limited." -ForegroundColor Yellow
    Write-Host "  Install with: winget install ffmpeg" -ForegroundColor Yellow
}

# Step 3: Rocky.AI
Write-Host ""
Write-Host "[3/3] Installing Rocky.AI..." -ForegroundColor White
Write-Host "  This installs Rocky.AI with its embedded AI engine." -ForegroundColor Cyan
Write-Host "  No external AI applications will be installed." -ForegroundColor Cyan
Write-Host ""

try {
    pip install rocky-ai 2>$null
} catch {
    pip install llama-cpp-python httpx rich prompt-toolkit pyyaml beautifulsoup4
}
Write-Host "  Rocky.AI installed" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "==========================================================="
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "==========================================================="
Write-Host ""
Write-Host "To start Rocky.AI, run:"
Write-Host "  Rocky" -ForegroundColor White
Write-Host ""
Write-Host "On first run, Rocky.AI will download its AI model (~3GB)."
Write-Host "Everything runs locally — no cloud, no external apps."
Write-Host ""
