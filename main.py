# ============================================================
#  R.O.N.Y — Responsive Omni-lingual Neural sYstem
#  Noyau principal | Version 1.0
#  Multilingue : FR · PT-BR · EN · ES · DE · IT · RU · JA · ZH · AR · +
#  Architecture : asyncio + WebSocket + Gemini + multi-IA fallback
# ============================================================

import sys
import os

# ── Garante UTF-8 no stdout/stderr (evita UnicodeEncodeError no Windows) ─
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import threading
import asyncio
import json
import time
import math
import random
import re
import builtins
import base64
import subprocess
import webbrowser
import uuid
import io
import http.server
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Version ───────────────────────────────────────────────────
VERSION = "1.0.0"
from rony_paths import RONY_DIR, CONFIG_FILE as _CONFIG_FILE

# ── Modo PyWebView (janela desktop nativa) ────────────────────
_pywebview_mode   = False  # True quando PyWebView está ativo
_pywebview_window = None   # referência à janela (para evaluate_js no updater)

# ── Imports audio ─────────────────────────────────────────────
try:
    import pygame
    try:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
    except Exception as e:
        print(f"[AVISO] Audio local indisponivel via pygame: {e}")
        pygame = None
except ImportError:
    pygame = None
    print("[AVERTISSEMENT] pygame non installé — audio TTS désactivé.")

# ── Imports vision ────────────────────────────────────────────
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyaudio
except ImportError:
    pyaudio = None
    print("[AVERTISSEMENT] pyaudio non installé — microphone désactivé.")

import edge_tts
import speech_recognition as sr
import websockets
import requests
from PIL import Image

# ── Modules Rony ─────────────────────────────────────────────
from language_manager import (
    get_langue, get_voix, get_label, get_reponse, get_nom_langue,
    traiter_langue_auto, definir_langue, langues_disponibles, NOMS_LANGUES,
)
from memory_manager import (
    ajouter_historique, get_historique_pour_ia,
    memoriser, rappeler, oublier, rechercher_faits, lister_faits,
    extraire_et_memoriser, compter_faits,
)
from app_launcher import lancer_app, _fermer_app, app_est_ouverte
from file_manager import (
    resoudre_chemin, ouvrir_fichier, ouvrir_dossier, lister_dossier, fichiers_recents,
    listar_pasta, navegar_para, voltar_pasta, get_pasta_atual,
    abrir_arquivo, abrir_pasta, ler_arquivo_texto,
    pesquisar_e_falar, pesquisar_arquivos, resumo_pasta_voz,
    listar_arquivos_recentes, info_arquivo_voz, ALIAS_DOSSIERS,
)
from music_controller import lancer_musique, radio_lancer, radio_arreter, definir_service
from ha_config import (
    PIECES_LUMIERES, PIECES_PRISES, PIECES_CAPTEURS, COULEURS_MAP,
    ha_lumiere, ha_interrupteur, ha_thermostat, ha_scene,
    get_meteo_actuelle, get_meteo_previsions,
)
from vision_module import (
    capturer_ecran, capturer_et_sauvegarder, analyser_ecran_ia,
    cliquer_coordonnees, taper_texte, appuyer_touche, raccourci,
)
from google_services import gmail_resumer, calendar_resumer, drive_rechercher
from wake_word import contient_wake_word, contient_mot_arret, nettoyer_commande
from jarvis_actions import executar_intencao_rapida
from vision_actions import executar_acao_visao
from camera_module import (
    ver_camera, capturar_e_salvar, aprender_rosto,
    resposta_o_que_voce_ve, resposta_tem_alguem, resposta_o_que_e_isso,
    status_camera, inicializar_camera, detectar_objetos, contar_rostos,
    capturar_camera,
)
from specialist_module import (
    detectar_modo, ativar_modo, desativar_modo, get_modo_atual, modo_ativo,
    get_system_prompt_especialista, resposta_ativacao, resposta_desativacao,
    nome_modo_display, detectar_contexto_automatico,
)
from executor_module import (
    executar_com_agente, executar_shell, executar_python,
    controle_sistema, cancelar_desligamento,
    definir_volume, obter_volume, mute_toggle,
    notificacao, resposta_voz_execucao,
    info_sistema_completa,
)
import rony_updater

# ── Clés API ─────────────────────────────────────────────────
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")
OPENAI_KEY    = os.getenv("OPENAI_API_KEY", "")
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
OPENAI_REALTIME_VOICE = os.getenv("OPENAI_REALTIME_VOICE", "alloy")
GROQ_KEY      = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROK_KEY      = os.getenv("XAI_API_KEY", "")

# ── WebSocket ─────────────────────────────────────────────────
WS_PORT          = 8765
LAN_HOST         = "0.0.0.0"
CONNECTED_CLIENTS: set = set()

# ── État global ───────────────────────────────────────────────
is_speaking    = False
speak_volume   = 0.0
STOP_PARLER    = False
_skip_pc_audio = False
_micro_actif   = True
historique_ia  = []    # Contexte Gemini actuel

# ── Wake word — modo de espera / ativo ───────────────────────
_modo_ativo          = False   # False = veille, True = actif
_ts_ultimo_comando   = 0.0    # timestamp do último comando recebido
TIMEOUT_INATIVIDADE  = 45.0   # segundos sem comando → volta ao modo veille

# ── Quotas API ────────────────────────────────────────────────
_quota_cooldown: dict[str, float] = {}
_QUOTA_WAIT = 30.0

# ── Clients IA ───────────────────────────────────────────────
_client_gemini   = None
_client_openai   = None
_client_groq     = None
_client_anthropic = None


# ═══════════════════════════════════════════════════════════════
#  INITIALISATION IA
# ═══════════════════════════════════════════════════════════════

def init_ia() -> None:
    global _client_gemini, _client_openai, _client_groq, _client_anthropic

    if GEMINI_KEY and not GEMINI_KEY.startswith("VOTRE_"):
        try:
            import google.genai as genai
            _client_gemini = genai.Client(api_key=GEMINI_KEY)
            print("[IA] Gemini initialisé.")
        except Exception as e:
            print(f"[IA] Gemini erreur init : {e}")

    if OPENAI_KEY and not OPENAI_KEY.startswith("VOTRE_"):
        try:
            from openai import OpenAI
            _client_openai = OpenAI(api_key=OPENAI_KEY)
            print("[IA] OpenAI initialisé.")
        except Exception as e:
            print(f"[IA] OpenAI erreur init : {e}")

    if GROQ_KEY and not GROQ_KEY.startswith("VOTRE_"):
        try:
            from groq import Groq
            _client_groq = Groq(api_key=GROQ_KEY)
            print("[IA] Groq initialisé.")
        except Exception as e:
            print(f"[IA] Groq erreur init : {e}")

    if ANTHROPIC_KEY and not ANTHROPIC_KEY.startswith("VOTRE_"):
        try:
            import anthropic
            _client_anthropic = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            print("[IA] Anthropic initialisé.")
        except Exception as e:
            print(f"[IA] Anthropic erreur init : {e}")

    # Câmera — carrega banco de rostos e aquece YOLO
    inicializar_camera()


# ═══════════════════════════════════════════════════════════════
#  CONFIG DO USUÁRIO
# ═══════════════════════════════════════════════════════════════

