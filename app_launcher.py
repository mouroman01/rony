# ============================================================
#  app_launcher.py — Lancement / fermeture d'applications
#  R.O.N.Y — Amélioration JARVIS : cache TTL + noms multilingues
# ============================================================

import os
import subprocess
import winreg
import psutil
import time
from pathlib import Path
from typing import Optional

# ── TTL du cache de découverte (5 min) ───────────────────────
_CACHE_APPS: dict[str, str] = {}
_CACHE_TS: float = 0.0
_CACHE_TTL: float = 300.0

# ═══════════════════════════════════════════════════════════════
#  CATALOGUE STATIQUE (chemins connus + noms multilingues)
# ═══════════════════════════════════════════════════════════════
_APPS_CATALOGUE: dict[str, list[str]] = {
    # Navigateurs
    "chrome":    ["chrome", "google chrome", "navegador", "browser", "navegador chrome"],
    "firefox":   ["firefox", "mozilla", "foxfire"],
    "edge":      ["edge", "microsoft edge"],
    "brave":     ["brave"],
    "opera":     ["opera"],

    # Média
    "spotify":   ["spotify", "musique", "music", "música", "musik", "musica"],
    "vlc":       ["vlc", "lecteur vidéo", "video player", "leitor de vídeo"],
    "mpc":       ["mpc", "media player classic"],
    "mpv":       ["mpv"],

    # Communication
    "discord":   ["discord"],
    "telegram":  ["telegram"],
    "whatsapp":  ["whatsapp"],
    "teams":     ["teams", "microsoft teams"],
    "zoom":      ["zoom"],
    "slack":     ["slack"],
    "skype":     ["skype"],

    # Éditeurs
    "vscode":    ["vscode", "visual studio code", "code", "editeur", "editor", "editor de código"],
    "notepad":   ["notepad", "bloc-notes", "bloc notes", "bloco de notas"],
    "notepad++": ["notepad++", "notepadpp"],
    "sublime":   ["sublime", "sublime text"],

    # Bureautique
    "word":      ["word", "microsoft word"],
    "excel":     ["excel", "microsoft excel"],
    "powerpoint":["powerpoint", "microsoft powerpoint", "ppt"],
    "outlook":   ["outlook", "microsoft outlook"],

    # Outils système
    "explorer":  ["explorateur", "explorer", "gestionnaire de fichiers", "file explorer", "explorador de arquivos", "gerenciador de arquivos"],
    "taskmgr":   ["gestionnaire des tâches", "task manager", "gerenciador de tarefas", "administrador de tareas"],
    "cmd":       ["cmd", "invite de commandes", "terminal", "prompt", "command prompt"],
    "powershell":["powershell", "ps"],
    "calculator":["calculatrice", "calculator", "calculadora", "rechner"],
    "paint":     ["paint", "ms paint"],
    "mspaint":   ["paint", "ms paint"],

    # Gaming / Streaming
    "obs":       ["obs", "obs studio", "stream", "streaming"],
    "steam":     ["steam"],
    "epic":      ["epic games", "epic"],
    "geforce":   ["geforce experience", "nvidia"],

    # Utilitaires
    "7zip":      ["7zip", "7-zip", "archiver", "archive"],
    "winrar":    ["winrar", "rar"],
    "everything":["everything"],
}

