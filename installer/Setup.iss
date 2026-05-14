; ============================================================
;  Setup.iss â€” Instalador profissional do R.O.N.Y
;  Ferramenta: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
;
;  Para compilar:
;    scripts\GERAR_INSTALADOR.bat
;
;  Para atualizar a versÃ£o:
;    1. Altere MyAppVersion abaixo
;    2. Atualize update_manifest.json na raiz
;    3. Compile e publique no GitHub Releases
; ============================================================

#define MyAppName      "Rony"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Robertson Romano"
#define MyAppURL       "https://github.com/mouroman01/rony"
#define MyAppExeName   "Rony.exe"
#define MyAppId        "RONY-ASSISTENTE-PESSOAL-2025-V1"

; â”€â”€ ConfiguraÃ§Ã£o geral â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Instala em AppData sem precisar de admin
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; SaÃ­da
OutputDir=..\installer_output
OutputBaseFilename=Rony_Setup_{#MyAppVersion}

; CompressÃ£o
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Visual
SetupIconFile=..\app.ico
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

; Sem necessidade de admin
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Registro de versÃ£o
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} â€” Assistente Pessoal Inteligente
VersionInfoProductName={#MyAppName}

; â”€â”€ Idiomas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Languages]
Name: "ptbr";    MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; â”€â”€ Tarefas opcionais â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Tasks]
Name: "desktopicon"; \
  Description: "Criar atalho na Ãrea de Trabalho"; \
  GroupDescription: "Atalhos adicionais:"; \
  Flags: checkedonce
Name: "startupicon"; \
  Description: "Iniciar Rony automaticamente com o Windows"; \
  GroupDescription: "Atalhos adicionais:"; \
  Flags: unchecked

; â”€â”€ Arquivos a instalar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Files]
; ExecutÃ¡vel launcher (gerado por GERAR_EXECUTAVEL.bat)
Source: "..\release\{#MyAppExeName}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

; CÃ³digo-fonte Python (mÃ³dulos principais)
Source: "..\*.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.txt";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.bat";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.md";   DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Arquivo de ambiente (template)
Source: "..\.env.example"; DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist

; Ãcone da aplicaÃ§Ã£o
Source: "..\app.ico"; DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist

; Frontend prÃ©-compilado
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; \
  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Setup wizard e scripts auxiliares
Source: "..\\_setup\*"; DestDir: "{app}\_setup"; \
  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; â”€â”€ Atalhos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Icons]
; Menu Iniciar
Name: "{group}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\{#MyAppExeName}"; \
  AppUserModelID: "RONY.AssistentePessoal.Desktop"

Name: "{group}\Configurar {#MyAppName}"; \
  Filename: "{app}\_setup\setup_wizard.py"; \
  WorkingDir: "{app}"

Name: "{group}\Desinstalar {#MyAppName}"; \
  Filename: "{uninstallexe}"

; Ãrea de Trabalho (opcional)
Name: "{autodesktop}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\{#MyAppExeName}"; \
  AppUserModelID: "RONY.AssistentePessoal.Desktop"; \
  Tasks: desktopicon

; Startup (opcional)
Name: "{userstartup}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\{#MyAppExeName}"; \
  AppUserModelID: "RONY.AssistentePessoal.Desktop"; \
  Tasks: startupicon

; â”€â”€ ExecuÃ§Ã£o pÃ³s-instalaÃ§Ã£o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Run]
; Instala dependÃªncias Python e builda frontend (pode demorar 2-5 min)
Filename: "{cmd}"; \
  Parameters: "/c ""{app}\INSTALAR.bat"""; \
  WorkingDir: "{app}"; \
  StatusMsg: "Instalando dependÃªncias (pode demorar alguns minutos)..."; \
  Flags: waituntilterminated

