"""
setup_wizard.py — Assistente de configuracao inicial do R.O.N.Y
Executa na primeira instalacao ou quando reconfigurar e necessario.
"""

import json
import os
import sys
import time
from pathlib import Path

# ── Dirs ──────────────────────────────────────────────────────
RONY_DIR    = Path(__file__).parent.parent
ENV_FILE    = RONY_DIR / ".env"
ENV_EXAMPLE = RONY_DIR / ".env.example"

# Config vai para AppData (dados do usuário isolados do programa)
_local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
_appdata_data = Path(_local) / "Rony" / "data"
_appdata_data.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = _appdata_data / "rony_config.json"
# Mantém cópia legada para compatibilidade (lida como fallback)
CONFIG_FILE_LEGADO = RONY_DIR / "rony_config.json"

# ── Cores ANSI (funciona no Windows 10+) ──────────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    VERDE  = "\033[92m"
    AZUL   = "\033[94m"
    AMARELO= "\033[93m"
    VERMELHO="\033[91m"
    CINZA  = "\033[90m"
    NEGRITO= "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    VERDE = AZUL = AMARELO = VERMELHO = CINZA = NEGRITO = RESET = ""


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def linha(char="─", n=56):
    print(" ", char * n)


def titulo(texto):
    print()
    linha("═")
    print(f"  {NEGRITO}{AZUL}{texto}{RESET}")
    linha("═")
    print()


def ok(msg):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def aviso(msg):
    print(f"  {AMARELO}[!]{RESET}  {msg}")


def erro(msg):
    print(f"  {VERMELHO}[X]{RESET}  {msg}")


def info(msg):
    print(f"  {CINZA}···{RESET} {msg}")


def perguntar(prompt, padrao="", oculto=False):
    """Lê entrada do usuário com valor padrão opcional."""
    if padrao:
        display = f"{AZUL}{prompt}{RESET} [{CINZA}{padrao}{RESET}]: "
    else:
        display = f"{AZUL}{prompt}{RESET}: "

    sys.stdout.write("  " + display)
    sys.stdout.flush()

    if oculto:
        import getpass
        resp = getpass.getpass("").strip()
    else:
        resp = input().strip()

    return resp if resp else padrao


def perguntar_lista(prompt, opcoes: dict, padrao: str):
    """Pergunta com lista de opções numeradas."""
    print(f"  {AZUL}{prompt}{RESET}")
    for codigo, nome in opcoes.items():
        marca = f" {VERDE}[padrão]{RESET}" if codigo == padrao else ""
        print(f"    {CINZA}{codigo}{RESET} — {nome}{marca}")
    sys.stdout.write(f"  Escolha [{padrao}]: ")
    resp = input().strip().lower()
    return resp if resp in opcoes else padrao


# ══════════════════════════════════════════════════════════════
#  CARREGAR / SALVAR
# ══════════════════════════════════════════════════════════════

def carregar_env() -> dict:
    """Lê variáveis do .env como dicionário."""
    env = {}
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        import shutil
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
    if ENV_FILE.exists():
        for linha_txt in ENV_FILE.read_text(encoding="utf-8").splitlines():
            linha_txt = linha_txt.strip()
            if linha_txt and not linha_txt.startswith("#") and "=" in linha_txt:
                k, _, v = linha_txt.partition("=")
                env[k.strip()] = v.strip()
    return env


def salvar_env(env: dict) -> None:
    """Salva dicionário no .env, preservando comentários do example."""
    template = ""
    if ENV_EXAMPLE.exists():
        template = ENV_EXAMPLE.read_text(encoding="utf-8")

    linhas_saida = []
    chaves_escritas = set()

    for linha_txt in template.splitlines():
        stripped = linha_txt.strip()
        if stripped.startswith("#") or not stripped:
            linhas_saida.append(linha_txt)
            continue
        if "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in env:
                linhas_saida.append(f"{k}={env[k]}")
                chaves_escritas.add(k)
            else:
                linhas_saida.append(linha_txt)
        else:
            linhas_saida.append(linha_txt)

    # Chaves novas não presentes no template
    for k, v in env.items():
        if k not in chaves_escritas:
            linhas_saida.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(linhas_saida) + "\n", encoding="utf-8")