# Chemins d'installation connus (fixes)
_CHEMINS_CONNUS: dict[str, list[str]] = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "vlc": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "discord": [
        str(Path.home() / "AppData/Local/Discord/Update.exe"),
    ],
    "spotify": [
        str(Path.home() / "AppData/Roaming/Spotify/Spotify.exe"),
    ],
    "vscode": [
        str(Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "notepad++": [
        r"C:\Program Files\Notepad++\notepad++.exe",
        r"C:\Program Files (x86)\Notepad++\notepad++.exe",
    ],
    "obs": [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\32bit\obs32.exe",
    ],
    "steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],
    "7zip": [
        r"C:\Program Files\7-Zip\7zFM.exe",
        r"C:\Program Files (x86)\7-Zip\7zFM.exe",
    ],
}

# Apps système Windows (via commande directe)
_APPS_SYSTEME: dict[str, str] = {
    "explorer"  : "explorer",
    "taskmgr"   : "taskmgr",
    "cmd"       : "cmd",
    "powershell": "powershell",
    "calculator": "calc",
    "paint"     : "mspaint",
    "mspaint"   : "mspaint",
    "notepad"   : "notepad",
    "word"      : "WINWORD",
    "excel"     : "EXCEL",
    "powerpoint": "POWERPNT",
    "outlook"   : "OUTLOOK",
}


# ═══════════════════════════════════════════════════════════════
#  DÉCOUVERTE VIA REGISTRE WINDOWS
# ═══════════════════════════════════════════════════════════════

def _scanner_registre() -> dict[str, str]:
    """Scanne le registre Windows pour trouver les applications installées."""
    apps: dict[str, str] = {}
    cles = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for hive, chemin in cles:
        try:
            cle = winreg.OpenKey(hive, chemin)
            for i in range(winreg.QueryInfoKey(cle)[0]):
                try:
                    nom_exe = winreg.EnumKey(cle, i)
                    sous_cle = winreg.OpenKey(cle, nom_exe)
                    path, _ = winreg.QueryValueEx(sous_cle, "")
                    if path and os.path.exists(path):
                        nom_clean = nom_exe.lower().replace(".exe", "")
                        apps[nom_clean] = path
                except Exception:
                    pass
        except Exception:
            pass
    return apps


def _get_cache_apps() -> dict[str, str]:
    global _CACHE_APPS, _CACHE_TS
    if time.time() - _CACHE_TS > _CACHE_TTL:
        _CACHE_APPS = _scanner_registre()
        _CACHE_TS   = time.time()
    return _CACHE_APPS


# ═══════════════════════════════════════════════════════════════
#  RÉSOLUTION D'UN NOM VOCAL → CHEMIN EXE
# ═══════════════════════════════════════════════════════════════

def _resoudre_app(nom_vocal: str) -> Optional[str]:
    nom = nom_vocal.lower().strip()

    # 1. Correspondance directe dans le catalogue
    for exe_name, aliases in _APPS_CATALOGUE.items():
        if nom in aliases or nom == exe_name:
            # Chercher dans les chemins connus
            if exe_name in _CHEMINS_CONNUS:
                for chemin in _CHEMINS_CONNUS[exe_name]:
                    if os.path.exists(chemin):
                        return chemin
            # Chercher dans le registre
            cache = _get_cache_apps()
            if exe_name in cache:
                return cache[exe_name]
            # Système Windows
            if exe_name in _APPS_SYSTEME:
                return _APPS_SYSTEME[exe_name]

    # 2. Correspondance partielle dans le registre
    cache = _get_cache_apps()
    for nom_reg, chemin in cache.items():
        if nom in nom_reg or nom_reg in nom:
            return chemin

    # 3. Système Windows direct
    if nom in _APPS_SYSTEME:
        return _APPS_SYSTEME[nom]

    return None


# ═══════════════════════════════════════════════════════════════
#  LANCEMENT / FERMETURE
# ═══════════════════════════════════════════════════════════════

def lancer_app(nom_vocal: str, url: str = None) -> str:
    """Lance une application par son nom vocal. Retourne un message de statut."""
    if url:
        subprocess.Popen(["explorer", url], shell=True)
        return f"Ouverture de {url}"

    chemin = _resoudre_app(nom_vocal)
    if not chemin:
        return f"Application '{nom_vocal}' introuvable."

    try:
        if chemin in _APPS_SYSTEME.values() or not os.path.sep in chemin:
            subprocess.Popen(chemin, shell=True)
        else:
            subprocess.Popen([chemin], shell=False)
        return f"Lancement de {nom_vocal}."
    except Exception as e:
        return f"Erreur lors du lancement de {nom_vocal} : {e}"


def _fermer_app(nom_vocal: str) -> str:
    """Ferme un processus par nom vocal."""
    nom = nom_vocal.lower().strip()

    # Correspondance catalogue → nom de processus
    noms_process = {
        "chrome": ["chrome.exe"], "firefox": ["firefox.exe"], "edge": ["msedge.exe"],
        "spotify": ["spotify.exe"], "discord": ["discord.exe"], "vlc": ["vlc.exe"],
        "vscode": ["code.exe"], "obs": ["obs64.exe", "obs32.exe"],
        "steam": ["steam.exe"], "teams": ["teams.exe"], "zoom": ["zoom.exe"],
        "slack": ["slack.exe"],
        "camera": ["WindowsCamera.exe"], "câmera": ["WindowsCamera.exe"],
        "webcam": ["WindowsCamera.exe"], "windows camera": ["WindowsCamera.exe"],
    }

    cibles = []
    for exe, aliases in _APPS_CATALOGUE.items():
        if nom in aliases or nom == exe:
            cibles = noms_process.get(exe, [f"{exe}.exe"])
            break

    if not cibles:
        cibles = [f"{nom}.exe"]

    fermes = 0
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"].lower() in [c.lower() for c in cibles]:
                proc.terminate()
                fermes += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return f"{fermes} instance(s) de '{nom_vocal}' fermée(s)." if fermes else f"'{nom_vocal}' n'était pas ouvert."


def app_est_ouverte(nom_vocal: str) -> bool:
    """Vérifie si une application est en cours d'exécution."""
    nom = nom_vocal.lower().strip()
    for proc in psutil.process_iter(["name"]):
        try:
            if nom in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False
