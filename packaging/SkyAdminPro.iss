; SkyAdmin Pro — Windows installer (Inno Setup 6)
; Build:  packaging\build-installer.ps1
; Requires: Inno Setup 6 — https://jrsoftware.org/isdl.php

#ifdef AppVersion
  #if AppVersion == ""
    #error "AppVersion must be non-empty — pass /DAppVersion via ISCC or build-installer.ps1"
  #endif
#else
  #error "AppVersion not defined — build via packaging/build-installer.ps1 which passes /DAppVersion=APP_VERSION"
#endif

#define AppName "SkyAdmin Pro"
#define AppPublisher "Sky Creation Innovations"
#define AppURL "https://skyadmin-worker.skyadmin-pro.workers.dev"
#define AppExeName "SkyAdminPro.exe"

[Setup]
AppId={{A7B3C9D1-4E2F-5A6B-8C0D-1E2F3A4B5C6D}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} v{#AppVersion}
VersionInfoCopyright=Sky Creation Innovations
AppCopyright=Sky Creation Innovations
UninstallDisplayName={#AppName} {#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoBeforeFile=..\DISCLAIMER.md
OutputDir=..\dist
OutputBaseFilename=SkyAdminPro-Setup-{#AppVersion}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible arm64
ArchitecturesInstallIn64BitMode=x64compatible arm64
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Messages]
; User data lives in %USERPROFILE%\.skyadmin_pro — not removed on uninstall.
WelcomeLabel2=This will install [name/ver] on your computer.%n%nYour database and license stay in %USERPROFILE%\.skyadmin_pro and are kept when you uninstall.