def carregar_config() -> dict:
    """Lê rony_config.json."""
    defaults = {
        "version": "1.0.0",
        "mic_device_index": None,
        "langue_defaut": "pt",
        "auto_detect_langue": True,
        "ws_port": 8765,
        "frontend_port": 5173,
        "tts_rate": "+0%",
        "tts_volume": "+0%",
        "historique_max_ram": 30,
        "historique_max_disk": 300,
        "ia_ordre": ["gemini", "claude", "groq", "openai"],
        "quota_cooldown_sec": 30,
        "captures_max": 50,
        "nom_utilisateur": "",
        "personalidade": "amigavel",
        "humor": True,
    }
    if CONFIG_FILE.exists():
        try:
            dados = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            defaults.update(dados)
        except Exception:
            pass
    return defaults


def salvar_config(config: dict) -> None:
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ══════════════════════════════════════════════════════════════
#  TESTES DE API
# ══════════════════════════════════════════════════════════════

def testar_gemini(chave: str) -> bool:
    """Testa se a chave Gemini é válida."""
    if not chave or chave.startswith("VOTRE") or chave.startswith("SUA"):
        return False
    try:
        import google.genai as genai
        client = genai.Client(api_key=chave)
        r = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents="Diga apenas: OK"
        )
        return bool(r.text)
    except Exception:
        return False


def validar_formato_chave(chave: str, prefixo: str = "") -> bool:
    """Validação básica de formato."""
    if not chave or len(chave) < 10:
        return False
    if prefixo and not chave.startswith(prefixo):
        return False
    placeholders = ["VOTRE", "YOUR", "SUA", "SU_", "AQUI", "HERE", "INSERIR", "INSERT"]
    return not any(p in chave.upper() for p in placeholders)


# ══════════════════════════════════════════════════════════════
#  SEÇÕES DO WIZARD
# ══════════════════════════════════════════════════════════════

