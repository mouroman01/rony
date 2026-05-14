# ============================================================
#  music_controller.py — Contrôle musical unifié
#  R.O.N.Y — Spotify + Deezer + YouTube Music + Radio
#  Amélioration JARVIS : détection automatique du service actif
# ============================================================

import os
import subprocess
import webbrowser
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_URI        = os.getenv("SPOTIFY_MUSIQUE_URI", "")
DEEZER_URL         = os.getenv("DEEZER_MUSIQUE_URL", "")
YOUTUBE_MUSIC_URL  = os.getenv("YOUTUBE_MUSIQUE_URL", "https://music.youtube.com")

SPOTIFY_EXE = Path.home() / "AppData/Roaming/Spotify/Spotify.exe"

# ── Service musical préféré ───────────────────────────────────
_service_actif = "auto"   # "spotify" | "deezer" | "youtube" | "auto"

# ── Radios en ligne (URL de flux) ────────────────────────────
RADIOS = {
    # FR
    "france inter"   : "https://icecast.radiofrance.fr/franceinter-midfi.mp3",
    "france info"    : "https://icecast.radiofrance.fr/franceinfo-midfi.mp3",
    "nrj"            : "https://scdn.nrjaudio.fm/adwz1/fr/30001/mp3_128.mp3",
    "skyrock"        : "https://icecast.skyrock.net/s/natio_mp3_128k",
    "fun radio"      : "https://streaming.fun-radio.fr/fun-radio/all/mp3/128",
    "rtl"            : "https://streaming.rtl.fr/rtl-1-44-128",

    # Internacional
    "bbc radio 1"    : "https://stream.live.vc.bbcmedia.co.uk/bbc_radio_one",
    "bbc radio 2"    : "https://stream.live.vc.bbcmedia.co.uk/bbc_radio_two",
    "lofi hip hop"   : "https://streams.ilovemusic.de/iloveradio17.mp3",
    "jazz"           : "https://streaming.radio.co/s2e83a4891/listen",
    "classique"      : "https://mediaserv30.live-streams.nl:8036/stream",
    "classic"        : "https://mediaserv30.live-streams.nl:8036/stream",
    "clássica"       : "https://mediaserv30.live-streams.nl:8036/stream",
    "rádio brasil"   : "https://31593.live.streamtheworld.com/RADIOBRASIL_ADP.aac",
    "radio brasil"   : "https://31593.live.streamtheworld.com/RADIOBRASIL_ADP.aac",
}

# ── Playlists Spotify nommées ─────────────────────────────────
PLAYLISTS_SPOTIFY: dict[str, str] = {
    "principale"   : SPOTIFY_URI,
    "main"         : SPOTIFY_URI,
    "principal"    : SPOTIFY_URI,
    "principal"    : SPOTIFY_URI,
}

# ── Playlists Deezer nommées ──────────────────────────────────
PLAYLISTS_DEEZER: dict[str, str] = {
    "principale"   : DEEZER_URL,
    "main"         : DEEZER_URL,
    "principal"    : DEEZER_URL,
}


# ═══════════════════════════════════════════════════════════════
#  SPOTIFY
# ═══════════════════════════════════════════════════════════════

def spotify_disponible() -> bool:
    return SPOTIFY_EXE.exists()


def spotify_lancer(uri: str = None) -> str:
    uri = uri or SPOTIFY_URI
    if not spotify_disponible():
        return "Spotify n'est pas installé."
    try:
        if uri:
            subprocess.Popen([str(SPOTIFY_EXE), f"--uri={uri}"])
        else:
            subprocess.Popen([str(SPOTIFY_EXE)])
        return "Spotify lancé."
    except Exception as e:
        return f"Erreur Spotify : {e}"


def spotify_lancer_playlist(nom: str = "principale") -> str:
    uri = PLAYLISTS_SPOTIFY.get(nom.lower(), SPOTIFY_URI)
    return spotify_lancer(uri)


def spotify_chercher(requete: str) -> str:
    """Ouvre une recherche Spotify dans le navigateur."""
    url = f"https://open.spotify.com/search/{requests.utils.quote(requete)}"
    webbrowser.open(url)
    return f"Recherche Spotify : {requete}."


