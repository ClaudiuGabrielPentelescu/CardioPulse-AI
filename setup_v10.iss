
; Script de instalare pentru Monitor Puls + Respirație (v10)

[Setup]
AppName=Monitor Puls + Respirație v10
AppVersion=1.0
DefaultDirName={autopf}\MonitorPulsRespiratieV10
DefaultGroupName=Monitor Puls + Respirație v10
OutputDir=Output
OutputBaseFilename=MonitorPulsRespiratieSetup_V10
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\pulse_breath_monitor_v10.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "istoric_puls.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Monitor Puls + Respirație v10"; Filename: "{app}\pulse_breath_monitor_v10.exe"
Name: "{commondesktop}\Monitor Puls + Respirație v10"; Filename: "{app}\pulse_breath_monitor_v10.exe"

[Run]
Filename: "{app}\pulse_breath_monitor_v10.exe"; Description: "Lansează aplicația Monitor Puls + Respirație v10"; Flags: nowait postinstall skipifsilent
