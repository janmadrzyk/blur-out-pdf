param([Parameter(Mandatory = $true)][string]$InnoCompiler)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Missing project Python environment." }
$versionSource = Join-Path $projectRoot "src\blurout_pdf\_version.py"
$candidateVersion = (& $python -c "import runpy, sys; print(runpy.run_path(sys.argv[1])['VERSION'])" $versionSource)
if ($LASTEXITCODE -ne 0) { throw "Could not read the application version." }
$candidateVersion = $candidateVersion.Trim()
$candidate = Join-Path $projectRoot "dist\BlurOutPDF-Setup-$candidateVersion.exe"
if (-not (Test-Path -LiteralPath $InnoCompiler)) { throw "Inno Setup compiler not found." }
if (-not (Test-Path -LiteralPath $candidate)) { throw "Build the $candidateVersion installer first." }
if ((Get-Item -LiteralPath $candidate).VersionInfo.ProductVersion.Trim() -ne $candidateVersion) {
    throw "The release candidate installer does not report version $candidateVersion."
}

# Keep synthetic installers out of dist/ so they cannot be mistaken for releases.
$runRoot = Join-Path $projectRoot (".pytest-temp\issue4-fixtures\" + [guid]::NewGuid().ToString("N"))
$outputRoot = Join-Path $runRoot "installers"
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

foreach ($fixtureVersion in @("0.9.0", "1.0.0")) {
    $fixtureRoot = Join-Path $runRoot ("source-" + $fixtureVersion)
    New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null
    foreach ($name in @("src", "scripts", "packaging", "licenses", "run.py", "LICENSE", "THIRD_PARTY_NOTICES.md")) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $name) -Destination $fixtureRoot -Recurse
    }
    $versionFile = Join-Path $fixtureRoot "src\blurout_pdf\_version.py"
    Set-Content -LiteralPath $versionFile -Value "VERSION = `"$fixtureVersion`"" -Encoding utf8

    Push-Location -LiteralPath $fixtureRoot
    try {
        & $python "scripts\release_version.py" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Version generation failed for $fixtureVersion." }
        & $python -m PyInstaller --log-level WARN --noconfirm --windowed --onedir --name BlurOutPDF --paths src --icon "packaging\app.ico" --version-file "build\version_info.txt" --add-data "src\blurout_pdf\assets\app.png;blurout_pdf\assets" run.py
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $fixtureVersion." }
        & $python "scripts\prepare_bundle.py"
        if ($LASTEXITCODE -ne 0) { throw "Bundle preparation failed for $fixtureVersion." }
        & $python "scripts\check_bundle_imports.py"
        if ($LASTEXITCODE -ne 0) { throw "Bundled Qt modules could not load for $fixtureVersion." }
        & $InnoCompiler "/DAppVersion=$fixtureVersion" "/O$outputRoot" "/FTEST-ONLY-BlurOutPDF-Setup-$fixtureVersion" "/Qp" "packaging\windows.iss"
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed for $fixtureVersion." }
    }
    finally {
        Pop-Location
    }
}

Copy-Item -LiteralPath $candidate -Destination $outputRoot
& $python (Join-Path $projectRoot "scripts\create_installer_samples.py") $outputRoot
if ($LASTEXITCODE -ne 0) { throw "Could not create synthetic Open with samples." }
Get-ChildItem -LiteralPath $outputRoot -Filter "*.exe" |
    ForEach-Object { "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash, $_.Name } |
    Set-Content -LiteralPath (Join-Path $outputRoot "SHA256.txt") -Encoding ascii
Write-Output $outputRoot
