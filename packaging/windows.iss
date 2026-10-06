#define AppName "Rectveil"
#define AppVersion "0.1.0"

[Setup]
AppId=Rectveil.PDF.Reader
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Rectveil-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ChangesAssociations=yes
UninstallDisplayIcon={app}\Rectveil.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Files]
Source: "..\dist\Rectveil\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Rectveil"; Filename: "{app}\Rectveil.exe"
Name: "{autodesktop}\Rectveil"; Filename: "{app}\Rectveil.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Registry]
Root: HKCU; Subkey: "Software\Classes\Rectveil.PDF"; ValueType: string; ValueData: "PDF document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Rectveil.PDF\DefaultIcon"; ValueType: string; ValueData: "{app}\Rectveil.exe,0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Rectveil.PDF\shell\open\command"; ValueType: string; ValueData: """{app}\Rectveil.exe"" ""%1"""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: none; ValueName: "Rectveil.PDF"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\Rectveil.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey

[Run]
Filename: "{app}\Rectveil.exe"; Description: "Launch Rectveil"; Flags: nowait postinstall skipifsilent
