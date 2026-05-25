param(
    [switch]$NoShortcut,
    [switch]$NoLaunchBat
)

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RepoDir "venv"
$BatPath = Join-Path $RepoDir "run_pyos.bat"

Write-Host "=== PyOS Installer ===" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: Check Python ----
$py = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python not found. Install Python 3.8+ from https://python.org" -ForegroundColor Red
    exit 1
}
$ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "Python $ver found at $($py.Source)" -ForegroundColor Green
$major, $minor = ($ver -split '\.')[0..1] | ForEach-Object { [int]$_ }
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
    Write-Host "Python 3.8+ required" -ForegroundColor Red
    exit 1
}

# ---- Step 2: Create venv ----
if (Test-Path $VenvDir) {
    Write-Host "Virtual environment exists at $VenvDir (skipping)" -ForegroundColor Yellow
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    & python -m venv $VenvDir
    Write-Host "Virtual environment created" -ForegroundColor Green
}

$pip = Join-Path $VenvDir "Scripts\pip.exe"

# ---- Step 3: Install requirements ----
Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $pip install --upgrade pip
& $pip install -r (Join-Path $RepoDir "requirements.txt")
Write-Host "Dependencies installed" -ForegroundColor Green

# ---- Step 4: Check ffmpeg ----
$ffmpeg = Get-Command "ffmpeg" -ErrorAction SilentlyContinue
if ($ffmpeg) {
    Write-Host "FFmpeg found" -ForegroundColor Green
} else {
    Write-Host "FFmpeg not found. Audio falls back to software tones." -ForegroundColor Yellow
    Write-Host "  Install via: winget install ffmpeg" -ForegroundColor Gray
}

# ---- Step 5: Create launch batch file ----
if (-not $NoLaunchBat) {
    @"
@echo off
cd /d "%~dp0"
call "%~dp0venv\Scripts\activate.bat"
python desktop.py
pause
"@ | Set-Content -Path $BatPath -Encoding ASCII
    Write-Host "Created launch script: run_pyos.bat" -ForegroundColor Green
}

# ---- Step 6: Desktop shortcut (optional) ----
if (-not $NoShortcut) {
    if (-not $NoLaunchBat -and (Test-Path $BatPath)) {
        $wshell = New-Object -ComObject WScript.Shell
        $sc = $wshell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\PyOS.lnk")
        $sc.TargetPath = "$env:SystemRoot\System32\cmd.exe"
        $sc.Arguments = "/c `"$BatPath`""
        $sc.WorkingDirectory = $RepoDir
        $sc.Description = "PyOS Desktop Simulator"
        $sc.Save()
        Write-Host "Desktop shortcut created" -ForegroundColor Green
    } else {
        Write-Host "Skipping shortcut (no launch batch to point to)" -ForegroundColor Yellow
    }
}

# ---- Done ----
Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To launch PyOS:" -ForegroundColor White
if (Test-Path $BatPath) {
    Write-Host "  run_pyos.bat" -ForegroundColor Gray
} else {
    Write-Host "  .\venv\Scripts\activate && python desktop.py" -ForegroundColor Gray
}