# ═══════════════════════════════════════════════════════════════
#  DEEZER
# ═══════════════════════════════════════════════════════════════

def deezer_lancer(url: str = None) -> str:
    url = url or DEEZER_URL
    if not url:
        url = "https://www.deezer.com"
    webbrowser.open(url)
    return "Deezer ouvert."


def deezer_chercher(requete: str) -> str:
    url = f"https://www.deezer.com/search/{requests.utils.quote(requete)}"
    webbrowser.open(url)
    return f"Recherche Deezer : {requete}."


# ═══════════════════════════════════════════════════════════════
#  YOUTUBE MUSIC
# ═══════════════════════════════════════════════════════════════

def youtube_music_lancer(requete: str = None) -> str:
    if requete:
        url = f"https://music.youtube.com/search?q={requests.utils.quote(requete)}"
    else:
        url = YOUTUBE_MUSIC_URL
    webbrowser.open(url)
    msg = f"Tocando {requete} no YouTube Music." if requete else "Abrindo YouTube Music."
    return msg


def youtube_lancer(requete: str = None) -> str:
    if requete:
        url = f"https://www.youtube.com/results?search_query={requests.utils.quote(requete)}"
    else:
        url = "https://www.youtube.com"
    webbrowser.open(url)
    msg = f"Procurando {requete} no YouTube." if requete else "Abrindo YouTube."
    return msg


# ═══════════════════════════════════════════════════════════════
#  RADIO EN LIGNE (via VLC)
# ═══════════════════════════════════════════════════════════════

_radio_process = None

def radio_lancer(nom: str) -> str:
    global _radio_process
    url = RADIOS.get(nom.lower())
    if not url:
        # Recherche partielle
        for nom_radio, url_radio in RADIOS.items():
            if nom.lower() in nom_radio:
                url = url_radio
                nom = nom_radio
                break

    if not url:
        return f"Radio '{nom}' introuvable. Radios disponibles : {', '.join(RADIOS.keys())}."

    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]
    vlc = next((p for p in vlc_paths if os.path.exists(p)), None)

    radio_arreter()
    try:
        if vlc:
            _radio_process = subprocess.Popen([vlc, "--intf", "dummy", url])
        else:
            webbrowser.open(url)
        return f"Radio {nom} en cours de lecture."
    except Exception as e:
        return f"Erreur radio : {e}"


def radio_arreter() -> str:
    global _radio_process
    if _radio_process:
        try:
            _radio_process.terminate()
            _radio_process = None
            return "Radio arrêtée."
        except Exception:
            pass
    return "Aucune radio en cours."


def radio_disponibles() -> list[str]:
    return list(RADIOS.keys())


# ═══════════════════════════════════════════════════════════════
#  INTERFACE UNIFIÉE
# ═══════════════════════════════════════════════════════════════

def lancer_musique(requete: str = None, service: str = None) -> str:
    """
    Lance la musique sur le service approprié.
    - Si requete est None : lance la playlist principale.
    - service : "spotify" | "deezer" | "youtube" | "radio" | None (auto)
    """
    global _service_actif
    svc = (service or _service_actif).lower()

    if svc == "auto":
        if spotify_disponible():
            svc = "spotify"
        else:
            svc = "youtube"

    if svc == "spotify":
        if requete:
            return spotify_chercher(requete)
        return spotify_lancer_playlist()

    if svc == "deezer":
        if requete:
            return deezer_chercher(requete)
        return deezer_lancer()

    if svc == "youtube":
        return youtube_music_lancer(requete)

    if svc == "radio":
        return radio_lancer(requete or "lofi hip hop")

    return "Service musical non reconnu."


def definir_service(service: str) -> str:
    global _service_actif
    services_valides = {"spotify", "deezer", "youtube", "radio", "auto"}
    s = service.lower()
    if s in services_valides:
        _service_actif = s
        return f"Service musical défini sur {s}."
    return f"Service '{service}' non reconnu. Options : {', '.join(services_valides)}."
