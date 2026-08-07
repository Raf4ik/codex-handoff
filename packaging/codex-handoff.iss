#define MyAppName "Codex Handoff"
#define MyAppVersion "0.2.0-beta.1"
#define MyAppPublisher "Codex Handoff contributors"
#define MyAppExeName "CodexHandoff.exe"

[Setup]
AppId={{6E2688C5-5C79-4E71-AF94-1BA8D615A37D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Codex Handoff
DefaultGroupName=Codex Handoff
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\build\icons\codex-handoff.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
OutputDir=..\dist
OutputBaseFilename=CodexHandoff-Windows-x64-Setup
VersionInfoVersion=0.2.0.1
VersionInfoDescription=Secure bidirectional Codex state synchronization
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "autostart"; Description: "Start Codex Handoff with Windows"; GroupDescription: "Background monitoring:"; Flags: checkedonce

[Files]
Source: "..\dist\CodexHandoff\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Codex Handoff"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Codex Handoff"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Codex Handoff"; ValueData: """{app}\{#MyAppExeName}"" --background"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Codex Handoff"; Flags: nowait postinstall skipifsilent
