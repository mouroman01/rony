# R.O.N.Y — Histórico de Desenvolvimento

> Última atualização: 10/05/2026.  
> Acesse de qualquer máquina via `git pull`.

---

## ✅ O que foi feito (em ordem)

### 1. PyWebView — Janela desktop nativa
**Commit:** `68e6f50`  
- Integrado `pywebview` para abrir o Rony como app nativo (sem depender do navegador)
- Se PyWebView falhar (WebView2 não instalado), abre o navegador automaticamente
- **Bug corrigido:** quando PyWebView falha, o código travava no `join()` sem abrir o navegador — corrigido para chamar `webbrowser.open()` no bloco `except`
- Arquivo modificado: `main.py` — bloco `__main__`

### 2. AppData isolation — Dados separados do programa
**Commit:** `fda9aec`  
- Criado `rony_paths.py` — módulo central com todos os caminhos do sistema
- Dados do usuário movidos para `%LOCALAPPDATA%\Rony\`:
  - `data/rony_config.json` — configurações
  - `data/rony_memoire.json` — memória
  - `data/rony_historique.json` — histórico
  - `logs/executor_log.jsonl` — logs
  - `captures/` — fotos da câmera
  - `updates/` — instaladores de atualização
- Migração automática dos arquivos legados na raiz do projeto
- Todos os módulos atualizados para importar de `rony_paths`

### 3. Auto-update via GitHub Releases
**Commit:** `4ab4a06`  
- Criado `rony_updater.py` — verifica atualizações em background
- URL do manifest: `https://raw.githubusercontent.com/mouroman01/rony/main/update_manifest.json`
- Criado `update_manifest.json` na raiz do repositório
- Download do instalador para `%LOCALAPPDATA%\Rony\updates\`
- Executa instalador silencioso (`/VERYSILENT /NORESTART`)

### 4. Instalador profissional — Inno Setup
**Commit:** `f514774`  
- Criado `installer/Setup.iss` — gera `Rony_Setup_1.0.0.exe`
- Instala em `%LOCALAPPDATA%\Programs\Rony\` (sem precisar de admin)
- Criado `launcher.py` → compilado como `release/Rony.exe` via PyInstaller
- Criado `GERAR_EXECUTAVEL.bat` e `GERAR_INSTALADOR.bat`
- Atalho na Área de Trabalho e Menu Iniciar
- Opção de iniciar com o Windows (desmarcada por padrão)

### 5. Correções de bugs críticos
**Commit:** `dfbb185`  
17 bugs identificados em auditoria completa. Os 5 críticos corrigidos:

| Bug | Causa | Correção |
|-----|-------|----------|
| Abre e fecha sem mensagem | `UnicodeEncodeError` nos prints com acentos | `PYTHONUTF8=1` no bat + `sys.stdout.reconfigure(utf-8)` no main.py |
| Double event loop | `asyncio.run(main())` chamado 2x no PyWebView except | Verificar `_asyncio_thread.is_alive()` antes de chamar |
| Crash no Windows | `psutil.disk_usage("/")` — caminho Unix | Usar `"C:\\"` quando `os.name == "nt"` |
| NameError câmera | `_EYE_CASCADE` não definido no except ImportError | Inicializar como `None` no bloco except |
| Config ignorada | `_charger_config_micro()` lia o arquivo legado | Verificar AppData primeiro |

### 6. Correções nos scripts .bat
**Commits:** `d508b53`, `16421d3`

**GERAR_EXECUTAVEL.bat:**
- Bug: `set "PYINST_ARGS=... --distpath "%RELEASE%""` — as aspas internas fechavam o `set "` prematuramente
- Fix: removida a variável, PyInstaller chamado diretamente em dois branches `if/else`

**GERAR_INSTALADOR.bat:**
- Bug: `for %%P in (... %ProgramFiles(x86)% ...)` — o `)` de `(x86)` fechava o `for`
- Fix: caminhos pré-extraídos para `%P1%..%P5%` e verificados com `if exist`