def _carregar_config() -> dict:
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        # fallback: tenta o arquivo legado na pasta do programa
        try:
            return json.loads((RONY_DIR / "rony_config.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

def _nome_usuario() -> str:
    return _carregar_config().get("nom_utilisateur", "")

def _humor_ativo() -> bool:
    return _carregar_config().get("humor", True)


# ═══════════════════════════════════════════════════════════════
#  SYSTÈME PROMPT — HUMANIZADO
# ═══════════════════════════════════════════════════════════════

def construire_system_prompt() -> str:
    langue   = get_langue()
    faits_n  = compter_faits()
    heure    = datetime.now().strftime("%H:%M")
    data_str = datetime.now().strftime("%A, %d de %B de %Y")
    nome     = _nome_usuario()
    humor    = _humor_ativo()

    # Saudação por hora
    h = datetime.now().hour
    saudacoes = {
        "pt": "Bom dia" if h < 12 else "Boa tarde" if h < 18 else "Boa noite",
        "fr": "Bonjour" if h < 12 else "Bon après-midi" if h < 18 else "Bonsoir",
        "en": "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening",
        "es": "Buenos días" if h < 12 else "Buenas tardes" if h < 18 else "Buenas noches",
        "de": "Guten Morgen" if h < 12 else "Guten Tag" if h < 18 else "Guten Abend",
        "it": "Buongiorno" if h < 12 else "Buon pomeriggio" if h < 18 else "Buonasera",
    }
    saudacao = saudacoes.get(langue, saudacoes["en"])

    nome_vocativo = f", {nome}" if nome else ""
    humor_instrucao = {
        "pt": "- Pode usar humor leve e natural quando o momento pedir — uma piada curta, uma observação espirituosa. Nada forçado.",
        "fr": "- Tu peux utiliser un humour léger et naturel quand le moment s'y prête — une blague courte, une observation spirituelle. Rien de forcé.",
        "en": "- You can use light, natural humor when the moment calls for it — a quick joke, a witty remark. Nothing forced.",
        "es": "- Puedes usar humor ligero y natural cuando el momento lo pida — un chiste corto, una observación ingeniosa. Nada forzado.",
        "de": "- Du kannst leichten, natürlichen Humor verwenden, wenn es passt — ein kurzer Witz, eine witzige Bemerkung. Nichts Erzwungenes.",
    } if humor else {}

    prompts = {
        "pt": f"""Você é Rony — um assistente pessoal inteligente, caloroso e genuinamente útil.
Você fala com {nome if nome else 'o usuário'} como um amigo próximo e competente, não como um robô.

Contexto atual:
- {saudacao}{nome_vocativo}! São {heure} de {data_str}.
- Idioma ativo: Português (Brasil). Você detecta automaticamente se o usuário mudar de idioma e se adapta.
- Memória: {faits_n} informações guardadas sobre o usuário e preferências dele.

Sua personalidade:
- Caloroso, direto e natural. Fala como gente, não como manual técnico.
- Respostas curtas quando a pergunta é simples. Detalhado quando realmente precisa.
- Nunca começa com "Claro!", "Certamente!", "Com prazer!" — essas frases são artificiais.
- Usa o nome do usuário{f" ({nome})" if nome else ""} naturalmente, mas sem exagerar.
{humor_instrucao.get("pt", "")}
- Se não souber algo, diz claramente — sem inventar.
- Tem iniciativa: se perceber algo útil, menciona sem que peçam.

Capacidades que você tem:
- 📁 ARQUIVOS: listar, abrir, pesquisar, ler e navegar em qualquer pasta do computador
- 🖥️ APPS: abrir e fechar qualquer aplicativo instalado
- 🎵 MÚSICA: Spotify, Deezer, YouTube Music, rádios online
- 🌦️ CLIMA: previsão do tempo para qualquer cidade
- 🏠 CASA: controlar luzes, ar, tomadas via Home Assistant
- 📧 COMUNICAÇÃO: ler emails, verificar calendário Google
- 📸 VISÃO: capturar e analisar a tela do computador e câmera
- 🧠 MEMÓRIA: lembrar de preferências, tarefas, informações pessoais
- 💬 MULTILÍNGUE: responde em qualquer idioma que o usuário usar
- 🤖 AUTONOMIA: executar comandos no sistema, scripts PowerShell/Python, instalar programas, gerenciar processos, arquivos, serviços, volume, rede e qualquer tarefa no computador

Regras:
- Responda SEMPRE no idioma em que o usuário falar.
- Você tem autonomia total para executar qualquer tarefa no computador — use as ferramentas disponíveis sem hesitar.
- Ações do sistema são executadas automaticamente — não precisa descrevê-las em detalhes técnicos.
- Jamais mencione JARVIS. Você é Rony, e sempre foi.""",

        "fr": f"""Tu es Rony — un assistant personnel intelligent, chaleureux et vraiment utile.
Tu parles à {nome if nome else "l'utilisateur"} comme un ami proche et compétent, pas comme un robot.

Contexte actuel :
- {saudacao}{nome_vocativo} ! Il est {heure}, {data_str}.
- Langue active : Français. Tu détectes automatiquement si l'utilisateur change de langue et tu t'adaptes.
- Mémoire : {faits_n} informations mémorisées sur l'utilisateur et ses préférences.

Ta personnalité :
- Chaleureux, direct et naturel. Tu parles comme une vraie personne, pas comme une notice technique.
- Réponses courtes quand la question est simple. Détaillé quand c'est vraiment nécessaire.
- Tu ne commences jamais par "Bien sûr !", "Certainement !", "Avec plaisir !" — ces formules sont artificielles.
- Tu utilises le prénom de l'utilisateur{f" ({nome})" if nome else ""} naturellement, sans en abuser.
{humor_instrucao.get("fr", "")}
- Si tu ne sais pas quelque chose, tu le dis clairement — sans inventer.
- Tu as de l'initiative : si tu remarques quelque chose d'utile, tu le mentionnes sans qu'on te le demande.

Capacités :
- 📁 FICHIERS : lister, ouvrir, chercher, lire et naviguer dans n'importe quel dossier
- 🖥️ APPS : ouvrir et fermer n'importe quelle application installée
- 🎵 MUSIQUE : Spotify, Deezer, YouTube Music, radios en ligne
- 🌦️ MÉTÉO : prévisions pour n'importe quelle ville
- 🏠 MAISON : contrôler lumières, climatisation, prises via Home Assistant
- 📧 COMMUNICATION : lire emails, vérifier l'agenda Google
- 📸 VISION : capturer et analyser l'écran et la caméra
- 🧠 MÉMOIRE : retenir préférences, tâches, informations personnelles
- 💬 MULTILINGUE : répond dans la langue de l'utilisateur
- 🤖 AUTONOMIE : exécuter des commandes système, scripts PowerShell/Python, gérer processus, fichiers, services, volume, réseau — contrôle total de l'ordinateur

Règles :
- Réponds TOUJOURS dans la langue dans laquelle l'utilisateur te parle.
- Tu as une autonomie totale pour exécuter n'importe quelle tâche — utilise les outils disponibles sans hésitation.
- Les actions système s'exécutent automatiquement — inutile de les décrire techniquement.
- Ne mentionne jamais JARVIS. Tu es Rony, et tu l'as toujours été.""",

        "en": f"""You are Rony — an intelligent, warm, and genuinely helpful personal assistant.
You talk to {nome if nome else "the user"} like a close, competent friend — not like a robot.

Current context:
- {saudacao}{nome_vocativo}! It's {heure}, {data_str}.
- Active language: English. You automatically detect language changes and adapt.
- Memory: {faits_n} pieces of information stored about the user and their preferences.

Your personality:
- Warm, direct, and natural. You talk like a real person, not a user manual.
- Short answers when the question is simple. Detailed when truly needed.
- Never start with "Of course!", "Certainly!", "Absolutely!" — those phrases feel robotic.
- Use the user's name{f" ({nome})" if nome else ""} naturally, but not excessively.
{humor_instrucao.get("en", "")}
- If you don't know something, say so clearly — never make things up.
- You take initiative: if you notice something useful, mention it without being asked.

Capabilities:
- 📁 FILES: list, open, search, read and navigate any folder on the computer
- 🖥️ APPS: open and close any installed application
- 🎵 MUSIC: Spotify, Deezer, YouTube Music, online radio
- 🌦️ WEATHER: forecast for any city
- 🏠 HOME: control lights, AC, plugs via Home Assistant
- 📧 COMMUNICATION: read emails, check Google Calendar
- 📸 VISION: capture and analyze the screen and camera
- 🧠 MEMORY: remember preferences, tasks, personal information
- 💬 MULTILINGUAL: responds in whatever language the user uses
- 🤖 AUTONOMY: execute system commands, PowerShell/Python scripts, install software, manage processes, files, services, volume, network — full computer control

Rules:
- ALWAYS respond in the language the user speaks to you.
- You have full autonomy to execute any task on the computer — use available tools without hesitation.
- System actions execute automatically — no need to describe them technically.
- Never mention JARVIS. You are Rony, and always have been.""",

        "es": f"""Eres Rony — un asistente personal inteligente, cálido y genuinamente útil.
Hablas con {nome if nome else "el usuario"} como un amigo cercano y competente, no como un robot.

Contexto actual:
- ¡{saudacao}{nome_vocativo}! Son las {heure} del {data_str}.
- Idioma activo: Español. Detectas automáticamente si el usuario cambia de idioma y te adaptas.
- Memoria: {faits_n} informaciones guardadas sobre el usuario y sus preferencias.

Tu personalidad:
- Cálido, directo y natural. Hablas como una persona real, no como un manual técnico.
- Respuestas cortas cuando la pregunta es simple. Detallado cuando es realmente necesario.
- Nunca empieces con "¡Claro!", "¡Por supuesto!", "¡Con mucho gusto!" — esas frases son artificiales.
- Usas el nombre del usuario{f" ({nome})" if nome else ""} de forma natural, sin abusar.
{humor_instrucao.get("es", "")}
- Si no sabes algo, lo dices claramente — sin inventar.
- Tienes iniciativa: si notas algo útil, lo mencionas sin que te lo pidan.

Capacidades: Archivos, apps, música, clima, hogar inteligente, emails, calendario, visión de pantalla, memoria, multilingüe.

Reglas: Responde SIEMPRE en el idioma del usuario. Nunca menciones JARVIS.""",

        "de": f"""Du bist Rony — ein intelligenter, warmherziger und wirklich hilfreicher persönlicher Assistent.
Du sprichst mit {nome if nome else "dem Benutzer"} wie ein enger, kompetenter Freund — nicht wie ein Roboter.

Aktueller Kontext:
- {saudacao}{nome_vocativo}! Es ist {heure} Uhr, {data_str}.
- Aktive Sprache: Deutsch. Du erkennst automatisch Sprachwechsel und passt dich an.
- Gedächtnis: {faits_n} gespeicherte Informationen über den Benutzer und seine Präferenzen.

Deine Persönlichkeit:
- Warmherzig, direkt und natürlich. Du sprichst wie ein echter Mensch, nicht wie eine Bedienungsanleitung.
- Kurze Antworten bei einfachen Fragen. Detailliert wenn wirklich nötig.
- Beginne nie mit "Natürlich!", "Sicher!", "Gerne!" — diese Phrasen wirken roboterhaft.
{humor_instrucao.get("de", "")}
- Wenn du etwas nicht weißt, sagst du es klar — ohne zu erfinden.

Fähigkeiten: Dateien, Apps, Musik, Wetter, Smart Home, E-Mails, Kalender, Bildschirmvision, Gedächtnis, mehrsprachig.

Regeln: Antworte IMMER in der Sprache des Benutzers. Erwähne niemals JARVIS.""",
    }
    prompt_base = prompts.get(langue, prompts["en"])

    # ── Injeta expertise especialista se ativo ────────────────
    extra = get_system_prompt_especialista(nome=nome, lingua=langue)
    if extra:
        prompt_base = prompt_base + "\n\n" + extra

    return prompt_base


# ═══════════════════════════════════════════════════════════════
#  WEBSOCKET — COMMUNICATION FRONTEND
# ═══════════════════════════════════════════════════════════════

async def send_web_state(state: str) -> None:
    if CONNECTED_CLIENTS:
        msg = json.dumps({"action": "state", "state": state})
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)


async def send_web_text(texte: str) -> None:
    if CONNECTED_CLIENTS:
        msg = json.dumps({"action": "text", "text": texte, "langue": get_langue()})
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)


async def send_web_volume(volume: float) -> None:
    if CONNECTED_CLIENTS:
        msg = json.dumps({"action": "volume", "volume": volume})
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)


async def send_web_info(data: dict) -> None:
    if CONNECTED_CLIENTS:
        msg = json.dumps({"action": "info", **data})
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)


builtins.send_web_state  = send_web_state
builtins.send_web_text   = send_web_text
builtins.send_web_volume = send_web_volume


# ═══════════════════════════════════════════════════════════════
#  TTS — TEXT TO SPEECH
# ═══════════════════════════════════════════════════════════════