; Pergunta se quer iniciar agora
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Iniciar {#MyAppName} agora"; \
  WorkingDir: "{app}"; \
  Flags: nowait postinstall skipifsilent

; â”€â”€ Limpeza na desinstalaÃ§Ã£o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[UninstallDelete]
; Remove o venv criado pÃ³s-instalaÃ§Ã£o (maior parte do espaÃ§o)
Type: filesandordirs; Name: "{app}\venv"
; Remove cache Python
Type: filesandordirs; Name: "{app}\__pycache__"
; Remove build temporÃ¡rios do frontend
Type: filesandordirs; Name: "{app}\frontend\node_modules"

; â”€â”€ CÃ³digo Pascal â€” verificaÃ§Ã£o de prÃ©-requisitos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
[Code]
var
  RonyConfigPage: TInputQueryWizardPage;

function JsonEscape(Value: String): String;
begin
  StringChangeEx(Value, '\', '\\', True);
  StringChangeEx(Value, '"', '\"', True);
  Result := Value;
end;

function EnvHasApiInput(): Boolean;
begin
  Result :=
    (Trim(RonyConfigPage.Values[2]) <> '') or
    (Trim(RonyConfigPage.Values[3]) <> '') or
    (Trim(RonyConfigPage.Values[4]) <> '') or
    (Trim(RonyConfigPage.Values[5]) <> '') or
    (Trim(RonyConfigPage.Values[6]) <> '');
end;

procedure InitializeWizard();
begin
  RonyConfigPage := CreateInputQueryPage(
    wpSelectDir,
    'Configuracao inicial do Rony',
    'Informe como o Rony deve se identificar e quais APIs ja deseja usar.',
    'Esses dados podem ficar em branco. O Rony continuara usando o nome padrao se nenhum nome de assistente for informado.'
  );

  RonyConfigPage.Add('Como a pessoa quer ser chamada?', False);
  RonyConfigPage.Add('Nome do assistente:', False);
  RonyConfigPage.Add('Gemini API Key:', True);
  RonyConfigPage.Add('Groq API Key:', True);
  RonyConfigPage.Add('OpenAI API Key:', True);
  RonyConfigPage.Add('Anthropic API Key:', True);
  RonyConfigPage.Add('XAI/Grok API Key:', True);
  RonyConfigPage.Values[1] := 'Rony';
end;

procedure SaveRonyInstallerConfig();
var
  DataDir: String;
  EnvPath: String;
  ConfigPath: String;
  UserName: String;
  AssistantName: String;
  EnvText: String;
  ConfigText: String;
begin
  if not Assigned(RonyConfigPage) then
    Exit;

  UserName := Trim(RonyConfigPage.Values[0]);
  AssistantName := Trim(RonyConfigPage.Values[1]);
  if AssistantName = '' then
    AssistantName := 'Rony';

  if EnvHasApiInput() then
  begin
    EnvPath := ExpandConstant('{app}\.env');
    EnvText :=
      'GEMINI_API_KEY=' + Trim(RonyConfigPage.Values[2]) + #13#10 +
      'GROQ_API_KEY=' + Trim(RonyConfigPage.Values[3]) + #13#10 +
      'OPENAI_API_KEY=' + Trim(RonyConfigPage.Values[4]) + #13#10 +
      'ANTHROPIC_API_KEY=' + Trim(RonyConfigPage.Values[5]) + #13#10 +
      'XAI_API_KEY=' + Trim(RonyConfigPage.Values[6]) + #13#10;
    SaveStringToFile(EnvPath, EnvText, False);
  end;

  DataDir := ExpandConstant('{localappdata}\Rony\data');
  ForceDirectories(DataDir);
  ConfigPath := DataDir + '\rony_config.json';
  ConfigText :=
    '{' + #13#10 +
    '  "version": "1.0.0",' + #13#10 +
    '  "mic_device_index": null,' + #13#10 +
    '  "langue_defaut": "pt",' + #13#10 +
    '  "auto_detect_langue": true,' + #13#10 +
    '  "ws_port": 8765,' + #13#10 +
    '  "frontend_port": 5173,' + #13#10 +
    '  "tts_rate": "+0%",' + #13#10 +
    '  "tts_volume": "+0%",' + #13#10 +
    '  "historique_max_ram": 30,' + #13#10 +
    '  "historique_max_disk": 300,' + #13#10 +
    '  "ia_ordre": ["gemini", "claude", "groq", "openai"],' + #13#10 +
    '  "quota_cooldown_sec": 30,' + #13#10 +
    '  "captures_max": 50,' + #13#10 +
    '  "nom_utilisateur": "' + JsonEscape(UserName) + '",' + #13#10 +
    '  "nom_assistant": "' + JsonEscape(AssistantName) + '",' + #13#10 +
    '  "personalidade": "amigavel",' + #13#10 +
    '  "humor": true' + #13#10 +
    '}' + #13#10;
  SaveStringToFile(ConfigPath, ConfigText, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SaveRonyInstallerConfig();
end;

function InitializeSetup(): Boolean;
var
  PythonPath: String;
  ResultCode: Integer;
  HasPython: Boolean;
begin
  Result := True;
  HasPython := False;

  // Verifica se Python 3.10+ esta instalado
  if Exec(ExpandConstant('{cmd}'), '/C py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
    HasPython := True;

  if (not HasPython) and Exec(ExpandConstant('{cmd}'), '/C python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
    HasPython := True;

  if (not HasPython) and (
     RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.14\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.13\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.12\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.11\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.10\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.14\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.13\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', PythonPath) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonPath)) then
    HasPython := True;

  if not HasPython then
  begin
    if MsgBox(
      'Python 3.10 ou superior nao foi encontrado.' + #13#10 + #13#10 +
      'O Rony requer Python 3.10+ para funcionar.' + #13#10 +
      'Deseja abrir o site de download do Python?',
      mbConfirmation, MB_YESNO
    ) = IDYES then
    begin
      ShellExec('open', 'https://www.python.org/downloads/', '', '', SW_SHOW, ewNoWait, ResultCode);
    end;
    Result := False;
  end;
end;