### 7. Frontend incluído no repositório
**Commit:** `b750f47`  
- `frontend/dist/` removido do `.gitignore`
- Interface compilada incluída no repo — funciona sem Node.js instalado
- Corrigido `/dist/` no .gitignore para não afetar `frontend/dist/`

### 8. Idioma padrão alterado para Português
**Commit:** `b750f47`  
- `language_manager.py` linha 12: `_langue_active = "pt"` (era `"fr"`)
- `main.py`: lê `langue_defaut` do config e chama `definir_langue()` no startup, antes do WebSocket iniciar

### 9. Correções no instalador Inno Setup
**Commits:** `ef97788`, `d7f0c77`  
- Removida linha `SetupIconFile=..\app.ico` — arquivo não existe
- Corrigido `Source: "..\*.env.example"` com `DestName` inválido (wildcard + DestName não é permitido)

### 10. Limpeza de arquivos desnecessários
**Commit:** `b750f47`  
Removidos:
- `jarvis_agent.py` — não importado em lugar nenhum (legado JARVIS)
- `install.bat` — redirecionava para INSTALAR.bat
- `DEMARRER_RONY.bat` — redirecionava para INICIAR_RONY.bat (versão francesa)
- `_setup/setup_langue.py` — substituído pelo setup_wizard.py
- `_setup/setup_mic.py` — substituído pelo setup_wizard.py
- `rony_config.json` — migrado para AppData
- `rony_historique.json` — migrado para AppData
- `executor_log.jsonl` — migrado para AppData
- `mobile/` — pasta vazia

---

## 📁 Estrutura atual do projeto

```
Rony/
├── .env                    ← chaves de API (NÃO vai para o git)
├── .env.example            ← template das chaves
├── .gitignore
├── update_manifest.json    ← controle de versão para auto-update
├── requirements.txt
│
├── INICIAR_RONY.bat        ← iniciar o Rony (uso diário)
├── INSTALAR.bat            ← instalar dependências (primeira vez)
├── ATUALIZAR_RONY.bat      ← atualizar deps + frontend
├── GERAR_EXECUTAVEL.bat    ← gera release/Rony.exe (PyInstaller)
├── GERAR_INSTALADOR.bat    ← gera installer_output/Rony_Setup_1.0.0.exe
│
├── main.py                 ← núcleo principal do sistema
├── rony_paths.py           ← caminhos centralizados (AppData)
├── rony_updater.py         ← auto-update em background
├── language_manager.py     ← gestão de idiomas (padrão: PT)
├── memory_manager.py       ← memória e histórico persistente
├── launcher.py             ← alvo do PyInstaller → Rony.exe
│
├── app_launcher.py         ← abre/fecha aplicativos do Windows
├── camera_module.py        ← câmera, reconhecimento facial, YOLO
├── executor_module.py      ← execução de comandos do sistema
├── file_manager.py         ← gerenciamento de arquivos
├── google_services.py      ← Gmail, Calendar, Drive
├── ha_config.py            ← Home Assistant (automação)
├── music_controller.py     ← controle de música
├── specialist_module.py    ← módulos especializados
├── vision_module.py        ← análise de imagem com IA
├── wake_word.py            ← detecção de "Rony", "Hey Rony"
│
├── yolov8n.pt              ← modelo YOLO (auto-download na 1ª vez)
│
├── frontend/               ← interface web (Three.js + TypeScript)
│   ├── dist/               ← build compilado (incluído no git)
│   └── src/                ← código-fonte da interface
│
├── installer/
│   └── Setup.iss           ← script Inno Setup
│
├── _setup/
│   ├── setup_wizard.py     ← assistente de configuração inicial
│   └── criar_atalho.py     ← cria atalho na Área de Trabalho
│
├── release/                ← Rony.exe gerado (não vai para o git)
├── captures/               ← fotos da câmera (runtime, AppData)
└── rostos/                 ← rostos reconhecidos (runtime, AppData)
```

---

## ⚙️ Dados do usuário (AppData)