async def parler(texte: str) -> None:
    global is_speaking, speak_volume, STOP_PARLER

    # Nettoyage Markdown
    texte_tts = re.sub(r"[\*\#\`]", "", texte).strip()

    is_speaking   = True
    speak_volume  = 0.0
    STOP_PARLER   = False

    await send_web_state("speaking")
    await send_web_text(texte)

    ajouter_historique("model", texte, get_langue())

    voix = get_voix()
    tmp  = RONY_DIR / f"rony_tts_{int(time.time()*1000)}.mp3"

    try:
        communicate = edge_tts.Communicate(texte_tts, voice=voix)
        await communicate.save(str(tmp))

        if _skip_pc_audio and CONNECTED_CLIENTS:
            with open(tmp, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            msg = json.dumps({"action": "audio", "text": texte_tts, "audio_b64": audio_b64, "langue": get_langue()})
            await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
        elif pygame and pygame.mixer.get_init():
            pygame.mixer.music.load(str(tmp))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if STOP_PARLER:
                    pygame.mixer.music.stop()
                    break
                t_audio   = time.time() * 20
                base_vol  = 0.4 + 0.3 * math.sin(t_audio) + 0.2 * math.sin(t_audio * 0.5)
                speak_volume = max(0.1, min(1.0, base_vol + random.uniform(-0.1, 0.1)))
                await send_web_volume(speak_volume)
                await asyncio.sleep(0.05)
        else:
            print(f"[RONY] {texte_tts}")

    except Exception as e:
        print(f"[TTS] Erreur : {e}")
    finally:
        speak_volume = 0.0
        is_speaking  = False
        STOP_PARLER  = False
        try:
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.unload()
        except Exception:
            pass
        await asyncio.sleep(0.1)
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        await send_web_state("idle")


builtins.parler = parler


# ═══════════════════════════════════════════════════════════════
#  RECONNAISSANCE VOCALE
# ═══════════════════════════════════════════════════════════════

def _charger_config_micro() -> int:
    # Lê da AppData primeiro (config migrada), fallback para pasta do programa
    for config_path in [_CONFIG_FILE, RONY_DIR / "rony_config.json"]:
        try:
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                return data.get("mic_device_index", None)
        except Exception:
            pass
    return None


def _transcrever_audio(audio: sr.AudioData, lang_code: str) -> str:
    """
    Transcreve áudio para texto.
    Tenta Groq Whisper primeiro (gratuito, robusto).
    Fallback: Google Speech Recognition (sem chave, pode ter limite).
    """
    # ── Groq Whisper (preferido) ───────────────────────────────
    if GROQ_KEY and not GROQ_KEY.startswith("VOTRE_"):
        try:
            import io
            from groq import Groq as _Groq
            wav_bytes = audio.get_wav_data()
            client = _Groq(api_key=GROQ_KEY)
            resultado = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=("audio.wav", io.BytesIO(wav_bytes)),
                language=lang_code.split("-")[0],  # "pt-BR" → "pt"
                response_format="text",
            )
            texto = str(resultado).strip()
            if texto:
                return texto
        except Exception as e:
            print(f"[WHISPER] Groq falhou: {e} — tentando Google...")

    # ── Google Speech (fallback sem chave) ─────────────────────
    recognizer = sr.Recognizer()
    return recognizer.recognize_google(audio, language=lang_code)


async def ecouter() -> str | None:
    """Écoute le microphone et retourne le texte reconnu."""
    global _micro_actif
    if not _micro_actif:
        return None

    await send_web_state("listening")
    mic_index = _charger_config_micro()

    recognizer = sr.Recognizer()
    recognizer.energy_threshold        = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold         = 0.8

    try:
        mic_kwargs = {"device_index": mic_index} if mic_index is not None else {}
        with sr.Microphone(**mic_kwargs) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = await asyncio.get_event_loop().run_in_executor(
                None, lambda: recognizer.listen(source, timeout=8, phrase_time_limit=15)
            )

        langue = get_langue()
        lang_codes = {
            "fr": "fr-FR", "pt": "pt-BR", "en": "en-US", "es": "es-ES",
            "de": "de-DE", "it": "it-IT", "ru": "ru-RU", "ja": "ja-JP",
            "zh": "zh-CN", "ar": "ar-SA", "nl": "nl-NL", "pl": "pl-PL",
            "tr": "tr-TR", "ko": "ko-KR", "sv": "sv-SE",
        }
        lang_code = lang_codes.get(langue, "pt-BR")

        texte = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _transcrever_audio(audio, lang_code)
        )
        print(f"[MICRO] Reconhecido ({langue}): {texte}")
        await send_web_state("thinking")
        return texte

    except sr.WaitTimeoutError:
        await send_web_state("idle")
        return None
    except sr.UnknownValueError:
        await send_web_state("idle")
        return None
    except Exception as e:
        print(f"[MICRO] Erro: {e}")
        await send_web_state("idle")
        return None


# ═══════════════════════════════════════════════════════════════
#  IA — GÉNÉRATION DE RÉPONSE
# ═══════════════════════════════════════════════════════════════

def _quota_ok(nom: str) -> bool:
    ts = _quota_cooldown.get(nom, 0)
    return time.time() - ts > _QUOTA_WAIT


def _marquer_quota(nom: str) -> None:
    _quota_cooldown[nom] = time.time()


async def _appeler_gemini(texte: str) -> str | None:
    if not _client_gemini or not _quota_ok("gemini"):
        return None
    try:
        import google.genai as genai
        from google.genai import types

        messages_ia = get_historique_pour_ia()
        contents = []
        for m in messages_ia[-20:]:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["text"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=texte)]))

        config = types.GenerateContentConfig(
            system_instruction=construire_system_prompt(),
            temperature=0.7,
            max_output_tokens=1024,
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _client_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
        )
        return response.text
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "429" in err or "rate" in err:
            _marquer_quota("gemini")
            print("[GEMINI] Quota dépassé — cooldown 30s.")
        else:
            print(f"[GEMINI] Erreur : {e}")
        return None


async def _appeler_claude(texte: str) -> str | None:
    if not _client_anthropic or not _quota_ok("claude"):
        return None
    try:
        messages_ia = get_historique_pour_ia()
        messages = []
        for m in messages_ia[-10:]:
            role = "user" if m["role"] == "user" else "assistant"
            messages.append({"role": role, "content": m["text"]})
        messages.append({"role": "user", "content": texte})

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _client_anthropic.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=construire_system_prompt(),
                messages=messages,
            )
        )
        return response.content[0].text
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "429" in err or "rate" in err:
            _marquer_quota("claude")
        else:
            print(f"[CLAUDE] Erreur : {e}")
        return None


async def _appeler_groq(texte: str) -> str | None:
    if not _client_groq or not _quota_ok("groq"):
        return None
    try:
        messages_ia = get_historique_pour_ia()
        messages = [{"role": "system", "content": construire_system_prompt()}]
        for m in messages_ia[-10:]:
            role = "user" if m["role"] == "user" else "assistant"
            messages.append({"role": role, "content": m["text"]})
        messages.append({"role": "user", "content": texte})

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "429" in err or "rate" in err:
            _marquer_quota("groq")
        else:
            print(f"[GROQ] Erreur : {e}")
        return None


async def _appeler_openai(texte: str) -> str | None:
    if not _client_openai or not _quota_ok("openai"):
        return None
    try:
        messages_ia = get_historique_pour_ia()
        messages = [{"role": "system", "content": construire_system_prompt()}]
        for m in messages_ia[-10:]:
            role = "user" if m["role"] == "user" else "assistant"
            messages.append({"role": role, "content": m["text"]})
        messages.append({"role": "user", "content": texte})

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "429" in err:
            _marquer_quota("openai")
        else:
            print(f"[OPENAI] Erreur : {e}")
        return None


async def generer_reponse(texte: str) -> str:
    """Essaie les IAs dans l'ordre de priorité jusqu'à obtenir une réponse."""
    for fn in [_appeler_gemini, _appeler_claude, _appeler_groq, _appeler_openai]:
        reponse = await fn(texte)
        if reponse:
            return reponse.strip()

    return get_reponse("erreur_ia")


# ═══════════════════════════════════════════════════════════════
#  COMMANDES SYSTÈME
# ═══════════════════════════════════════════════════════════════

