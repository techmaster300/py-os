param(
    [switch]$NoShortcut,
    [switch]$NoLaunchBat,
    [string]$CloneDir = "$env:USERPROFILE\py-os"
)

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "PyOS Installer"

Write-Host "===== PyOS Installer =====" -ForegroundColor Cyan
Write-Host ""

# ---- Detect if already in repo ----
$InRepo = Test-Path (Join-Path $PSScriptRoot "desktop.py")
if ($InRepo) {
    $RepoDir = $PSScriptRoot
    Write-Host "Detected PyOS repository at: $RepoDir" -ForegroundColor Green
} else {
    $RepoDir = $CloneDir
    Write-Host "Will clone PyOS to: $RepoDir" -ForegroundColor Yellow
}
Write-Host ""

# ---- Ensure winget ----
$winget = Get-Command "winget" -ErrorAction SilentlyContinue
if (-not $winget) {
    Write-Host "winget not found. Install the App Installer package from the Microsoft Store." -ForegroundColor Red
    exit 1
}

# ---- Helper: install via winget ----
function Install-WithWinget {
    param([string]$Name, [string]$WingetId)
    Write-Host "  -> Installing $Name..." -ForegroundColor Cyan
    & winget install --id $WingetId --exact --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  -> Failed to auto-install $Name. Install it manually." -ForegroundColor Red
        return $false
    }
    Write-Host "  -> $Name installed" -ForegroundColor Green
    return $true
}

# ---- Helper: refresh PATH from registry ----
function Update-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

# ---- 1. Git ----
$git = Get-Command "git" -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "[1/6] Git not found. Installing..." -ForegroundColor Yellow
    Install-WithWinget "Git" "Git.Git"
    Update-Path
    $git = Get-Command "git" -ErrorAction SilentlyContinue
}
if ($git) {
    Write-Host "[1/6] Git: $(& git --version)" -ForegroundColor Green
} else {
    Write-Host "[1/6] Git is required. Install from https://git-scm.com" -ForegroundColor Red
    exit 1
}

# ---- 2. Python ----
$py = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[2/6] Python not found. Installing..." -ForegroundColor Yellow
    Install-WithWinget "Python 3.12" "Python.Python.3.12"
    Update-Path
    $py = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $py) {
        # winget install may not refresh session PATH fully; probe common install paths
        $candidates = @(
            "$env:ProgramFiles\Python312\python.exe",
            "$env:LocalAppData\Programs\Python\Python312\python.exe",
            "$env:LocalAppData\Microsoft\WindowsApps\python.exe"
        )
        foreach ($c in $candidates) {
            if (Test-Path $c) { $py = Get-Command $c; break }
        }
    }
}
if (-not $py) {
    Write-Host "[2/6] Python is required. Install from https://python.org" -ForegroundColor Red
    exit 1
}
$pyPath = $py.Source
$ver = & $pyPath -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "[2/6] Python $ver" -ForegroundColor Green
$major, $minor = ($ver -split '\.')[0..1] | ForEach-Object { [int]$_ }
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
    Write-Host "  -> Python 3.8+ required, got $major.$minor" -ForegroundColor Red
    exit 1
}

# ---- 3. Clone repo ----
if (-not $InRepo) {
    Write-Host "[3/6] Cloning PyOS repository..." -ForegroundColor Cyan
    if (Test-Path $RepoDir) {
        Write-Host "  -> Directory $RepoDir already exists." -ForegroundColor Yellow
    } else {
        & git clone https://github.com/techmaster300/py-os.git $RepoDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  -> Clone failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "  -> Repository cloned" -ForegroundColor Green
    }
} else {
    Write-Host "[3/6] Already inside repository (skipping clone)" -ForegroundColor Green
}

# ---- 4. FFmpeg ----
$ffmpeg = Get-Command "ffmpeg" -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "[4/6] FFmpeg not found. Installing..." -ForegroundColor Yellow
    Install-WithWinget "FFmpeg" "Gyan.FFmpeg"
    Update-Path
    $ffmpeg = Get-Command "ffmpeg" -ErrorAction SilentlyContinue
}
if ($ffmpeg) {
    Write-Host "[4/6] FFmpeg: $(& ffmpeg -version | Select-Object -First 1)" -ForegroundColor Green
} else {
    Write-Host "[4/6] FFmpeg not found (optional — some sounds use software tones)" -ForegroundColor Yellow
}

# ---- 5. Virtual environment and dependencies ----
$VenvDir = Join-Path $RepoDir "venv"
if (Test-Path $VenvDir) {
    Write-Host "[5/6] Virtual environment exists (skipping creation)" -ForegroundColor Yellow
} else {
    Write-Host "[5/6] Creating virtual environment..." -ForegroundColor Cyan
    & $pyPath -m venv $VenvDir
    Write-Host "  -> Virtual environment created" -ForegroundColor Green
}

$pip = Join-Path $VenvDir "Scripts\pip.exe"
Write-Host "[5/6] Installing Python packages..." -ForegroundColor Cyan
& $pip install --upgrade pip 2>&1 | Out-Null
& $pip install -r (Join-Path $RepoDir "requirements.txt")
if ($LASTEXITCODE -eq 0) {
    Write-Host "  -> Packages installed" -ForegroundColor Green
} else {
    Write-Host "  -> Package install had warnings (check output above)" -ForegroundColor Yellow
}

# ---- 6. Launcher and shortcut ----
$BatPath = Join-Path $RepoDir "run_pyos.bat"

if (-not $NoLaunchBat) {
    Write-Host "[6/6] Creating launch script..." -ForegroundColor Cyan
    @"
@echo off
cd /d "%~dp0"
call "%~dp0venv\Scripts\activate.bat"
python desktop.py
pause
"@ | Set-Content -Path $BatPath -Encoding ASCII
    Write-Host "  -> Created run_pyos.bat" -ForegroundColor Green
}

if (-not $NoShortcut -and (Test-Path $BatPath)) {
    Write-Host "[6/6] Creating desktop shortcut..." -ForegroundColor Cyan
    $wshell = New-Object -ComObject WScript.Shell
    $sc = $wshell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\PyOS.lnk")
    $sc.TargetPath = "$env:SystemRoot\System32\cmd.exe"
    $sc.Arguments = "/c `"$BatPath`""
    $sc.WorkingDirectory = $RepoDir
    $sc.Description = "PyOS Desktop Simulator"
    $sc.Save()
    Write-Host "  -> PyOS shortcut created" -ForegroundColor Green
}

# ---- Done ----
Write-Host ""
Write-Host "===== Installation complete =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "To launch PyOS:" -ForegroundColor White
if (Test-Path $BatPath) {
    Write-Host "  run_pyos.bat" -ForegroundColor Gray
} else {
    Write-Host "  cd $RepoDir" -ForegroundColor Gray
    Write-Host "  .\venv\Scripts\activate" -ForegroundColor Gray
    Write-Host "  python desktop.py" -ForegroundColor Gray
}
