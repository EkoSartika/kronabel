; Inno Setup 6 Script untuk Kronabel
; Menghasilkan installer mandiri untuk Windows 10 & Windows 11 (64-bit)
; Menggunakan Python 3.11 + PySide6 (Qt 6)

#define MyAppName "Kronabel"
#define MyAppVersion "1.2.4"
#define MyAppPublisher "Pengembang Kronabel"
#define MyAppExeName "KRONABEL.exe"
#define MyAppSourceDir "..\dist\KRONABEL"

[Setup]
; Informasi dasar aplikasi (AppId dipertahankan untuk kompatibilitas upgrade in-place)
AppId={{C47F892A-3D5E-4B91-81FE-B9E4F5712A80}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} version {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments=Aplikasi Bel Otomatis Sekolah
UninstallDisplayName={#MyAppName} version {#MyAppVersion}
VersionInfoDescription=Kronabel — Aplikasi Bel Otomatis Sekolah Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0
VersionInfoVersion={#MyAppVersion}.0
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\release
OutputBaseFilename=KRONABEL_Setup_v{#MyAppVersion}
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
; Kedua pilihan default dicentang (checked) saat instalasi, pengguna tetap bebas uncheck jika diinginkan
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Jalankan KRONABEL saat komputer Windows dinyalakan"; GroupDescription: "Pengaturan Startup Windows:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KRONABEL"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "BelOtomatisSekolah"; Flags: dontcreatekey uninsdeletevalue

[Files]
; Berkas aplikasi dari folder dist PyInstaller
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Catatan: Database pengguna (%APPDATA%\KRONABEL dan %APPDATA%\BelOtomatisSekolah) TIDAK disertakan di sini agar tidak pernah tertimpa saat update.

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; HANYA menghapus berkas program instalasi
; JANGAN PERNAH menghapus data pengguna di %APPDATA%
Type: filesandordirs; Name: "{app}\*__pycache__*"