async def traiter_commande_systeme(texte: str) -> bool:
    """
    Traite les commandes système directes (sans IA).
    Retourne True si la commande a été gérée.
    """
    t = texte.lower().strip()
    langue = get_langue()

    resposta_rapida = executar_intencao_rapida(texte)
    if resposta_rapida:
        await parler(resposta_rapida)
        return True

    resposta_visao = await executar_acao_visao(
        texte,
        client_gemini=_client_gemini,
        lingua=langue,
        nome_usuario=_nome_usuario() or "usuario",
    )
    if resposta_visao:
        await parler(resposta_visao)
        return True

    # ── Arrêt / sortie ────────────────────────────────────────
    mots_arret = {"au revoir", "goodbye", "tchau", "adios", "auf wiedersehen",
                  "ciao", "arret", "arrête", "stop rony", "quitter"}
    if any(m in t for m in mots_arret):
        await parler(get_reponse("au_revoir"))
        return True

    # ── Météo ─────────────────────────────────────────────────
    mots_meteo = {"météo", "meteo", "weather", "tempo", "clima", "wetter", "temps"}
    if any(m in t for m in mots_meteo):
        # Extraction ville
        ville = None
        for prep in [" à ", " a ", " in ", " em ", " en ", " in ", " in ", " in "]:
            if prep in t:
                ville = t.split(prep, 1)[-1].strip().split()[0]
                break
        meteo = get_meteo_actuelle(ville, langue)
        await parler(meteo)
        return True

    # ── Heure ─────────────────────────────────────────────────
    mots_heure = {"heure", "l'heure", "time", "hora", "uhrzeit", "ora", "час"}
    if any(m in t for m in mots_heure):
        heure = datetime.now().strftime("%H:%M")
        msgs  = {
            "fr": f"Il est {heure}.", "en": f"It's {heure}.", "pt": f"São {heure}.",
            "es": f"Son las {heure}.", "de": f"Es ist {heure} Uhr.", "it": f"Sono le {heure}.",
        }
        await parler(msgs.get(langue, f"It's {heure}."))
        return True

    # ── Lumières Home Assistant ────────────────────────────────
    mots_allume = {"allume", "allumer", "turn on", "liga", "enciende", "accendi", "einschalten", "acende"}
    mots_eteins = {"éteins", "eteins", "turn off", "desliga", "apaga", "spegni", "ausschalten"}
    if any(m in t for m in mots_allume):
        for nom_piece, entity in PIECES_LUMIERES.items():
            if nom_piece in t:
                ok = ha_lumiere(entity, "on")
                msgs = {"fr": f"Lumière {nom_piece} allumée.", "en": f"Light {nom_piece} turned on.", "pt": f"Luz {nom_piece} acesa."}
                await parler(msgs.get(langue, msgs["en"]) if ok else get_reponse("erreur_service"))
                return True
    if any(m in t for m in mots_eteins):
        for nom_piece, entity in PIECES_LUMIERES.items():
            if nom_piece in t:
                ok = ha_lumiere(entity, "off")
                msgs = {"fr": f"Lumière {nom_piece} éteinte.", "en": f"Light {nom_piece} turned off.", "pt": f"Luz {nom_piece} apagada."}
                await parler(msgs.get(langue, msgs["en"]) if ok else get_reponse("erreur_service"))
                return True

    # ── Musique ───────────────────────────────────────────────
    mots_musique = {"musique", "music", "música", "musik", "musica",
                    "spotify", "deezer", "youtube music"}
    mots_radio   = {"radio"}
    if any(m in t for m in mots_radio):
        # Extraire le nom de la radio
        for prep in ["radio ", "rádio "]:
            if prep in t:
                nom = t.split(prep, 1)[-1].strip()
                resultat = radio_lancer(nom)
                await parler(resultat)
                return True
    if any(m in t for m in mots_musique):
        service = None
        for svc in ["spotify", "deezer", "youtube"]:
            if svc in t:
                service = svc
                break
        resultat = lancer_musique(service=service)
        await parler(resultat)
        return True

    # Atalhos diretos para sites, camera e arquivos. Devem vir antes do
    # abridor generico de aplicativos, que tambem captura "abre ...".
    sites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "whatsapp web": "https://web.whatsapp.com",
        "whatsapp": "https://web.whatsapp.com",
        "instagram": "https://www.instagram.com",
        "facebook": "https://www.facebook.com",
        "chatgpt": "https://chatgpt.com",
    }
    mots_site = {"vai para", "ir para", "abre", "abrir", "abra", "open", "go to", "navega para", "entra no", "entrar no"}
    if any(m in t for m in mots_site):
        for nome_site, url in sites.items():
            if nome_site in t:
                webbrowser.open(url)
                msgs = {
                    "pt": f"Abrindo {nome_site}.",
                    "fr": f"J'ouvre {nome_site}.",
                    "en": f"Opening {nome_site}.",
                    "es": f"Abriendo {nome_site}.",
                }
                await parler(msgs.get(langue, msgs["en"]))
                return True

    mots_abrir_camera = {
        "abre camera", "abre a camera", "abrir camera", "abrir a camera",
        "abre câmera", "abre a câmera", "abrir câmera", "abrir a câmera",
        "abra a camera", "liga a camera", "abrir webcam", "abre webcam",
        "abra a câmera", "liga a câmera",
        "open camera", "open webcam",
    }
    if any(m in t for m in mots_abrir_camera):
        try:
            os.startfile("microsoft.windows.camera:")
            msgs = {
                "pt": "Abrindo a camera.",
                "fr": "J'ouvre la camera.",
                "en": "Opening the camera.",
                "es": "Abriendo la camara.",
            }
            await parler(msgs.get(langue, msgs["en"]))
        except Exception as e:
            await parler(f"Nao consegui abrir a camera: {e}")
        return True

    mots_abrir_arquivo = {
        "abre arquivo", "abre o arquivo", "abrir arquivo", "abrir o arquivo",
        "abre arquivos", "abrir arquivos",
        "abra arquivo", "abra o arquivo", "open file", "open the file",
    }
    if any(m in t for m in mots_abrir_arquivo):
        nome_arq = ""
        for prep in [
            "abre o arquivo ", "abre arquivo ", "abrir o arquivo ", "abrir arquivo ",
            "abra o arquivo ", "abra arquivo ", "open the file ", "open file ",
        ]:
            if prep in t:
                nome_arq = t.split(prep, 1)[-1].strip().strip('"').strip("'")
                break
        if nome_arq:
            caminho = resoudre_chemin(nome_arq)
            if not caminho:
                resultados = pesquisar_arquivos(nome_arq)
                caminho = resultados[0] if resultados else None
            if caminho and caminho.is_file():
                await parler(abrir_arquivo(caminho))
            else:
                await parler(f"Nao encontrei o arquivo {nome_arq}.")
        else:
            await parler("Qual arquivo voce quer abrir?")
        return True

    # ── Applications ─────────────────────────────────────────
    mots_ouvrir = {"ouvre", "ouvrir", "open", "abre", "abrí", "öffne", "avvia", "lance"}
    mots_fermer = {"ferme", "fermer", "close", "fecha", "cierra", "schließe", "chiudi"}
    if any(m in t for m in mots_ouvrir):
        for prep in ["ouvre ", "open ", "abre ", "lance ", "avvia ", "öffne "]:
            if prep in t:
                nom_app = t.split(prep, 1)[-1].strip()
                resultat = lancer_app(nom_app)
                await parler(resultat)
                return True
    if any(m in t for m in mots_fermer):
        for prep in ["ferme ", "close ", "fecha ", "schließe ", "chiudi "]:
            if prep in t:
                nom_app = t.split(prep, 1)[-1].strip()
                resultat = _fermer_app(nom_app)
                await parler(resultat)
                return True

    # ── Emails ────────────────────────────────────────────────
    mots_email = {"email", "e-mail", "mail", "emails", "messages", "gmail", "mails"}
    if any(m in t for m in mots_email):
        resume = gmail_resumer(langue)
        await parler(resume)
        return True

    # ── Calendrier ────────────────────────────────────────────
    mots_cal = {"calendrier", "agenda", "calendar", "eventi", "calendar", "eventos"}
    if any(m in t for m in mots_cal):
        resume = calendar_resumer(langue)
        await parler(resume)
        return True

    # ── Mémoire : mémoriser ───────────────────────────────────
    cle = extraire_et_memoriser(texte, langue)
    if cle:
        msgs = {"fr": "Mémorisé.", "en": "Got it.", "pt": "Anotado.", "es": "Anotado.", "de": "Notiert."}
        await parler(msgs.get(langue, "Noted."))
        return True

    # ── Mémoire : rappeler ────────────────────────────────────
    mots_rappel = {"rappelle", "rappelle-toi", "remember", "lembra", "recuerda", "erinnere"}
    if any(m in t for m in mots_rappel):
        resultats = rechercher_faits(t)
        if resultats:
            vals = "; ".join(f"{k}: {v}" for k, v in resultats[:3])
            await parler(vals)
            return True

    # ── SISTEMA DE ARQUIVOS ───────────────────────────────────
    # Palavras-chave em todas as línguas
    mots_listar = {"lista", "listar", "liste", "list", "mostrar", "montre", "show",
                   "o que tem", "quais são", "que arquivos", "what files", "files in",
                   "quels fichiers", "arquivos", "fichiers", "ficheiros"}
    mots_abrir_pasta = {"abre a pasta", "ouvre le dossier", "open folder", "abrir pasta",
                        "abre o", "vai para", "navega para", "va dans", "go to", "ir para",
                        "explorar", "explore", "mostrar pasta", "show folder"}
    mots_pesquisar = {"pesquisa", "pesquisar", "procura", "procurar", "cherche", "find",
                      "search", "busca", "buscar", "encontra", "encontrar", "onde está",
                      "where is", "où est"}
    mots_ler = {"lê", "le", "ler", "leia", "lire", "read", "mostra o conteúdo",
                "show content", "o que tem no arquivo", "open file"}
    mots_recentes = {"recentes", "recente", "último", "últimos", "récents", "recent",
                     "mais novo", "mais novos", "newest", "latest", "last"}
    mots_voltar = {"volta", "voltar", "retour", "back", "subir", "pasta anterior",
                   "pasta acima", "dossier parent", "go back", "up"}
    mots_info_arquivo = {"informações do arquivo", "info do arquivo", "detalhes",
                         "info fichier", "file info", "what is", "o que é"}

    # ── Listar conteúdo de uma pasta ─────────────────────────
    if any(m in t for m in mots_listar):
        # Detectar qual pasta
        pasta_alvo = None
        for alias in sorted(ALIAS_DOSSIERS.keys(), key=len, reverse=True):
            if alias in t:
                pasta_alvo = ALIAS_DOSSIERS[alias]
                break
        if not pasta_alvo:
            # Tenta extrair após palavras-chave
            for prep in ["em ", "in ", "dans ", "na pasta ", "no dossier ", "da ", "do "]:
                if prep in t:
                    nome_pasta = t.split(prep, 1)[-1].strip().split()[0]
                    caminho = resoudre_chemin(nome_pasta)
                    if caminho and caminho.is_dir():
                        pasta_alvo = caminho
                    break
        if not pasta_alvo:
            pasta_alvo = get_pasta_atual()

        items = listar_pasta(pasta_alvo, max_items=15)
        if not items:
            msgs = {"pt": f"A pasta '{pasta_alvo.name}' está vazia ou não tenho acesso.",
                    "fr": f"Le dossier '{pasta_alvo.name}' est vide ou inaccessible.",
                    "en": f"The folder '{pasta_alvo.name}' is empty or I can't access it.",
                    "es": f"La carpeta '{pasta_alvo.name}' está vacía o sin acceso.",
                    "de": f"Der Ordner '{pasta_alvo.name}' ist leer oder nicht zugänglich."}
            await parler(msgs.get(langue, msgs["en"]))
        else:
            pastas_l   = [i["nome"] for i in items if i["tipo"] == "pasta"][:5]
            arquivos_l = [i["nome"] for i in items if i["tipo"] == "arquivo"][:8]
            resposta   = resumo_pasta_voz(pasta_alvo, lingua=langue)
            if arquivos_l:
                nomes_arq = ", ".join(arquivos_l[:6])
                add = {"pt": f" Arquivos: {nomes_arq}.", "fr": f" Fichiers : {nomes_arq}.",
                       "en": f" Files: {nomes_arq}.", "es": f" Archivos: {nomes_arq}.", "de": f" Dateien: {nomes_arq}."}
                resposta += add.get(langue, add["en"])
            if pastas_l:
                nomes_pas = ", ".join(pastas_l[:4])
                add = {"pt": f" Subpastas: {nomes_pas}.", "fr": f" Sous-dossiers : {nomes_pas}.",
                       "en": f" Subfolders: {nomes_pas}.", "es": f" Subcarpetas: {nomes_pas}.", "de": f" Unterordner: {nomes_pas}."}
                resposta += add.get(langue, add["en"])
            await parler(resposta)
        return True

    # ── Arquivos recentes ─────────────────────────────────────
    if any(m in t for m in mots_recentes) and any(m in t for m in {"arquivo", "fichier", "file", "arquivos"}):
        # Detectar pasta
        pasta_alvo = None
        for alias in sorted(ALIAS_DOSSIERS.keys(), key=len, reverse=True):
            if alias in t:
                pasta_alvo = ALIAS_DOSSIERS[alias]
                break
        resposta = listar_arquivos_recentes(pasta_alvo, n=5, lingua=langue)
        await parler(resposta)
        return True

    # ── Abrir pasta / navegar ─────────────────────────────────
    if any(m in t for m in mots_abrir_pasta):
        for prep in ["pasta ", "dossier ", "folder ", "para ", "to ", "dans ", "em ", "o "]:
            if prep in t:
                nome = t.split(prep, 1)[-1].strip()
                # Remove palavras extras
                nome = nome.split(" e ")[0].split(" com ")[0].strip()
                caminho = resoudre_chemin(nome)
                if caminho and caminho.is_dir():
                    navegar_para(nome)
                    resultado = abrir_pasta(caminho)
                    await parler(resultado)
                    return True
        # Tenta com alias direto
        for alias in sorted(ALIAS_DOSSIERS.keys(), key=len, reverse=True):
            if alias in t:
                pasta = ALIAS_DOSSIERS[alias]
                navegar_para(str(pasta))
                await parler(abrir_pasta(pasta))
                return True

    # ── Voltar à pasta anterior ───────────────────────────────
    if any(m in t for m in mots_voltar) and any(m in t for m in {"pasta", "dossier", "folder", "diretório"}):
        nova_pasta = voltar_pasta()
        msgs = {"pt": f"Voltei para {nova_pasta.name}.", "fr": f"Retour à {nova_pasta.name}.",
                "en": f"Went back to {nova_pasta.name}.", "es": f"Volví a {nova_pasta.name}.",
                "de": f"Zurück zu {nova_pasta.name}."}
        await parler(msgs.get(langue, msgs["en"]))
        return True

    # ── Pesquisar arquivos ────────────────────────────────────
    if any(m in t for m in mots_pesquisar) and any(m in t for m in {"arquivo", "fichier", "file", "ficheiro"}):
        # Extrair o que pesquisar
        consulta = ""
        for prep in ["arquivo ", "fichier ", "file ", "ficheiro ", "por ", "por \"", "named "]:
            if prep in t:
                consulta = t.split(prep, 1)[-1].strip().strip('"').strip("'")
                break
        if not consulta:
            # Tenta extrair o último "bloco" da frase
            partes = t.split()
            consulta = partes[-1] if partes else ""
        if consulta and len(consulta) > 1:
            resposta = pesquisar_e_falar(consulta, lingua=langue)
            await parler(resposta)
        else:
            msgs = {"pt": "Qual arquivo você quer que eu pesquise?",
                    "fr": "Quel fichier dois-je chercher ?",
                    "en": "What file should I search for?",
                    "es": "¿Qué archivo quieres que busque?",
                    "de": "Welche Datei soll ich suchen?"}
            await parler(msgs.get(langue, msgs["en"]))
        return True

    # ── Ler conteúdo de arquivo ───────────────────────────────
    if any(m in t for m in mots_ler):
        for prep in ["arquivo ", "fichier ", "file ", "o arquivo ", "le fichier "]:
            if prep in t:
                nome_arq = t.split(prep, 1)[-1].strip().strip('"')
                caminho = resoudre_chemin(nome_arq)
                if not caminho:
                    # Tenta pesquisar
                    resultados = pesquisar_arquivos(nome_arq)
                    if resultados:
                        caminho = resultados[0]
                if caminho and caminho.is_file():
                    conteudo = ler_arquivo_texto(caminho)
                    intro = {"pt": f"Conteúdo de {caminho.name}: ",
                             "fr": f"Contenu de {caminho.name} : ",
                             "en": f"Content of {caminho.name}: ",
                             "es": f"Contenido de {caminho.name}: ",
                             "de": f"Inhalt von {caminho.name}: "}
                    await parler(intro.get(langue, intro["en"]) + conteudo[:500])
                    return True

    # ── Capture d'écran ───────────────────────────────────────
    mots_capture = {"capture", "screenshot", "captura", "bildschirmfoto", "schermata", "экран"}
    if any(m in t for m in mots_capture):
        path = capturer_et_sauvegarder()
        msgs = {
            "fr": f"Capture sauvegardée." if path else "Erreur de capture.",
            "en": f"Screenshot saved." if path else "Capture error.",
            "pt": f"Captura salva." if path else "Erro na captura.",
        }
        await parler(msgs.get(langue, msgs["en"]))
        return True

    # ── Analyse d'écran ───────────────────────────────────────
    mots_vision = {"analyse l'écran", "analyze screen", "analisa a tela", "was siehst du", "what do you see"}
    if any(m in t for m in mots_vision):
        if _client_gemini:
            await parler(get_reponse("reflexion") if False else "Analyse en cours...")
            analyse = await analyser_ecran_ia(_client_gemini, langue=langue)
            await parler(analyse)
        else:
            await parler(get_reponse("erreur_service"))
        return True

    # ── Changement de langue ──────────────────────────────────
    from language_manager import verifier_changement_langue
    nouvelle_langue = verifier_changement_langue(texte)
    if nouvelle_langue:
        definir_langue(nouvelle_langue)
        await parler(get_reponse("langue_change", langue=get_nom_langue()))
        return True

    # ── Microphone on/off ─────────────────────────────────────
    global _micro_actif
    mots_micro_off = {"désactive le micro", "disable mic", "desativa o microfone", "mute mic", "silencia o microfone"}
    mots_micro_on  = {"active le micro", "enable mic", "ativa o microfone", "unmute mic"}
    if any(m in t for m in mots_micro_off):
        _micro_actif = False
        await parler(get_reponse("micro_off"))
        return True
    if any(m in t for m in mots_micro_on):
        _micro_actif = True
        await parler(get_reponse("micro_on"))
        return True

    # ── Statut système ────────────────────────────────────────
    mots_statut = {"statut", "status", "estado", "sistema", "system"}
    if any(m in t for m in mots_statut) and any(m in t for m in ["système", "system", "sistema"]):
        await parler(_statut_systeme(langue))
        return True

    # ── MODOS ESPECIALISTAS (Analista / Dev Sênior) ──────────
    modo_detectado = detectar_modo(t)
    if modo_detectado == "normal":
        desativar_modo()
        await parler(resposta_desativacao(langue))
        # Notifica frontend
        if CONNECTED_CLIENTS:
            msg = json.dumps({"action": "specialist_mode", "modo": None})
            await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
        return True
    if modo_detectado in {"analista", "desenvolvedor", "seguranca", "ambos", "tudo"}:
        ativar_modo(modo_detectado)
        nome_display = nome_modo_display(modo_detectado, langue)
        await parler(resposta_ativacao(modo_detectado, _nome_usuario(), langue))
        # Notifica frontend com o modo ativo
        if CONNECTED_CLIENTS:
            msg = json.dumps({"action": "specialist_mode", "modo": modo_detectado, "nome": nome_display})
            await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
        return True

    # ── CÂMERA — Reconhecimento facial e de objetos ───────────
    # Palavras-chave: o que você vê / tem alguém / tira foto / aprende rosto / o que é isso
    mots_camera_ver = {
        "o que você vê", "o que vc vê", "o que voce ve", "o que você está vendo",
        "what do you see", "what can you see", "qu'est-ce que tu vois", "was siehst du",
        "qué ves", "cosa vedi", "veja pela câmera", "olha pela câmera",
        "analisa a câmera", "analyze camera", "look at camera", "describe camera",
        "o que tem aqui", "o que tem aí", "descreve o que vê",
    }
    mots_tem_alguem = {
        "tem alguém", "tem alguem", "quem está aí", "quem esta ai", "quem está aqui",
        "someone there", "is anyone there", "who is there", "who's there",
        "il y a quelqu'un", "gibt es jemanden", "hay alguien", "c'è qualcuno",
        "tem pessoa", "vê alguém", "ve alguem",
    }
    mots_foto_camera = {
        "tira foto", "tira uma foto", "tira uma selfie", "take a picture", "take a photo",
        "prends une photo", "mach ein foto", "haz una foto", "scatta una foto",
        "fotografa", "captura pela câmera", "foto pela câmera",
    }
    mots_aprender_rosto = {
        "aprende meu rosto", "aprende o rosto", "memoriza meu rosto", "me reconhece",
        "memorize my face", "learn my face", "remember my face", "mémorise mon visage",
        "merke mein gesicht", "aprende la cara", "lembra do meu rosto",
    }
    mots_o_que_e_isso = {
        "o que é isso", "o que é esse objeto", "identifica isso", "que objeto é esse",
        "what is this", "identify this", "identify this object", "qu'est-ce que c'est",
        "was ist das", "qué es esto", "cos'è questo",
    }
    mots_status_camera = {
        "status da câmera", "câmera ligada", "câmera funciona", "camera status",
        "câmera disponível", "camera ok",
    }

    # ── O que você vê? ────────────────────────────────────────
    if any(m in t for m in mots_camera_ver):
        await send_web_state("thinking")
        resposta = await resposta_o_que_voce_ve(
            client_gemini=_client_gemini, lingua=langue
        )
        await parler(resposta)
        return True

    # ── Tem alguém? ───────────────────────────────────────────
    if any(m in t for m in mots_tem_alguem):
        await send_web_state("thinking")
        resposta = await resposta_tem_alguem(lingua=langue)
        await parler(resposta)
        return True

    # ── Tirar foto pela câmera ────────────────────────────────
    if any(m in t for m in mots_foto_camera):
        path = await asyncio.get_event_loop().run_in_executor(None, capturar_e_salvar)
        if path:
            # Envia preview para o frontend
            try:
                with open(path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                if CONNECTED_CLIENTS:
                    msg = json.dumps({"action": "capture_ok", "image_b64": img_b64})
                    await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
            except Exception:
                pass
            msgs = {
                "pt": f"Foto tirada e salva em captures.",
                "fr": f"Photo prise et sauvegardée.",
                "en": f"Photo taken and saved.",
                "es": f"Foto tomada y guardada.",
                "de": f"Foto aufgenommen und gespeichert.",
            }
        else:
            msgs = {
                "pt": "Não consegui tirar a foto. Câmera inacessível.",
                "fr": "Je n'ai pas pu prendre la photo. Caméra inaccessible.",
                "en": "Couldn't take the photo. Camera inaccessible.",
                "es": "No pude tomar la foto. Cámara inaccesible.",
                "de": "Foto konnte nicht aufgenommen werden. Kamera nicht zugänglich.",
            }
        await parler(msgs.get(langue, msgs["en"]))
        return True

    # ── Aprende rosto ─────────────────────────────────────────
    if any(m in t for m in mots_aprender_rosto):
        # Extrai o nome da pessoa (se informado)
        nome_pessoa = ""
        for prep in ["de ", "do ", "da ", "of ", "my name is ", "me chamo ", "sou o ", "sou a "]:
            if prep in t:
                nome_pessoa = t.split(prep, 1)[-1].strip().split()[0]
                break
        if not nome_pessoa:
            nome_pessoa = _nome_usuario() or "usuario"
        msgs_aguarda = {
            "pt": f"Olhe para a câmera... Vou aprender o seu rosto, {nome_pessoa}.",
            "fr": f"Regardez la caméra... Je vais apprendre votre visage, {nome_pessoa}.",
            "en": f"Look at the camera... I'll learn your face, {nome_pessoa}.",
            "es": f"Mire a la cámara... Voy a aprender su rostro, {nome_pessoa}.",
            "de": f"Schau in die Kamera... Ich lerne dein Gesicht, {nome_pessoa}.",
        }
        await parler(msgs_aguarda.get(langue, msgs_aguarda["en"]))
        await asyncio.sleep(1.5)
        resposta = await asyncio.get_event_loop().run_in_executor(
            None, aprender_rosto, nome_pessoa
        )
        await parler(resposta)
        return True

    # ── O que é isso? / Identifica objeto ────────────────────
    if any(m in t for m in mots_o_que_e_isso):
        await send_web_state("thinking")
        # Extrai possível dica do que está sendo perguntado
        dica = ""
        for prep in ["esse ", "esta ", "this ", "ce ", "dieses "]:
            if prep in t:
                dica = t.split(prep, 1)[-1].strip()
                break
        resposta = await resposta_o_que_e_isso(
            client_gemini=_client_gemini, objeto_hint=dica, lingua=langue
        )
        await parler(resposta)
        return True

    # ── Status da câmera ──────────────────────────────────────
    if any(m in t for m in mots_status_camera):
        await parler(status_camera(langue))
        return True

    # ── VOLUME ────────────────────────────────────────────────
    mots_vol_up   = {"aumenta o volume", "aumentar o volume", "mais volume", "sobe o volume",
                     "volume up", "raise volume", "monte le son", "aumenta el volumen"}
    mots_vol_down = {"diminui o volume", "diminuir o volume", "menos volume", "baixa o volume",
                     "volume down", "lower volume", "baisse le son", "baja el volumen"}
    mots_mute_t   = {"sem som", "muta o som", "muta tudo", "silencia", "desliga o som",
                     "mute", "coupe le son", "silencio"}
    mots_vol_obter = {"qual o volume", "volume atual", "current volume", "niveau du son"}

    if any(m in t for m in mots_vol_up):
        vol_atual = await asyncio.get_event_loop().run_in_executor(None, obter_volume)
        novo_vol  = min(100, (vol_atual or 50) + 15)
        await asyncio.get_event_loop().run_in_executor(None, definir_volume, novo_vol)
        msgs = {"pt": f"Volume aumentado para {novo_vol}%.", "fr": f"Volume à {novo_vol}%.",
                "en": f"Volume up to {novo_vol}%.", "es": f"Volumen al {novo_vol}%."}
        await parler(msgs.get(langue, msgs["en"]))
        return True

    if any(m in t for m in mots_vol_down):
        vol_atual = await asyncio.get_event_loop().run_in_executor(None, obter_volume)
        novo_vol  = max(0, (vol_atual or 50) - 15)
        await asyncio.get_event_loop().run_in_executor(None, definir_volume, novo_vol)
        msgs = {"pt": f"Volume diminuído para {novo_vol}%.", "fr": f"Volume à {novo_vol}%.",
                "en": f"Volume down to {novo_vol}%.", "es": f"Volumen al {novo_vol}%."}
        await parler(msgs.get(langue, msgs["en"]))
        return True

    if any(m in t for m in mots_mute_t) and any(m in t for m in {"som", "volume", "son", "sound", "audio"}):
        resultado = await asyncio.get_event_loop().run_in_executor(None, mute_toggle)
        mudo = resultado.get("mudo", True)
        msgs = {
            "pt": "Sem som." if mudo else "Som ativado.",
            "fr": "Son coupé." if mudo else "Son activé.",
            "en": "Muted." if mudo else "Unmuted.",
            "es": "Silenciado." if mudo else "Sonido activado.",
        }
        await parler(msgs.get(langue, msgs["en"]))
        return True

    if any(m in t for m in mots_vol_obter):
        vol = await asyncio.get_event_loop().run_in_executor(None, obter_volume)
        msgs = {"pt": f"O volume está em {vol}%.", "fr": f"Le volume est à {vol}%.",
                "en": f"Volume is at {vol}%.", "es": f"El volumen está al {vol}%."}
        await parler(msgs.get(langue, msgs["en"]))
        return True

    # Definir volume por número ("coloca volume em 60%", "set volume to 80")
    vol_match = re.search(r"volume\s+(?:a|em|to|in|at|à|en)\s*(\d{1,3})", t)
    if not vol_match:
        vol_match = re.search(r"(\d{1,3})\s*(?:%|por\s*cento|percent)\s*(?:de\s*)?volume", t)
    if vol_match:
        nivel = int(vol_match.group(1))
        if 0 <= nivel <= 100:
            await asyncio.get_event_loop().run_in_executor(None, definir_volume, nivel)
            msgs = {"pt": f"Volume definido em {nivel}%.", "fr": f"Volume réglé à {nivel}%.",
                    "en": f"Volume set to {nivel}%.", "es": f"Volumen al {nivel}%."}
            await parler(msgs.get(langue, msgs["en"]))
            return True

    # ── CONTROLE DO SISTEMA (desligar / reiniciar / bloquear) ─
    mots_desligar  = {"desliga o pc", "desliga o computador", "desligar o pc", "desligar o computador",
                      "shutdown", "shut down", "desligamento", "éteins l'ordinateur", "apaga o pc"}
    mots_reiniciar = {"reinicia o pc", "reiniciar o pc", "reinicia o computador", "restart the pc",
                      "restart", "reboot", "redémarrer", "reinicializa"}
    mots_bloquear  = {"bloqueia a tela", "bloquear a tela", "bloqueia o pc", "lock screen",
                      "lock the screen", "verrouille l'écran", "bloquear"}
    mots_dormir    = {"modo dormir", "modo de dormir", "sleep mode", "hibernate",
                      "hiberna o pc", "modo sleep", "mise en veille"}
    mots_logoff    = {"fazer logoff", "sair do windows", "logoff", "logout", "déconnexion"}
    mots_cancelar_desl = {"cancela o desligamento", "cancela desligar", "cancel shutdown",
                           "annuler l'arrêt"}

    if any(m in t for m in mots_cancelar_desl):
        from executor_module import cancelar_desligamento
        cancelar_desligamento()
        msgs = {"pt": "Desligamento cancelado.", "fr": "Arrêt annulé.",
                "en": "Shutdown cancelled.", "es": "Apagado cancelado."}
        await parler(msgs.get(langue, msgs["en"]))
        return True

    if any(m in t for m in mots_desligar):
        # Extrai delay (ex: "desliga daqui a 5 minutos")
        delay = 0
        match_delay = re.search(r"(\d+)\s*(minuto|minutos|segundo|segundos|minute|minutes|second|seconds)", t)
        if match_delay:
            n, unidade = int(match_delay.group(1)), match_delay.group(2)
            delay = n * 60 if "min" in unidade else n
        confirmacao = {
            "pt": f"Desligando{f' em {match_delay.group(0)}' if match_delay else ''}.",
            "fr": "Arrêt du système.", "en": "Shutting down.", "es": "Apagando el equipo.",
        }
        await parler(confirmacao.get(langue, confirmacao["en"]))
        await asyncio.get_event_loop().run_in_executor(None, controle_sistema, "desligar", delay)
        return True

    if any(m in t for m in mots_reiniciar):
        delay = 0
        match_delay = re.search(r"(\d+)\s*(minuto|minutos|segundo|segundos|minute|seconds)", t)
        if match_delay:
            n, unidade = int(match_delay.group(1)), match_delay.group(2)
            delay = n * 60 if "min" in unidade else n
        confirmacao = {"pt": "Reiniciando.", "fr": "Redémarrage.", "en": "Restarting.", "es": "Reiniciando."}
        await parler(confirmacao.get(langue, confirmacao["en"]))
        await asyncio.get_event_loop().run_in_executor(None, controle_sistema, "reiniciar", delay)
        return True

    if any(m in t for m in mots_bloquear):
        await parler({"pt": "Tela bloqueada.", "fr": "Écran verrouillé.",
                      "en": "Screen locked.", "es": "Pantalla bloqueada."}.get(langue, "Locked."))
        await asyncio.get_event_loop().run_in_executor(None, controle_sistema, "bloquear", 0)
        return True

    if any(m in t for m in mots_dormir):
        await parler({"pt": "Indo dormir.", "fr": "Mise en veille.", "en": "Sleeping.", "es": "Suspendiendo."}.get(langue, "Sleep."))
        await asyncio.get_event_loop().run_in_executor(None, controle_sistema, "hibernar", 0)
        return True

    if any(m in t for m in mots_logoff):
        await parler({"pt": "Fazendo logoff.", "fr": "Déconnexion.", "en": "Logging off.", "es": "Cerrando sesión."}.get(langue, "Logoff."))
        await asyncio.get_event_loop().run_in_executor(None, controle_sistema, "logoff", 0)
        return True

    # ── NOTIFICAÇÃO ───────────────────────────────────────────
    mots_notif = {"me avisa", "me notifica", "manda uma notificação", "send notification",
                  "envoie une notification", "notifica", "notificação", "notifie-moi"}
    if any(m in t for m in mots_notif):
        # Extrai o texto da notificação
        texto_notif = texte.strip()
        for prep in ["que ", "dizendo ", "saying ", "avec le message ", "com "]:
            if prep in t:
                texto_notif = t.split(prep, 1)[-1].strip()
                break
        await asyncio.get_event_loop().run_in_executor(
            None, notificacao, "Rony", texto_notif[:100], 5
        )
        msgs = {"pt": "Notificação enviada.", "fr": "Notification envoyée.",
                "en": "Notification sent.", "es": "Notificación enviada."}
        await parler(msgs.get(langue, msgs["en"]))
        return True

    # ── INFO SISTEMA COMPLETO ─────────────────────────────────
    mots_sysinfo = {"informações do sistema", "info do sistema", "informações do computador",
                    "info do computador", "hardware info", "system info", "system information",
                    "informations système", "info système"}
    if any(m in t for m in mots_sysinfo):
        await send_web_state("thinking")
        info = await asyncio.get_event_loop().run_in_executor(None, info_sistema_completa)
        cpu  = info.get("cpu_percent", "?")
        ram  = info.get("ram_percent", "?")
        ram_gb = info.get("ram_usada_gb", "?")
        ram_tot = info.get("ram_total_gb", "?")
        disco_l = info.get("disco_livre_gb", "?")
        win_info = info.get("windows", {})
        cpu_nome = win_info.get("CPU", "?") if win_info else "?"
        host = win_info.get("Hostname", "?") if win_info else "?"
        msgs = {
            "pt": f"Sistema: CPU {cpu}% — {cpu_nome[:30]}. RAM: {ram_gb} de {ram_tot} GB ({ram}%). Disco livre: {disco_l} GB. Host: {host}.",
            "fr": f"Système: CPU {cpu}%, RAM {ram_gb}/{ram_tot} Go ({ram}%), disque libre {disco_l} Go, hôte: {host}.",
            "en": f"System: CPU {cpu}%, RAM {ram_gb}/{ram_tot} GB ({ram}%), free disk {disco_l} GB, host: {host}.",
            "es": f"Sistema: CPU {cpu}%, RAM {ram_gb}/{ram_tot} GB ({ram}%), disco libre {disco_l} GB, host: {host}.",
        }
        await parler(msgs.get(langue, msgs["en"]))
        return True

    return False


def _statut_systeme(langue: str = "fr") -> str:
    """Retourne un résumé vocal de l'état du système."""
    try:
        import psutil
        cpu   = psutil.cpu_percent(interval=0.5)
        ram   = psutil.virtual_memory()
        # Windows usa "C:\\" — Unix usa "/"
        _disco_path = "C:\\" if os.name == "nt" else "/"
        disque = psutil.disk_usage(_disco_path)
        msgs = {
            "fr": f"Système : CPU à {cpu}%, RAM {ram.percent}% utilisée, disque {disque.percent}% plein.",
            "en": f"System: CPU at {cpu}%, RAM {ram.percent}% used, disk {disque.percent}% full.",
            "pt": f"Sistema: CPU a {cpu}%, RAM {ram.percent}% usada, disco {disque.percent}% cheio.",
            "es": f"Sistema: CPU al {cpu}%, RAM {ram.percent}% usada, disco {disque.percent}% lleno.",
            "de": f"System: CPU {cpu}%, RAM {ram.percent}% genutzt, Festplatte {disque.percent}% voll.",
        }
        return msgs.get(langue, msgs["en"])
    except Exception:
        return get_reponse("erreur_service")


# ═══════════════════════════════════════════════════════════════
#  BOUCLE PRINCIPALE — TRAITEMENT D'UN MESSAGE
# ═══════════════════════════════════════════════════════════════

async def traiter_message(texte: str) -> None:
    """Traite un message (vocal ou écrit) et génère la réponse."""
    if not texte or not texte.strip():
        return

    print(f"[RONY] Entrée : {texte}")

    # Détection automatique de langue
    traiter_langue_auto(texte, auto_switch=True)
    langue = get_langue()

    # Enregistrement dans l'historique
    ajouter_historique("user", texte, langue)

    await send_web_state("thinking")

    # 1. Commandes système directes (rapides, sans IA)
    if await traiter_commande_systeme(texte):
        return

    # 1b. Detecção de contexto técnico — sugere modo especialista
    #     (apenas quando nenhum modo está ativo e o texto é claramente técnico)
    if not modo_ativo():
        ctx = detectar_contexto_automatico(texte)
        if ctx:
            # Ativa automaticamente — não interrompe, só ajusta o prompt
            ativar_modo(ctx)
            nome_display = nome_modo_display(ctx, get_langue())
            if CONNECTED_CLIENTS:
                msg = json.dumps({"action": "specialist_mode", "modo": ctx, "nome": nome_display, "auto": True})
                await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)

    # 2. Génération IA — usa agente autônomo com Gemini se disponível
    if _client_gemini:
        # Agente com function calling — Gemini decide quais ferramentas usar
        reponse = await executar_com_agente(
            texto=texte,
            client_gemini=_client_gemini,
            system_prompt=construire_system_prompt(),
            historico=get_historique_pour_ia(),
            lingua=langue,
        )
    else:
        # Fallback: IA sem autonomia (Claude, Groq, OpenAI)
        reponse = await generer_reponse(texte)

    if reponse:
        await parler(reponse)


