; ============================================================
;  Setup.iss — Instalador profissional do R.O.N.Y
;  Ferramenta: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
;
;  Para compilar:
;    scripts\GERAR_INSTALADOR.bat
;
;  Para atualizar a versão:
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

; ── Configuração geral ────────────────────────────────────────
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

; Saída
OutputDir=..\installer_output
OutputBaseFilename=Rony_Setup_{#MyAppVersion}

; Compressão
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

; Registro de versão
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} — Assistente Pessoal Inteligente
VersionInfoProductName={#MyAppName}

; ── Idiomas ───────────────────────────────────────────────────
[Languages]
Name: "ptbr";    MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── Tarefas opcionais ─────────────────────────────────────────
[Tasks]
Name: "desktopicon"; \
  Description: "Criar atalho na Área de Trabalho"; \
  GroupDescription: "Atalhos adicionais:"; \
  Flags: checkedonce
Name: "startupicon"; \
  Description: "Iniciar Rony automaticamente com o Windows"; \
  GroupDescription: "Atalhos adicionais:"; \
  Flags: unchecked

; ── Arquivos a instalar ──────────────────────────────────────
[Files]
; Executável launcher (gerado por GERAR_EXECUTAVEL.bat)
Source: "..\release\{#MyAppExeName}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

; Código-fonte Python (módulos principais)
Source: "..\*.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.txt";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.bat";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.md";   DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Arquivo de ambiente (template)
Source: "..\.env.example"; DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist

; Ícone da aplicação
Source: "..\app.ico"; DestDir: "{app}"; \
  Flags: ignoreversion skipifsourcedoesntexist

; Frontend pré-compilado
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; \
  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Setup wizard e scripts auxiliares
Source: "..\\_setup\*"; DestDir: "{app}\_setup"; \
  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ── Atalhos ───────────────────────────────────────────────────
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

; Área de Trabalho (opcional)
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
  AppUserModelID: "RONY.AssistentePessoal.Desktop"; \
  Tasks: startupicon

; ── Execução pós-instalação ──────────────────────────────────
[Run]
; Instala dependências Python e builda frontend (pode demorar 2-5 min)
Filename: "{cmd}"; \
  Parameters: "/c ""{app}\INSTALAR.bat"""; \
  WorkingDir: "{app}"; \
  StatusMsg: "Instalando dependências (pode demorar alguns minutos)..."; \
  Flags: waituntilterminated

; Pergunta se quer iniciar agora
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Iniciar {#MyAppName} agora"; \
  WorkingDir: "{app}"; \
  Flags: nowait postinstall skipifsilent

; ── Limpeza na desinstalação ──────────────────────────────────
[UninstallDelete]
; Remove o venv criado pós-instalação (maior parte do espaço)
Type: filesandordirs; Name: "{app}\venv"
; Remove cache Python
Type: filesandordirs; Name: "{app}\__pycache__"
; Remove build temporários do frontend
Type: filesandordirs; Name: "{app}\frontend\node_modules"

; ── Código Pascal — verificação de pré-requisitos ─────────────
[Code]
function InitializeSetup(): Boolean;
var
  PythonPath: String;
  ResultCode: Integer;
begin
  Result := True;

  // Verifica se Python 3.10+ está instalado
  if not RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.12\InstallPath', '', PythonPath) and
     not RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.11\InstallPath', '', PythonPath) and
     not RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.10\InstallPath', '', PythonPath) and
     not RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonPath) and
     not RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', PythonPath) and
     not RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonPath) then
  begin
    if MsgBox(
      'Python 3.10 ou superior não foi encontrado.' + #13#10 + #13#10 +
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
