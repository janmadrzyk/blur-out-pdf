param([string]$InnoCompiler = "")

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Create .venv and install the dev dependencies first (see README.md)."
}

& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --onedir --name Rectveil --paths src --icon "packaging\app.ico" --add-data "src\rectveil\assets\app.png;rectveil\assets" run.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

if (-not $InnoCompiler) {
    $found = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($found) { $InnoCompiler = $found.Source }
}
if (-not $InnoCompiler) {
    $locations = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    )
    foreach ($location in $locations) {
        if (Test-Path -LiteralPath $location) { $InnoCompiler = $location; break }
    }
}
if (-not $InnoCompiler) {
    throw "Rectveil was packaged in dist\Rectveil. Install Inno Setup and rerun with -InnoCompiler <path-to-ISCC.exe> to create the installer."
}
& $InnoCompiler "packaging\windows.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
