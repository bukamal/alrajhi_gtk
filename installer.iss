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

[Files]
Source: "dist\AlrajhiAccounting\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\الراجحي للمحاسبة"; Filename: "{app}\AlrajhiAccounting.exe"
Name: "{group}\إلغاء التثبيت"; Filename: "{uninstallexe}"
Name: "{userdesktop}\الراجحي للمحاسبة"; Filename: "{app}\AlrajhiAccounting.exe"

[Run]
Filename: "{app}\AlrajhiAccounting.exe"; Description: "تشغيل البرنامج"; Flags: postinstall nowait skipifsilent