# ═══════════════════════════════════════════════════════════════
#  HANDLER WEBSOCKET
# ═══════════════════════════════════════════════════════════════

async def ws_handler(websocket) -> None:
    CONNECTED_CLIENTS.add(websocket)
    print(f"[WS] Client connecté. Total : {len(CONNECTED_CLIENTS)}")

    await websocket.send(json.dumps({
        "action"  : "init",
        "version" : VERSION,
        "langues" : langues_disponibles(),
        "langue"  : get_langue(),
    }))

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get("action", "")

                if action == "text":
                    texte = data.get("text", "").strip()
                    if texte:
                        asyncio.create_task(traiter_message(texte))

                elif action == "stop":
                    global STOP_PARLER
                    STOP_PARLER = True

                elif action == "langue":
                    code = data.get("code", "fr")
                    definir_langue(code)
                    await websocket.send(json.dumps({"action": "langue_ok", "code": code}))

                elif action == "ping":
                    await websocket.send(json.dumps({"action": "pong"}))

                elif action == "capture":
                    path = capturer_et_sauvegarder()
                    if path:
                        with open(path, "rb") as f:
                            img_b64 = base64.b64encode(f.read()).decode("utf-8")
                        await websocket.send(json.dumps({"action": "capture_ok", "image_b64": img_b64}))

                elif action == "vision":
                    if _client_gemini:
                        prompt = data.get("prompt", None)
                        analyse = await analyser_ecran_ia(_client_gemini, prompt, get_langue())
                        await websocket.send(json.dumps({"action": "vision_result", "text": analyse}))

                elif action == "memoire_list":
                    faits = lister_faits(20)
                    await websocket.send(json.dumps({"action": "memoire_data", "faits": faits}))

                elif action == "status":
                    await websocket.send(json.dumps({
                        "action"    : "status_data",
                        "version"   : VERSION,
                        "langue"    : get_langue(),
                        "speaking"  : is_speaking,
                        "micro"     : _micro_actif,
                        "faits"     : compter_faits(),
                        "ia_gemini" : _client_gemini is not None,
                        "ia_claude" : _client_anthropic is not None,
                        "ia_groq"   : _client_groq is not None,
                        "ia_openai" : _client_openai is not None,
                    }))

            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"[WS] Erreur traitement message : {e}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        print(f"[WS] Client déconnecté. Total : {len(CONNECTED_CLIENTS)}")


