# ============================================================
#  google_services.py — Intégration Google Workspace
#  R.O.N.Y — Gmail · Drive · Docs · Sheets · Calendar
#  Amélioration JARVIS : gestion d'erreurs unifiée + lazy init
# ============================================================

import os
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Chemins OAuth ─────────────────────────────────────────────
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE       = Path(__file__).parent / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

_service_gmail    = None
_service_drive    = None
_service_docs     = None
_service_sheets   = None
_service_calendar = None


# ═══════════════════════════════════════════════════════════════
#  AUTHENTIFICATION OAUTH2
# ═══════════════════════════════════════════════════════════════

def _get_credentials():
    """Retourne les credentials OAuth2. Lance le flux si nécessaire."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif CREDENTIALS_FILE.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
                TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            else:
                print("[GOOGLE] Fichier credentials.json manquant.")
                return None

        return creds
    except ImportError:
        print("[GOOGLE] Bibliothèques Google non installées.")
        return None
    except Exception as e:
        print(f"[GOOGLE] Erreur authentification : {e}")
        return None


def _build_service(name: str, version: str):
    """Construit un service Google API."""
    try:
        from googleapiclient.discovery import build
        creds = _get_credentials()
        if not creds:
            return None
        return build(name, version, credentials=creds)
    except Exception as e:
        print(f"[GOOGLE] Erreur construction service {name} : {e}")
        return None


def init_google_services() -> dict[str, bool]:
    """Initialise tous les services Google. Retourne un dict de statuts."""
    global _service_gmail, _service_drive, _service_docs, _service_sheets, _service_calendar
    statuts = {}
    try:
        _service_gmail    = _build_service("gmail", "v1")
        _service_drive    = _build_service("drive", "v3")
        _service_docs     = _build_service("docs", "v1")
        _service_sheets   = _build_service("sheets", "v4")
        _service_calendar = _build_service("calendar", "v3")

        statuts = {
            "gmail"   : _service_gmail    is not None,
            "drive"   : _service_drive    is not None,
            "docs"    : _service_docs     is not None,
            "sheets"  : _service_sheets   is not None,
            "calendar": _service_calendar is not None,
        }
    except Exception as e:
        print(f"[GOOGLE] Erreur init : {e}")
    return statuts


# ═══════════════════════════════════════════════════════════════
#  GMAIL
# ═══════════════════════════════════════════════════════════════

def gmail_lire_emails(max_messages: int = 5, non_lus_seulement: bool = True) -> list[dict]:
    """Retourne les derniers emails (expéditeur + sujet + extrait)."""
    svc = _service_gmail or _build_service("gmail", "v1")
    if not svc:
        return []
    try:
        query  = "is:unread" if non_lus_seulement else ""
        result = svc.users().messages().list(userId="me", maxResults=max_messages, q=query).execute()
        msgs   = result.get("messages", [])
        emails = []
        for m in msgs:
            msg    = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                                metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            snippet  = msg.get("snippet", "")
            emails.append({
                "de"    : headers.get("From", "?"),
                "sujet" : headers.get("Subject", "(sans sujet)"),
                "date"  : headers.get("Date", "?"),
                "extrait": snippet[:150],
            })
        return emails
    except Exception as e:
        print(f"[GMAIL] Erreur lecture : {e}")
        return []


def gmail_resumer(langue: str = "fr") -> str:
    """Résumé vocal des emails non lus."""
    emails = gmail_lire_emails(max_messages=5)
    if not emails:
        messages = {
            "fr": "Aucun nouveau message.",
            "en": "No new messages.",
            "pt": "Nenhuma mensagem nova.",
            "es": "No hay mensajes nuevos.",
            "de": "Keine neuen Nachrichten.",
        }
        return messages.get(langue, messages["en"])

    prefixes = {
        "fr": f"Vous avez {len(emails)} message(s) non lu(s).",
        "en": f"You have {len(emails)} unread message(s).",
        "pt": f"Você tem {len(emails)} mensagem(s) não lida(s).",
        "es": f"Tiene {len(emails)} mensaje(s) sin leer.",
        "de": f"Sie haben {len(emails)} ungelesene Nachricht(en).",
    }
    resume = prefixes.get(langue, prefixes["en"])

    for i, e in enumerate(emails[:3], 1):
        de_court = e["de"].split("<")[0].strip()
        resume += f" {i}. De {de_court} : {e['sujet']}."

    return resume


# ═══════════════════════════════════════════════════════════════
#  GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════

def drive_rechercher(requete: str, max_fichiers: int = 5) -> list[dict]:
    """Recherche des fichiers dans Google Drive."""
    svc = _service_drive or _build_service("drive", "v3")
    if not svc:
        return []
    try:
        result = svc.files().list(
            q=f"name contains '{requete}'",
            pageSize=max_fichiers,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        ).execute()
        return result.get("files", [])
    except Exception as e:
        print(f"[DRIVE] Erreur recherche : {e}")
        return []


def drive_fichiers_recents(max_fichiers: int = 5) -> list[dict]:
    """Retourne les fichiers Drive récemment modifiés."""
    svc = _service_drive or _build_service("drive", "v3")
    if not svc:
        return []
    try:
        result = svc.files().list(
            orderBy="modifiedTime desc",
            pageSize=max_fichiers,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        ).execute()
        return result.get("files", [])
    except Exception as e:
        print(f"[DRIVE] Erreur fichiers récents : {e}")
        return []


# ═══════════════════════════════════════════════════════════════
#  GOOGLE CALENDAR
# ═══════════════════════════════════════════════════════════════

def calendar_evenements_jour(date: datetime = None, max_events: int = 5) -> list[dict]:
    """Retourne les événements du jour (ou d'une date donnée)."""
    svc = _service_calendar or _build_service("calendar", "v3")
    if not svc:
        return []
    try:
        jour   = date or datetime.now()
        debut  = jour.replace(hour=0,  minute=0,  second=0, microsecond=0).isoformat() + "Z"
        fin    = jour.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + "Z"
        result = svc.events().list(
            calendarId="primary", timeMin=debut, timeMax=fin,
            maxResults=max_events, singleEvents=True, orderBy="startTime",
        ).execute()
        events = []
        for e in result.get("items", []):
            start = e["start"].get("dateTime", e["start"].get("date", "?"))
            events.append({
                "titre"     : e.get("summary", "(sans titre)"),
                "debut"     : start,
                "description": e.get("description", ""),
                "lieu"      : e.get("location", ""),
            })
        return events
    except Exception as e:
        print(f"[CALENDAR] Erreur : {e}")
        return []


def calendar_resumer(langue: str = "fr") -> str:
    """Résumé vocal du calendrier du jour."""
    events = calendar_evenements_jour()
    if not events:
        messages = {
            "fr": "Aucun événement aujourd'hui.",
            "en": "No events today.",
            "pt": "Nenhum evento hoje.",
            "es": "No hay eventos hoy.",
            "de": "Keine Ereignisse heute.",
        }
        return messages.get(langue, messages["en"])

    prefixes = {
        "fr": f"Vous avez {len(events)} événement(s) aujourd'hui.",
        "en": f"You have {len(events)} event(s) today.",
        "pt": f"Você tem {len(events)} evento(s) hoje.",
        "es": f"Tiene {len(events)} evento(s) hoy.",
        "de": f"Sie haben heute {len(events)} Termin(e).",
    }
    resume = prefixes.get(langue, prefixes["en"])

    for e in events[:3]:
        try:
            heure = e["debut"][11:16] if "T" in e["debut"] else e["debut"]
        except Exception:
            heure = "?"
        resume += f" À {heure} : {e['titre']}."

    return resume
