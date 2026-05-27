; Script for Inno Setup
; Run with: iscc setup.iss

[Setup]
AppName=الراجحي للمحاسبة
AppVersion=1.0
DefaultDirName={pf}\AlrajhiAccounting
DefaultGroupName=الراجحي للمحاسبة
UninstallDisplayIcon={app}\AlrajhiAccounting.exe
Compression=lzma2
SolidCompression=yes
OutputDir=output
OutputBaseFilename=AlrajhiAccounting_Setup
PrivilegesRequired=admin
SetupIconFile=alrajhi_icon.ico

[Files]
Source: "dist\AlrajhiAccounting\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\الراجحي للمحاسبة"; Filename: "{app}\AlrajhiAccounting.exe"
Name: "{group}\إلغاء التثبيت"; Filename: "{uninstallexe}"
Name: "{commondesktop}\الراجحي للمحاسبة"; Filename: "{app}\AlrajhiAccounting.exe"

[Run]
Filename: "{app}\AlrajhiAccounting.exe"; Description: "تشغيل التطبيق"; Flags: postinstall nowait skipifsilent