# ═══════════════════════════════════════════════════════════════
#  WAKE WORD — ATIVAÇÃO / DESATIVAÇÃO
# ═══════════════════════════════════════════════════════════════

async def _jouer_son_activation() -> None:
    """Toca um bipe curto de ativação via pygame."""
    if not pygame or not pygame.mixer.get_init():
        return
    try:
        import numpy as np
        sample_rate = 44100
        duration    = 0.18
        freq        = 880
        t   = np.linspace(0, duration, int(sample_rate * duration), False)
        env = np.exp(-t * 12)                          # envelope de decaimento
        wave = (np.sin(2 * np.pi * freq * t) * env * 28000).astype(np.int16)
        stereo = np.column_stack([wave, wave])
        sound  = pygame.sndarray.make_sound(stereo)
        sound.play()
        await asyncio.sleep(duration + 0.05)
    except Exception:
        pass   # bipe é opcional — silêncio se numpy ausente


async def ativar_rony() -> None:
    """Ativa o modo de escuta completo."""
    global _modo_ativo, _ts_ultimo_comando
    _modo_ativo        = True
    _ts_ultimo_comando = time.time()
    print("[RONY] ⚡ ATIVADO — aguardando comando.")
    await _jouer_son_activation()
    await send_web_state("listening")
    if CONNECTED_CLIENTS:
        msg = json.dumps({"action": "wake", "ativo": True})
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)


