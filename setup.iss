[Setup]
AppId={{B8D5A8E2-9F3C-4D2A-8E9F-1C3D5E7A9B2F}
AppName=الراجحي للمحاسبة
AppVersion=1.0.0
AppPublisher=Alrajhi
DefaultDirName={pf}\AlrajhiAccounting
DefaultGroupName=الراجحي للمحاسبة
OutputDir=Output
OutputBaseFilename=AlrajhiAccounting_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\alrajhi_icon.ico
PrivilegesRequired=admin
UsePreviousLanguage=no
ShowLanguageDialog=yes

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء أيقونة على سطح المكتب"; GroupDescription: "أيقونات إضافية:"; Flags: unchecked

[Files]
Source: "dist\AlrajhiAccounting\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\الراجحي للمحاسبة"; Filename: "{app}\AlrajhiAccounting.exe"
Name: "{group}\إلغاء التثبيت"; Filename: "{uninstallexe}"
Name: "{commondesktop}\الراجحي للمحاسبة"; Filename: "{app}\AlrajhiAccounting.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AlrajhiAccounting.exe"; Description: "تشغيل التطبيق الآن"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"

[Code]
procedure InitializeWizard;
begin
  WizardForm.NextButton.Caption := 'التالي >';
  WizardForm.CancelButton.Caption := 'إلغاء';
  WizardForm.BackButton.Caption := '< السابق';
end;
