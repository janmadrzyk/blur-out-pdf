#define AppName "BlurOut PDF"
#define AppVersion "0.1.0"

[Setup]
AppId=BlurOutPDF.PDF.Reader
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
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

[Files]
Source: "..\dist\BlurOutPDF\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BlurOut PDF"; Filename: "{app}\BlurOutPDF.exe"
Name: "{autodesktop}\BlurOut PDF"; Filename: "{app}\BlurOutPDF.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Registry]
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.PDF"; ValueType: string; ValueData: "PDF document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.PDF\DefaultIcon"; ValueType: string; ValueData: "{app}\BlurOutPDF.exe,0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BlurOutPDF.PDF\shell\open\command"; ValueType: string; ValueData: """{app}\BlurOutPDF.exe"" ""%1"""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: none; ValueName: "BlurOutPDF.PDF"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\BlurOutPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey

[Run]
Filename: "{app}\BlurOutPDF.exe"; Description: "Launch BlurOut PDF"; Flags: nowait postinstall skipifsilent