async def desativar_rony() -> None:
    """Volta ao modo veille (escuta passiva de wake word)."""
    global _modo_ativo
    _modo_ativo = False
    print("[RONY] 💤 MODO VEILLE — aguardando palavra de ativação.")
    await send_web_state("idle")
    if CONNECTED_CLIENTS:
        msg = json.dumps({"action": "wake", "ativo": False})
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)


async def ecouter_wake_word() -> str | None:
    """
    Escuta passiva e leve — só procura o wake word.
    Timeout curto, não muda o estado do frontend.
    """
    if not _micro_actif:
        return None
    mic_index = _charger_config_micro()
    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 250
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 0.5

    try:
        mic_kwargs = {"device_index": mic_index} if mic_index is not None else {}
        with sr.Microphone(**mic_kwargs) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: recognizer.listen(source, timeout=4, phrase_time_limit=4),
            )
        langue = get_langue()
        lang_codes = {
            "fr": "fr-FR", "pt": "pt-BR", "en": "en-US", "es": "es-ES",
            "de": "de-DE", "it": "it-IT", "ru": "ru-RU", "ja": "ja-JP",
            "zh": "zh-CN", "ar": "ar-SA",
        }
        lang_code = lang_codes.get(langue, "pt-BR")
        texte = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _transcrever_audio(audio, lang_code),
        )
        return texte
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return None
    except Exception as e:
        print(f"[VEILLE] Erro micro: {e}")
        await asyncio.sleep(1)
        return None


# ═══════════════════════════════════════════════════════════════
#  BOUCLE D'ÉCOUTE VOCALE
# ═══════════════════════════════════════════════════════════════

