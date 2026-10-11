#define AppName "BlurOut PDF"
#ifndef AppVersion
  #error AppVersion must be passed by the build script
#endif

[Setup]
AppId=BlurOutPDF.PDF.Reader
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
UsePreviousAppDir=yes
DisableDirPage=auto
UninstallLogMode=append
AppMutex=Local\BlurOutPDF.PDF.Reader
CloseApplications=yes
RestartApplications=no
OutputDir=..\dist
OutputBaseFilename=BlurOutPDF-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ChangesAssociations=yes
UninstallDisplayIcon={app}\BlurOutPDF.exe
SetupIconFile=app.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[CustomMessages]
english.DesktopIcon=Create a desktop shortcut
polish.DesktopIcon=Utwórz skrót na pulpicie
english.AdditionalShortcuts=Additional shortcuts:
polish.AdditionalShortcuts=Dodatkowe skróty:
english.LaunchApp=Launch BlurOut PDF
polish.LaunchApp=Uruchom BlurOut PDF
english.AlreadyInstalled=BlurOut PDF %1 is already installed. No changes were made.
polish.AlreadyInstalled=BlurOut PDF %1 jest już zainstalowany. Nie wprowadzono zmian.
english.DowngradeBlocked=BlurOut PDF %1 is installed. This installer contains the older version %2, so no changes were made.
polish.DowngradeBlocked=Zainstalowano BlurOut PDF %1. Ten instalator zawiera starszą wersję %2, więc nie wprowadzono zmian.
english.UnknownInstalledVersion=An existing BlurOut PDF installation was found, but its version could not be read. No changes were made.
polish.UnknownInstalledVersion=Znaleziono instalację BlurOut PDF, ale nie można odczytać jej wersji. Nie wprowadzono zmian.

[Files]
Source: "..\dist\BlurOutPDF\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\BlurOut PDF"; Filename: "{app}\BlurOutPDF.exe"
Name: "{autodesktop}\BlurOut PDF"; Filename: "{app}\BlurOutPDF.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalShortcuts}"

[Registry]
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.PDF"; ValueType: string; ValueData: "PDF document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.PDF\DefaultIcon"; ValueType: string; ValueData: "{app}\BlurOutPDF.exe,0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.PDF\shell\open\command"; ValueType: string; ValueData: """{app}\BlurOutPDF.exe"" ""%1"""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.Raster"; ValueType: string; ValueData: "Raster image"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.Raster\DefaultIcon"; ValueType: string; ValueData: "{app}\BlurOutPDF.exe,0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.Raster\shell\open\command"; ValueType: string; ValueData: """{app}\BlurOutPDF.exe"" ""%1"""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.PDF"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.jpg\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.jpeg\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.png\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.tif\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.tiff\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.bmp\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.webp\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.Raster"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".jpg"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".jpeg"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".png"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".tif"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".tiff"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".bmp"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".webp"; ValueData: ""

[Run]
Filename: "{app}\BlurOutPDF.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  UninstallKey, InstalledVersion: String;
  InstalledPacked, NewPacked: Int64;
  Comparison: Integer;
begin
  Result := True;
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\BlurOutPDF.PDF.Reader_is1';
  if not RegKeyExists(HKCU, UninstallKey) then
    Exit;

  if not RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', InstalledVersion) or
     not StrToVersion(InstalledVersion, InstalledPacked) or
     not StrToVersion('{#AppVersion}', NewPacked) then
  begin
    SuppressibleMsgBox(CustomMessage('UnknownInstalledVersion'), mbError, MB_OK, IDOK);
    Result := False;
    Exit;
  end;

  Comparison := ComparePackedVersion(InstalledPacked, NewPacked);
  if Comparison = 0 then
  begin
    SuppressibleMsgBox(FmtMessage(CustomMessage('AlreadyInstalled'), [InstalledVersion]), mbInformation, MB_OK, IDOK);
    Result := False;
  end
  else if Comparison > 0 then
  begin
    SuppressibleMsgBox(FmtMessage(CustomMessage('DowngradeBlocked'), [InstalledVersion, '{#AppVersion}']), mbError, MB_OK, IDOK);
    Result := False;
  end;
end;
