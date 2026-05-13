# ============================================================
#  vision_module.py — Capture d'écran & interaction visuelle
#  R.O.N.Y — Gemini Vision + PyAutoGUI
#  Amélioration JARVIS : analyse locale + multilingue
# ============================================================

import os
import io
import time
import base64
import asyncio
from pathlib import Path
from typing import Optional
from PIL import Image

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False


# ── Dossier de captures ───────────────────────────────────────
from rony_paths import CAPTURES_DIR
# Pasta já criada pelo rony_paths na importação


# ═══════════════════════════════════════════════════════════════
#  CAPTURE D'ÉCRAN
# ═══════════════════════════════════════════════════════════════

def capturer_ecran(region: tuple = None, sauvegarder: bool = False) -> Optional[bytes]:
    """
    Capture l'écran (ou une région) et retourne les bytes JPEG.
    region: (x, y, largeur, hauteur) ou None pour tout l'écran.
    """
    if not PYAUTOGUI_OK:
        print("[VISION] PyAutoGUI non disponible.")
        return None
    try:
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()

        if sauvegarder:
            ts   = int(time.time())
            path = CAPTURES_DIR / f"capture_{ts}.jpg"
            screenshot.save(str(path), "JPEG", quality=85)
            print(f"[VISION] Capture sauvegardée : {path}")

        buf = io.BytesIO()
        screenshot.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception as e:
        print(f"[VISION] Erreur capture : {e}")
        return None


def capturer_vers_base64(region: tuple = None) -> Optional[str]:
    """Capture l'écran et retourne l'image en base64."""
    img_bytes = capturer_ecran(region)
    if img_bytes:
        return base64.b64encode(img_bytes).decode("utf-8")
    return None


def capturer_et_sauvegarder() -> Optional[Path]:
    """Capture et sauvegarde l'écran, retourne le chemin."""
    if not PYAUTOGUI_OK:
        return None
    try:
        ts   = int(time.time())
        path = CAPTURES_DIR / f"capture_{ts}.jpg"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(path), "JPEG", quality=85)
        return path
    except Exception as e:
        print(f"[VISION] Erreur sauvegarde : {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  ANALYSE VIA IA (Gemini Vision)
# ═══════════════════════════════════════════════════════════════

async def analyser_ecran_ia(client_gemini, prompt: str = None, langue: str = "fr") -> str:
    """
    Capture l'écran et envoie à Gemini pour analyse.
    client_gemini : instance google.genai.Client
    """
    img_bytes = capturer_ecran()
    if not img_bytes:
        msgs = {"fr": "Impossible de capturer l'écran.", "en": "Unable to capture screen.", "pt": "Não foi possível capturar a tela."}
        return msgs.get(langue, msgs["en"])

    prompts_defaut = {
        "fr": "Décris ce que tu vois à l'écran en détail. Identifie les éléments importants, le texte visible et les actions possibles.",
        "en": "Describe what you see on the screen in detail. Identify important elements, visible text and possible actions.",
        "pt": "Descreva o que você vê na tela em detalhes. Identifique os elementos importantes, texto visível e ações possíveis.",
        "es": "Describe lo que ves en la pantalla con detalle. Identifica elementos importantes, texto visible y acciones posibles.",
        "de": "Beschreibe was du auf dem Bildschirm siehst. Identifiziere wichtige Elemente, sichtbaren Text und mögliche Aktionen.",
    }
    prompt_final = prompt or prompts_defaut.get(langue, prompts_defaut["en"])

    try:
        import google.genai as genai
        from google.genai import types

        response = await asyncio.get_event_loop().run_in_executor(None, lambda: client_gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                prompt_final,
            ],
        ))
        return response.text or ""
    except Exception as e:
        print(f"[VISION IA] Erreur : {e}")
        errors = {"fr": f"Erreur d'analyse : {e}", "en": f"Analysis error: {e}", "pt": f"Erro de análise: {e}"}
        return errors.get(langue, errors["en"])


# ═══════════════════════════════════════════════════════════════
#  INTERACTION SOURIS / CLAVIER
# ═══════════════════════════════════════════════════════════════

def cliquer_coordonnees(x: int, y: int, double: bool = False) -> bool:
    """Clique aux coordonnées données."""
    if not PYAUTOGUI_OK:
        return False
    try:
        if double:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.click(x, y)
        return True
    except Exception as e:
        print(f"[VISION] Erreur clic ({x},{y}) : {e}")
        return False


def taper_texte(texte: str, intervalle: float = 0.05) -> bool:
    """Tape du texte avec PyAutoGUI."""
    if not PYAUTOGUI_OK:
        return False
    try:
        pyautogui.typewrite(texte, interval=intervalle)
        return True
    except Exception as e:
        try:
            import pyperclip
            pyperclip.copy(texte)
            pyautogui.hotkey("ctrl", "v")
            return True
        except Exception:
            print(f"[VISION] Erreur saisie : {e}")
            return False


def appuyer_touche(touche: str) -> bool:
    """Appuie sur une touche (ex: 'enter', 'escape', 'f5')."""
    if not PYAUTOGUI_OK:
        return False
    try:
        pyautogui.press(touche)
        return True
    except Exception as e:
        print(f"[VISION] Erreur touche '{touche}' : {e}")
        return False


def raccourci(touches: list[str]) -> bool:
    """Exécute un raccourci clavier (ex: ['ctrl', 'c'])."""
    if not PYAUTOGUI_OK:
        return False
    try:
        pyautogui.hotkey(*touches)
        return True
    except Exception as e:
        print(f"[VISION] Erreur raccourci {touches} : {e}")
        return False


def scroll(direction: str = "down", clics: int = 3) -> bool:
    """Fait défiler la page."""
    if not PYAUTOGUI_OK:
        return False
    try:
        montant = -clics if direction == "down" else clics
        pyautogui.scroll(montant)
        return True
    except Exception as e:
        print(f"[VISION] Erreur scroll : {e}")
        return False


def get_position_souris() -> tuple[int, int]:
    """Retourne la position actuelle de la souris."""
    if not PYAUTOGUI_OK:
        return (0, 0)
    pos = pyautogui.position()
    return (pos.x, pos.y)


def get_resolution_ecran() -> tuple[int, int]:
    """Retourne la résolution de l'écran principal."""
    if not PYAUTOGUI_OK:
        return (1920, 1080)
    return pyautogui.size()


# ═══════════════════════════════════════════════════════════════
#  ANALYSE D'IMAGE LOCALE (sans IA)
# ═══════════════════════════════════════════════════════════════

def info_image(chemin: Path) -> dict:
    """Retourne les informations d'une image locale."""
    try:
        img = Image.open(chemin)
        return {
            "format"    : img.format,
            "mode"      : img.mode,
            "dimensions": img.size,
            "taille"    : chemin.stat().st_size,
        }
    except Exception as e:
        return {"erreur": str(e)}


def lister_captures() -> list[Path]:
    """Liste les captures d'écran sauvegardées."""
    return sorted(CAPTURES_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)


def supprimer_vieilles_captures(max_captures: int = 50) -> int:
    """Garde seulement les max_captures captures les plus récentes."""
    captures = lister_captures()
    a_supprimer = captures[max_captures:]
    for c in a_supprimer:
        try:
            c.unlink()
        except Exception:
            pass
    return len(a_supprimer)
