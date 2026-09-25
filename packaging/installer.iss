; Inno Setup script for the Windows installer.
; Built by GitHub Actions after PyInstaller:  iscc /DAppVersion=1.0.0 packaging\installer.iss
; Input:  dist\Photoelectric Effect\   Output: dist\PhotoelectricEffect-Setup-<version>.exe

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Photoelectric Effect"
#define AppExe "Photoelectric Effect.exe"

[Setup]
; Keep AppId the same forever so new versions upgrade the old install.
AppId={{5E904C8C-717B-4012-AF1F-AC885AE14480}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=jrmumford
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=icon.ico
OutputDir=..\dist
OutputBaseFilename=PhotoelectricEffect-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} (Simulator)"; Filename: "{app}\{#AppExe}"; Parameters: "--simulate"
Name: "{group}\Check LabJack Connection"; Filename: "{app}\{#AppExe}"; Parameters: "--check-hardware"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function LabJackDriverInstalled(): Boolean;
begin
  Result := FileExists(ExpandConstant('{sys}\labjackud.dll'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not LabJackDriverInstalled()) and (not WizardSilent()) then
    MsgBox('The LabJack driver is not installed on this computer yet.' + #13#10 + #13#10 +
      'The program needs it to talk to the apparatus. Download the LabJack ' +
      'Windows installer from labjack.com (Support > Software & Driver > ' +
      'Installer Downloads), run it once, then plug in the apparatus.' + #13#10 + #13#10 +
      'The program''s Simulator mode works without it.',
      mbInformation, MB_OK);
end;