Ficam em `C:\Users\[usuario]\AppData\Local\Rony\`:
```
Rony/
├── data/
│   ├── rony_config.json    ← configurações
│   ├── rony_memoire.json   ← memória de longo prazo
│   ├── rony_historique.json← histórico de conversas
│   └── rostos/             ← rostos reconhecidos
├── logs/
│   └── executor_log.jsonl  ← log de comandos executados
├── captures/               ← capturas de câmera
└── updates/                ← instaladores baixados pelo auto-update
```

---

## 🔑 Chaves de API necessárias (arquivo `.env`)

```env
# Obrigatória (pelo menos uma):
GEMINI_API_KEY=AIzaSy...        # https://aistudio.google.com — gratuito
GROQ_API_KEY=gsk_...            # https://console.groq.com — gratuito e rápido

# Opcionais:
OPENAI_API_KEY=sk-...           # https://platform.openai.com
ANTHROPIC_API_KEY=sk-ant-...    # https://console.anthropic.com
```

> Se todas as IAs retornam "Ocorreu um erro e irá tentar em instantes",
> verifique as chaves no `.env` — provavelmente estão em branco ou inválidas.

---

### 11. Groq Whisper — Motor de voz principal
**Commit:** `055f6fd`  
- Substituído `recognize_google` (API não-oficial, rate-limited) por **Groq Whisper large-v3-turbo**
- Whisper é gratuito com chave Groq, muito mais preciso em português
- Fallback automático para Google se Groq não estiver configurado
- Corrigido: fallback de lang_code era `"fr-FR"`, agora é `"pt-BR"`
- Aplicado em `ecouter()` e `ecouter_wake_word()`
- Adicionado `_check_mic.py` — script de diagnóstico do microfone

### 12. Correções no instalador Inno Setup
**Commits:** `ef97788`, `d7f0c77`  
- Removida linha `SetupIconFile=..\app.ico` — arquivo não existe
- Corrigido `Source: "..\*.env.example"` com `DestName` inválido com wildcard

### 13. Frontend incluído no repositório
**Commit:** `b750f47`  
- `frontend/dist/` removido do `.gitignore` — funciona sem Node.js
- Corrigido `/dist/` para não afetar `frontend/dist/`

---

## 🐛 Problemas conhecidos e soluções

| Problema | Causa | Solução |
|----------|-------|---------|
| "Ocorreu um erro e irá tentar em instantes" | Chaves de API inválidas/vazias | Verificar `.env`, obter chave Groq em console.groq.com |
| Rony não escuta / não reconhece voz | `recognize_google` com rate limit | Resolvido — Groq Whisper como motor principal |
| Navegador abre com ERR_CONNECTION_REFUSED | `frontend/dist/` não existia | Resolvido — dist incluído no git |
| Rony abre e fecha instantaneamente | UnicodeEncodeError em terminais sem UTF-8 | Resolvido — PYTHONUTF8=1 no bat |
| PyWebView não abre nada | WebView2 não instalado, fallback travava | Resolvido — fallback abre browser corretamente |
| GERAR_INSTALADOR.bat falhava com (x86) | `for` loop parseava `)` como fechamento | Resolvido — paths pré-extraídos |
| Setup.iss erro linha 48 | app.ico não existe | Resolvido — linha removida |
| Setup.iss erro linha 93 | DestName com wildcard inválido | Resolvido — wildcard removido |

---

## 🚀 Próximos passos

- [ ] **Configurar chave Groq no `.env`** — necessário para voz + respostas IA (gratuito)
- [ ] Testar reconhecimento de voz com Whisper após configurar Groq
- [ ] Criar `app.ico` personalizado e reativar `SetupIconFile` no Setup.iss
- [ ] Gerar `Rony_Setup_1.0.0.exe` com sucesso e publicar no GitHub Releases
- [ ] Preencher `download_url` no `update_manifest.json` após publicar release
- [ ] Testar instalador completo em máquina limpa (sem Python pré-instalado)

---

## 🔧 Diagnóstico rápido

```bat
:: Testar microfone
venv\Scripts\python.exe _check_mic.py

:: Ver logs em tempo real ao iniciar
INICIAR_RONY.bat
:: Observar o terminal — erros aparecem com prefixo [MICRO], [GEMINI], [GROQ] etc.
```
