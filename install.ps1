# Rocky.AI Installer for Windows
# Checks prerequisites, installs everything needed.
# Usage: .\install.ps1
# After install: Rocky

$ErrorActionPreference = "Stop"

function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  [X]  $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "  [i]  $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "  Rocky.AI Installer" -ForegroundColor Cyan
Write-Host "  Fully local AI - Zero external apps - One command to run" -ForegroundColor DarkGray
Write-Host ""

$RAM = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$errors = 0

Write-Host "  Checking prerequisites..." -ForegroundColor White
Write-Host ""

# 1) Python 3.10+
try {
    $pyVer = python --version 2>&1
    if ($pyVer -match "(\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 10) {
            Write-Ok "Python $pyVer"
        } else {
            Write-Fail "Python $pyVer found, need 3.10+"
            $errors++
        }
    }
} catch {
    Write-Fail "Python not found. Install from https://python.org"
    $errors++
}

# 2) pip
try {
    pip --version | Out-Null
    Write-Ok "pip"
} catch {
    Write-Fail "pip not found. Run: python -m ensurepip"
    $errors++
}

# 3) C compiler
$hasCompiler = $false
foreach ($comp in @("cl", "gcc", "clang")) {
    if (Get-Command $comp -ErrorAction SilentlyContinue) {
        Write-Ok "C compiler ($comp)"
        $hasCompiler = $true
        break
    }
}
if (-not $hasCompiler) {
    Write-Warn "No C compiler found. Install Visual Studio Build Tools"
    Write-Info "  https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Write-Info "  Select 'Desktop development with C++'"
    $errors++
}

# 4) git
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Ok "git"
} else {
    Write-Warn "git not found (optional)"
}

# 5) FFmpeg
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Ok "FFmpeg"
} else {
    Write-Warn "FFmpeg not found (optional, for video/audio)"
    Write-Info "Install: winget install ffmpeg"
}

# 6) RAM
if ($RAM -ge 8) {
    Write-Ok "RAM: ${RAM}GB"
} else {
    Write-Warn "RAM: ${RAM}GB (8GB+ recommended)"
}

Write-Host ""

if ($errors -gt 0) {
    Write-Fail "Missing $errors required prerequisite(s). Fix and re-run."
    exit 1
}

Write-Host "  Installing Rocky.AI..." -ForegroundColor White
Write-Host ""

if (Test-Path "pyproject.toml") {
    $content = Get-Content "pyproject.toml" -Raw
    if ($content -match "rocky-ai") {
        Write-Info "Installing from local source..."
        pip install -e .
    } else {
        Write-Info "Installing from GitHub..."
        pip install git+https://github.com/RoshanZameerMohammedShaik/Rocky.git
    }
} else {
    Write-Info "Installing from GitHub..."
    pip install git+https://github.com/RoshanZameerMohammedShaik/Rocky.git
}

Write-Host ""

if (Get-Command Rocky -ErrorAction SilentlyContinue) {
    Write-Ok "Rocky installed successfully!"
} else {
    Write-Warn "Rocky installed. You may need to restart your terminal."
}

Write-Host ""
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  To start Rocky, just type:"
Write-Host "    Rocky" -ForegroundColor White
Write-Host ""
Write-Host "  First run downloads the AI model (~2.2GB)." -ForegroundColor DarkGray
Write-Host ""
