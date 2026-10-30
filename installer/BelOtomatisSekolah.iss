; Inno Setup 6 Script untuk Bel Otomatis Sekolah
; Menghasilkan installer mandiri untuk Windows 10 & Windows 11 (64-bit)
; Menggunakan Python 3.11 + PySide6 (Qt 6)

#define MyAppName "Bel Otomatis Sekolah"
#define MyAppVersion "1.2.2"
#define MyAppPublisher "Pengembang Bel Otomatis Sekolah"
#define MyAppExeName "BelOtomatisSekolah.exe"
#define MyAppSourceDir "..\dist\BelOtomatisSekolah"

[Setup]
; Informasi dasar aplikasi
AppId={{C47F892A-3D5E-4B91-81FE-B9E4F5712A80}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\release
OutputBaseFilename=BelOtomatisSekolah_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
DisableDirPage=no
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Jalankan Bel Otomatis Sekolah saat komputer Windows dinyalakan"; GroupDescription: "Pengaturan Startup Windows:"; Flags: checkedonce

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BelOtomatisSekolah"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Files]
; Berkas aplikasi dari folder dist PyInstaller
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Catatan: Database pengguna (%APPDATA%\BelOtomatisSekolah) TIDAK disertakan di sini agar tidak pernah tertimpa saat instalasi baru/update.

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; HANYA menghapus berkas sementara di folder program instalasi
; JANGAN PERNAH menghapus data pengguna di %APPDATA%\BelOtomatisSekolah
Type: filesandordirs; Name: "{app}\*__pycache__*"