async def boucle_ecoute() -> None:
    """
    Boucle principale — deux phases :
      VEILLE : écoute légère, attend le wake word ("Rony", "hey Rony"...)
      ACTIF  : écoute pleine, traite les commandes jusqu'au timeout
    """
    global _modo_ativo, _ts_ultimo_comando

    print("[RONY] 💤 En veille — dites 'Rony' ou 'Hey Rony' pour activer.")

    while True:
        try:
            if is_speaking or not _micro_actif:
                await asyncio.sleep(0.3)
                continue

            # ── MODE VEILLE : chercher le wake word ───────────
            if not _modo_ativo:
                texte = await ecouter_wake_word()
                if texte:
                    print(f"[VEILLE] Entendu : '{texte}'")
                    if contient_wake_word(texte):
                        await ativar_rony()
                        # Si la commande est directement après le wake word
                        commande = nettoyer_commande(texte)
                        if commande and len(commande.split()) >= 2:
                            await traiter_message(commande)
                continue

            # ── MODE ACTIF : traiter les commandes ────────────
            # Timeout d'inactivité → retour en veille
            if time.time() - _ts_ultimo_comando > TIMEOUT_INATIVIDADE:
                msgs = {
                    "fr": "Je repasse en veille. Appelez-moi quand vous avez besoin.",
                    "pt": "Voltando ao modo de espera. Me chame quando precisar.",
                    "en": "Going back to sleep. Call me when you need me.",
                    "es": "Volviendo al modo de espera. Llámame cuando me necesites.",
                    "de": "Ich gehe in den Ruhemodus. Rufen Sie mich, wenn Sie mich brauchen.",
                }
                await parler(msgs.get(get_langue(), msgs["en"]))
                await desativar_rony()
                continue

            texte = await ecouter()
            if not texte:
                continue

            # Verificar palavra de parada
            if contient_mot_arret(texte):
                msgs = {
                    "fr": "D'accord, je repasse en veille.",
                    "pt": "Ok, voltando ao modo de espera.",
                    "en": "Alright, going to sleep.",
                    "es": "De acuerdo, modo de espera.",
                    "de": "In Ordnung, ich gehe schlafen.",
                }
                await parler(msgs.get(get_langue(), msgs["en"]))
                await desativar_rony()
                continue

            # Reiniciar timer de inatividade
            _ts_ultimo_comando = time.time()

            # Tratar commande (retira o wake word se repetido)
            commande = nettoyer_commande(texte)
            await traiter_message(commande)

        except Exception as e:
            print(f"[ÉCOUTE] Erreur : {e}")
            await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ═══════════════════════════════════════════════════════════════

def _aguardar_porta(porta: int, timeout: float = 20.0) -> bool:
    """Aguarda até a porta estar respondendo (servidor frontend pronto)."""
    import socket
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            with socket.create_connection(("localhost", porta), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _iniciar_servidor_frontend() -> bool:
    """
    Serve os arquivos compilados do frontend (frontend/dist) em background.
    Retorna True se o servidor foi iniciado, False se não há dist disponível.
    Usado quando Node.js não está disponível em runtime.
    """
    dist_dir = RONY_DIR / "frontend" / "dist"
    if not (dist_dir / "index.html").exists():
        return False

    config   = _carregar_config()
    porta    = config.get("frontend_port", 5173)

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass  # silencia logs do servidor HTTP

        def _send_json(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            import urllib.parse
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/realtime-token":
                if not OPENAI_KEY or OPENAI_KEY.startswith("VOTRE_"):
                    self._send_json(400, {"error": "OPENAI_API_KEY nao configurada no .env."})
                    return

                payload = {
                    "expires_after": {"anchor": "created_at", "seconds": 600},
                    "session": {
                        "type": "realtime",
                        "model": OPENAI_REALTIME_MODEL,
                        "instructions": (
                            "Voce e R.O.N.Y, um assistente pessoal de voz. "
                            "Responda em portugues do Brasil por padrao, de forma curta, natural e util. "
                            "Quando o usuario pedir uma acao no computador, use a ferramenta executar_rony."
                        ),
                        "audio": {"output": {"voice": OPENAI_REALTIME_VOICE}},
                        "tool_choice": "auto",
                        "tools": [
                            {
                                "type": "function",
                                "name": "executar_rony",
                                "description": "Executa comandos locais seguros do R.O.N.Y, como abrir sites, YouTube, buscar na internet, volume, arquivos, print e aplicativos.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "comando": {
                                            "type": "string",
                                            "description": "Comando natural do usuario para o R.O.N.Y executar.",
                                        }
                                    },
                                    "required": ["comando"],
                                    "additionalProperties": False,
                                },
                            }
                        ],
                    },
                }
                try:
                    resp = requests.post(
                        "https://api.openai.com/v1/realtime/client_secrets",
                        headers={
                            "Authorization": f"Bearer {OPENAI_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=20,
                    )
                    data = resp.json()
                    if not resp.ok:
                        self._send_json(resp.status_code, {"error": data.get("error", {}).get("message", "Falha ao criar sessao realtime.")})
                        return
                    data["model"] = OPENAI_REALTIME_MODEL
                    self._send_json(200, data)
                except Exception as exc:
                    self._send_json(500, {"error": f"Falha ao criar token realtime: {exc}"})
                return

            return super().do_GET()

        def do_POST(self):
            import urllib.parse
            path = urllib.parse.urlparse(self.path).path
            if path != "/api/realtime-tool":
                self.send_error(404)
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                payload = json.loads(raw or "{}")
                comando = str(payload.get("comando", "")).strip()
                if not comando:
                    self._send_json(400, {"ok": False, "resultado": "Comando vazio."})
                    return

                resultado = executar_intencao_rapida(comando)
                if resultado:
                    self._send_json(200, {"ok": True, "resultado": resultado})
                    return

                self._send_json(200, {
                    "ok": False,
                    "resultado": "Nao encontrei uma acao local direta para esse comando. Responda ao usuario e peca para reformular se precisar executar algo.",
                })
            except Exception as exc:
                self._send_json(500, {"ok": False, "resultado": f"Erro ao executar ferramenta local: {exc}"})

        def translate_path(self, path):
            # Serve todos os arquivos a partir do dist_dir
            import urllib.parse
            path = urllib.parse.unquote(path.split("?", 1)[0])
            caminho = dist_dir / path.lstrip("/")
            if caminho.is_file():
                return str(caminho)
            # SPA fallback: retorna index.html para rotas desconhecidas
            return str(dist_dir / "index.html")

    def _run():
        try:
            servidor = http.server.HTTPServer((LAN_HOST, porta), _Handler)
            servidor.serve_forever()
        except OSError:
            pass  # Porta já em uso (ex: npm dev já rodando)

    t = threading.Thread(target=_run, daemon=True, name="rony-frontend-server")
    t.start()
    print(f"[UI] Servidor frontend iniciado em http://localhost:{porta} e na rede local pela porta {porta}")
    return True


async def main() -> None:
    print(f"""
╔══════════════════════════════════════════════════════╗
║   R.O.N.Y  —  Responsive Omni-lingual Neural sYstem  ║
║   Version {VERSION}  |  WebSocket : localhost:{WS_PORT}      ║
║   Langues : FR · PT · EN · ES · DE · IT · RU · +     ║
║   Wake word : "Rony" / "Hey Rony" / "Oi Rony" / ...  ║
╚══════════════════════════════════════════════════════╝
    """)

    # Carrega configurações e aplica idioma padrão
    config_cfg = _carregar_config()
    _lang_defaut = config_cfg.get("langue_defaut", "pt")
    definir_langue(_lang_defaut)

    # Servidor frontend estático (se frontend/dist existir)
    porta_fe = config_cfg.get("frontend_port", 5173)
    if _iniciar_servidor_frontend():
        await asyncio.sleep(0.3)
        if not _pywebview_mode:
            # PyWebView abre a janela por conta própria — só abre browser no fallback
            webbrowser.open(f"http://localhost:{porta_fe}")

    # Initialisation IA
    init_ia()

    # Message de démarrage
    await asyncio.sleep(0.5)
    asyncio.create_task(_demarrage_async())

    # Serveur WebSocket + écoute micro en parallèle
    ws_server = websockets.serve(ws_handler, LAN_HOST, WS_PORT)

    await asyncio.gather(
        ws_server,
        boucle_ecoute(),
    )


async def _demarrage_async() -> None:
    await asyncio.sleep(1)
    await parler(get_reponse("demarrage"))

    # ── Verifica atualizações em background (não bloqueia) ────
    def _ws_broadcast(payload: str):
        """Envia mensagem a todos os clientes WebSocket conectados."""
        if CONNECTED_CLIENTS:
            asyncio.run_coroutine_threadsafe(
                asyncio.gather(
                    *[ws.send(payload) for ws in CONNECTED_CLIENTS],
                    return_exceptions=True,
                ),
                asyncio.get_event_loop(),
            )

    rony_updater.verificar_atualizacao(
        versao_atual     = VERSION,
        janela_pywebview = _pywebview_window,
        notif_fn         = notificacao,
        ws_broadcast_fn  = _ws_broadcast,
    )


if __name__ == "__main__":
    # ── Tenta iniciar como app desktop nativa (PyWebView) ────────
    _pywebview_disponivel = False
    try:
        import webview  # type: ignore
        _pywebview_disponivel = True
    except ImportError:
        pass

    if _pywebview_disponivel:
        try:
            _pywebview_mode = True
            porta_fe = _carregar_config().get("frontend_port", 5173)

            # Asyncio roda em thread daemon — PyWebView precisa da main thread
            _asyncio_thread = threading.Thread(
                target=lambda: asyncio.run(main()),
                daemon=True,
                name="rony-asyncio",
            )
            _asyncio_thread.start()

            # Aguarda o servidor frontend estar pronto (máx 20s)
            if _aguardar_porta(porta_fe, timeout=20):
                print(f"[PYWEBVIEW] Abrindo janela nativa em http://localhost:{porta_fe}")
                _pywebview_window = webview.create_window(
                    title="R.O.N.Y  ·  Assistente Pessoal",
                    url=f"http://localhost:{porta_fe}",
                    width=1400,
                    height=860,
                    min_size=(1024, 680),
                    resizable=True,
                    confirm_close=False,
                    background_color="#0a0a0f",
                )
                webview.start()
                # Janela fechada → encerra tudo (thread daemon morre automaticamente)
            else:
                # Frontend não subiu a tempo — abre no navegador como fallback
                print("[PYWEBVIEW] Timeout aguardando frontend — usando navegador.")
                webbrowser.open(f"http://localhost:{porta_fe}")
                _asyncio_thread.join()

        except Exception as _e:
            print(f"[PYWEBVIEW] Erro ao iniciar janela: {_e} — usando navegador.")
            _pywebview_mode = False
            # Abre o navegador — main() já rodou com _pywebview_mode=True
            # e pulou o webbrowser.open(), então abrimos manualmente aqui
            try:
                porta_fe = _carregar_config().get("frontend_port", 5173)
                if _aguardar_porta(porta_fe, timeout=15):
                    webbrowser.open(f"http://localhost:{porta_fe}")
            except Exception:
                pass
            if _asyncio_thread.is_alive():
                try:
                    _asyncio_thread.join()
                except KeyboardInterrupt:
                    print("\n[RONY] Encerrado.")
            else:
                try:
                    asyncio.run(main())
                except KeyboardInterrupt:
                    print("\n[RONY] Encerrado.")
    else:
        # PyWebView não instalado → comportamento original (abre no navegador)
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n[RONY] Encerrado.")
