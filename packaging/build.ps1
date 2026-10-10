param([string]$InnoCompiler = "")

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Create .venv and install the dev dependencies first (see README.md)."
}

& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --onedir --name BlurOutPDF --paths src --icon "packaging\app.ico" --add-data "src\blurout_pdf\assets\app.png;blurout_pdf\assets" run.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
& ".venv\Scripts\python.exe" "scripts\prepare_bundle.py"
if ($LASTEXITCODE -ne 0) { throw "Bundle notice verification failed." }

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
    throw "BlurOut PDF was packaged in dist\BlurOutPDF. Install Inno Setup and rerun with -InnoCompiler <path-to-ISCC.exe> to create the installer."
}
& $InnoCompiler "packaging\windows.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