def secao_boas_vindas():
    cls()
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                                                      ║")
    print("  ║   R.O.N.Y — Assistente de Configuracao              ║")
    print("  ║   Responsive Omni-lingual Neural sYstem             ║")
    print("  ║                                                      ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print("  Vou te ajudar a configurar o Rony em alguns passos.")
    print("  Voce pode pressionar Enter para usar o valor padrao.")
    print()
    input("  Pressione Enter para comecar...")


def secao_usuario(config: dict) -> dict:
    titulo("PASSO 1 — Seu Nome")
    print("  O Rony usara seu nome para se referir a voce.")
    print()

    nome_atual = config.get("nom_utilisateur", "")
    nome = perguntar("Seu nome", padrao=nome_atual or "")

    if not nome:
        nome = "Amigo"
        aviso("Nome nao informado. Usando 'Amigo'.")

    config["nom_utilisateur"] = nome.strip().title()
    ok(f"Nome definido: {config['nom_utilisateur']}")
    return config


def secao_idioma(config: dict) -> dict:
    titulo("PASSO 2 — Idioma Padrao")
    print("  Em qual idioma o Rony deve responder por padrao?")
    print("  (Ele detecta automaticamente mudancas de idioma)")
    print()

    idiomas = {
        "pt": "Portugues (Brasil)  [recomendado]",
        "en": "English",
        "fr": "Francais",
        "es": "Espanol",
        "de": "Deutsch",
        "it": "Italiano",
    }

    atual = config.get("langue_defaut", "pt")
    lingua = perguntar_lista("Idioma", idiomas, atual)
    config["langue_defaut"] = lingua

    # Atualiza language_manager se disponivel
    lang_file = RONY_DIR / "rony_config.json"
    ok(f"Idioma definido: {idiomas[lingua].split('[')[0].strip()}")
    return config


def secao_cidade(env: dict, config: dict) -> tuple:
    titulo("PASSO 3 — Localizacao (Clima)")
    print("  Informe sua cidade para previsao do tempo.")
    print()

    cidade_atual = env.get("VILLE_DEFAUT", "Sao Paulo")
    cidade = perguntar("Cidade padrao", padrao=cidade_atual)

    if cidade:
        env["VILLE_DEFAUT"] = cidade
        ok(f"Cidade: {cidade}")

        # Coordenadas pre-definidas para cidades comuns
        coords = {
            "sao paulo": ("−23.5505", "−46.6333"),
            "rio de janeiro": ("−22.9068", "−43.1729"),
            "brasilia": ("−15.7801", "−47.9292"),
            "belo horizonte": ("−19.9191", "−43.9386"),
            "curitiba": ("−25.4284", "−49.2733"),
            "porto alegre": ("−30.0346", "−51.2177"),
            "salvador": ("−12.9714", "−38.5014"),
            "fortaleza": ("−3.7172", "−38.5433"),
            "recife": ("−8.0522", "−34.9286"),
            "manaus": ("−3.1190", "−60.0217"),
            "paris": ("48.8566", "2.3522"),
            "london": ("51.5074", "−0.1278"),
            "new york": ("40.7128", "−74.0060"),
            "madrid": ("40.4168", "−3.7038"),
            "berlin": ("52.5200", "13.4050"),
        }
        key = cidade.lower().strip()
        if key in coords:
            lat, lon = coords[key]
            env["LAT_DEFAUT"] = lat
            env["LON_DEFAUT"] = lon
            info(f"Coordenadas: {lat}, {lon}")
        else:
            aviso("Coordenadas nao encontradas. Edite LAT_DEFAUT e LON_DEFAUT no .env se quiser clima preciso.")

    return env, config


def secao_apis(env: dict) -> dict:
    titulo("PASSO 4 — Chaves de API")
    print("  O Rony usa IAs para responder. Configure pelo menos uma chave.")
    print(f"  {CINZA}(As chaves ficam salvas localmente no arquivo .env){RESET}")
    print()

    # ── Gemini (principal) ────────────────────────────────────
    print(f"  {NEGRITO}Google Gemini{RESET} {VERDE}[recomendado — gratis]{RESET}")
    print(f"  {CINZA}Obter em: https://aistudio.google.com/app/apikey{RESET}")
    chave_atual = env.get("GEMINI_API_KEY", "")
    chave_display = f"...{chave_atual[-8:]}" if len(chave_atual) > 10 and validar_formato_chave(chave_atual) else ""
    chave = perguntar("Chave Gemini", padrao=chave_display)

    if chave and chave != chave_display:
        env["GEMINI_API_KEY"] = chave
        print(f"  {CINZA}Testando conexao com Gemini...{RESET}", end="", flush=True)
        if testar_gemini(chave):
            print(f"\r  {VERDE}[OK]{RESET} Gemini conectado com sucesso!       ")
        else:
            print(f"\r  {AMARELO}[!]{RESET}  Chave salva mas nao foi possivel verificar agora.{' '*5}")
    elif chave_display and validar_formato_chave(chave_atual):
        ok("Chave Gemini ja configurada.")
    else:
        aviso("Chave Gemini nao configurada.")

    print()

    # ── Outras APIs (opcionais) ───────────────────────────────
    print(f"  {NEGRITO}Outras IAs{RESET} {CINZA}(todas opcionais — Gemini ja e suficiente){RESET}")
    print()

    outras = [
        ("GROQ_API_KEY",      "Groq (Llama 3.3, gratis)",    "https://console.groq.com"),
        ("ANTHROPIC_API_KEY", "Anthropic (Claude)",           "https://console.anthropic.com"),
        ("OPENAI_API_KEY",    "OpenAI (ChatGPT)",             "https://platform.openai.com"),
    ]

    for chave_env, nome, url in outras:
        valor_atual = env.get(chave_env, "")
        ja_tem = validar_formato_chave(valor_atual)

        if ja_tem:
            ok(f"{nome} ja configurado.")
        else:
            print(f"  {CINZA}{nome} — {url}{RESET}")
            resp = perguntar(f"Chave {nome.split(' ')[0]} (Enter para pular)", padrao="")
            if resp:
                env[chave_env] = resp
                ok(f"{nome.split(' ')[0]} configurado.")
            print()

    return env


def secao_microfone():
    titulo("PASSO 5 — Microfone")

    try:
        import speech_recognition as sr
        micros = sr.Microphone.list_microphone_names()
    except Exception:
        aviso("SpeechRecognition nao disponivel. Microfone nao configurado.")
        return

    if not micros:
        aviso("Nenhum microfone detectado. O Rony funcionara em modo texto.")
        return

    print(f"  Microfones detectados ({len(micros)}):")
    print()
    for i, nome in enumerate(micros[:10]):
        print(f"  {CINZA}[{i}]{RESET} {nome}")
    if len(micros) > 10:
        print(f"  {CINZA}... e mais {len(micros) - 10}{RESET}")
    print()
    print("  Pressione Enter para usar o padrao (recomendado)")
    print("  Ou informe o numero do microfone que deseja usar:")

    resp = perguntar("Indice do microfone", padrao="auto")

    config = carregar_config()
    if resp == "auto" or resp == "":
        config["mic_device_index"] = None
        ok("Microfone automatico (padrao do sistema).")
    elif resp.isdigit() and int(resp) < len(micros):
        config["mic_device_index"] = int(resp)
        ok(f"Microfone [{resp}]: {micros[int(resp)]}")
    else:
        aviso("Indice invalido. Usando padrao automatico.")
        config["mic_device_index"] = None

    salvar_config(config)


def secao_confirmacao(config: dict, env: dict):
    titulo("RESUMO DA CONFIGURACAO")

    nome      = config.get("nom_utilisateur", "?")
    lingua    = config.get("langue_defaut", "pt")
    cidade    = env.get("VILLE_DEFAUT", "?")
    gemini    = "Configurado" if validar_formato_chave(env.get("GEMINI_API_KEY", "")) else "Nao configurado"
    groq      = "Configurado" if validar_formato_chave(env.get("GROQ_API_KEY", "")) else "—"
    anthropic = "Configurado" if validar_formato_chave(env.get("ANTHROPIC_API_KEY", "")) else "—"
    openai    = "Configurado" if validar_formato_chave(env.get("OPENAI_API_KEY", "")) else "—"

    lingua_nome = {
        "pt": "Portugues (BR)", "en": "English", "fr": "Francais",
        "es": "Espanol", "de": "Deutsch", "it": "Italiano"
    }.get(lingua, lingua)

    print(f"  Nome:          {NEGRITO}{nome}{RESET}")
    print(f"  Idioma:        {lingua_nome}")
    print(f"  Cidade:        {cidade}")
    print()
    print(f"  Gemini:        {VERDE if 'Configurado' in gemini else AMARELO}{gemini}{RESET}")
    print(f"  Groq:          {VERDE if 'Configurado' in groq else CINZA}{groq}{RESET}")
    print(f"  Anthropic:     {VERDE if 'Configurado' in anthropic else CINZA}{anthropic}{RESET}")
    print(f"  OpenAI:        {VERDE if 'Configurado' in openai else CINZA}{openai}{RESET}")
    print()

    if gemini == "Nao configurado" and groq == "—" and anthropic == "—" and openai == "—":
        print(f"  {AMARELO}AVISO: Nenhuma chave de API configurada!{RESET}")
        print(f"  {AMARELO}O Rony nao conseguira responder sem uma IA.{RESET}")
        print(f"  {CINZA}Recomendado: obtenha uma chave gratuita do Gemini em{RESET}")
        print(f"  {CINZA}https://aistudio.google.com/app/apikey{RESET}")
        print()

    resp = perguntar("Salvar configuracao? [S/n]", padrao="s")
    return resp.lower() != "n"


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    secao_boas_vindas()

    env    = carregar_env()
    config = carregar_config()

    # Passo 1: Nome
    config = secao_usuario(config)
    time.sleep(0.3)

    # Passo 2: Idioma
    config = secao_idioma(config)
    time.sleep(0.3)

    # Passo 3: Cidade
    env, config = secao_cidade(env, config)
    time.sleep(0.3)

    # Passo 4: APIs
    env = secao_apis(env)
    time.sleep(0.3)

    # Passo 5: Microfone
    secao_microfone()
    time.sleep(0.3)

    # Confirmação e salvamento
    if secao_confirmacao(config, env):
        salvar_env(env)
        salvar_config(config)

        # Atualiza language_manager se possivel
        try:
            sys.path.insert(0, str(RONY_DIR))
            from language_manager import definir_lingua
            definir_lingua(config["langue_defaut"])
        except Exception:
            pass

        print()
        ok("Configuracao salva com sucesso!")
        print()
        print(f"  {NEGRITO}Proximo passo:{RESET} Execute INICIAR_RONY.bat")
        print()
    else:
        print()
        aviso("Configuracao cancelada. Nenhuma alteracao foi salva.")
        print()

    input("  Pressione Enter para fechar...")


if __name__ == "__main__":
    main()
