# ============================================================
#  memory_manager.py — Mémoire persistante de Rony
#  Stockage JSON : faits + historique de conversation
#  Amélioration JARVIS : tagging par langue, recherche sémantique
#  et expiration automatique des entrées anciennes.
# ============================================================

import json
import os
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rony_paths import MEMOIRE_FILE, HISTORIQUE_FILE

MAX_HISTORIQUE_RAM  = 30    # échanges chargés en mémoire active
MAX_HISTORIQUE_DISK = 300   # échanges max conservés sur disque
MAX_FAITS           = 500   # faits mémorisés max
EXPIRATION_JOURS    = 180   # faits non utilisés supprimés après 6 mois

# ── Structure interne ─────────────────────────────────────────
_memoire: dict = {}       # {clé: {valeur, langue, timestamp, acces}}
_historique: list = []    # [{role, text, langue, ts}]


# ═══════════════════════════════════════════════════════════════
#  INITIALISATION
# ═══════════════════════════════════════════════════════════════

def _charger_memoire() -> None:
    global _memoire
    if MEMOIRE_FILE.exists():
        try:
            with open(MEMOIRE_FILE, encoding="utf-8") as f:
                _memoire = json.load(f)
        except Exception:
            _memoire = {}


def _sauvegarder_memoire() -> None:
    try:
        with open(MEMOIRE_FILE, "w", encoding="utf-8") as f:
            json.dump(_memoire, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[MÉMOIRE] Erreur sauvegarde : {e}")


def _charger_historique_recent() -> list:
    if not HISTORIQUE_FILE.exists():
        return []
    try:
        with open(HISTORIQUE_FILE, encoding="utf-8") as f:
            tous = json.load(f)
        return tous[-MAX_HISTORIQUE_RAM:]
    except Exception:
        return []


def _sauvegarder_echange_conv(role: str, texte: str, langue: str = "fr") -> None:
    tous = []
    if HISTORIQUE_FILE.exists():
        try:
            with open(HISTORIQUE_FILE, encoding="utf-8") as f:
                tous = json.load(f)
        except Exception:
            tous = []

    tous.append({
        "role"   : role,
        "text"   : texte,
        "langue" : langue,
        "ts"     : datetime.now().isoformat(),
    })

    if len(tous) > MAX_HISTORIQUE_DISK:
        tous = tous[-MAX_HISTORIQUE_DISK:]

    try:
        with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
            json.dump(tous, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[HISTORIQUE] Erreur sauvegarde : {e}")


def init_memoire() -> None:
    """Initialise la mémoire au démarrage de Rony."""
    global _historique
    _charger_memoire()
    _historique = _charger_historique_recent()
    _purger_faits_expires()
    print(f"[MÉMOIRE] {len(_memoire)} faits | {len(_historique)} échanges récents chargés.")


# ═══════════════════════════════════════════════════════════════
#  FAITS — LIRE / ÉCRIRE / OUBLIER
# ═══════════════════════════════════════════════════════════════

def memoriser(cle: str, valeur: str, langue: str = "fr") -> None:
    """Enregistre un fait en mémoire."""
    _memoire[cle.lower().strip()] = {
        "valeur"    : valeur,
        "langue"    : langue,
        "timestamp" : time.time(),
        "acces"     : 0,
    }
    if len(_memoire) > MAX_FAITS:
        _purger_faits_anciens()
    _sauvegarder_memoire()


def rappeler(cle: str) -> Optional[str]:
    """Récupère un fait mémorisé. Retourne None si absent."""
    entree = _memoire.get(cle.lower().strip())
    if entree:
        entree["acces"] += 1
        return entree["valeur"]
    return None


def oublier(cle: str) -> bool:
    """Supprime un fait. Retourne True si trouvé et supprimé."""
    cle = cle.lower().strip()
    if cle in _memoire:
        del _memoire[cle]
        _sauvegarder_memoire()
        return True
    return False


def rechercher_faits(requete: str) -> list[tuple[str, str]]:
    """Cherche des faits dont la clé ou la valeur contient la requête."""
    requete = requete.lower()
    resultats = []
    for cle, entree in _memoire.items():
        if requete in cle or requete in entree["valeur"].lower():
            resultats.append((cle, entree["valeur"]))
    return resultats[:10]


def lister_faits(limite: int = 20) -> list[tuple[str, str]]:
    """Liste les derniers faits mémorisés, par ordre d'insertion."""
    items = sorted(_memoire.items(), key=lambda x: x[1].get("timestamp", 0), reverse=True)
    return [(k, v["valeur"]) for k, v in items[:limite]]


def compter_faits() -> int:
    return len(_memoire)


# ═══════════════════════════════════════════════════════════════
#  HISTORIQUE DE CONVERSATION
# ═══════════════════════════════════════════════════════════════

def ajouter_historique(role: str, texte: str, langue: str = "fr") -> None:
    """Ajoute un échange à l'historique en mémoire et sur disque."""
    global _historique
    entree = {"role": role, "text": texte, "langue": langue, "ts": datetime.now().isoformat()}
    _historique.append(entree)
    if len(_historique) > MAX_HISTORIQUE_RAM:
        _historique = _historique[-MAX_HISTORIQUE_RAM:]
    _sauvegarder_echange_conv(role, texte, langue)


def get_historique_recent(n: int = 10) -> list:
    """Retourne les n derniers échanges pour contexte IA."""
    return _historique[-n:]


def get_historique_pour_ia() -> list[dict]:
    """Formate l'historique pour l'injection dans le contexte IA."""
    messages = []
    for entree in _historique[-MAX_HISTORIQUE_RAM:]:
        role = "user" if entree["role"] == "user" else "model"
        messages.append({"role": role, "text": entree["text"]})
    return messages


def vider_historique_session() -> None:
    """Efface l'historique en RAM (pas le fichier disque)."""
    global _historique
    _historique = []


def effacer_tout_historique() -> None:
    """Efface l'historique en RAM et sur disque."""
    global _historique
    _historique = []
    if HISTORIQUE_FILE.exists():
        HISTORIQUE_FILE.write_text("[]", encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
#  PURGE AUTOMATIQUE
# ═══════════════════════════════════════════════════════════════

def _purger_faits_expires() -> None:
    """Supprime les faits non accédés depuis EXPIRATION_JOURS."""
    limite = time.time() - EXPIRATION_JOURS * 86400
    a_supprimer = [
        cle for cle, e in _memoire.items()
        if e.get("timestamp", 0) < limite and e.get("acces", 0) == 0
    ]
    for cle in a_supprimer:
        del _memoire[cle]
    if a_supprimer:
        print(f"[MÉMOIRE] {len(a_supprimer)} fait(s) expirés supprimés.")
        _sauvegarder_memoire()


def _purger_faits_anciens() -> None:
    """Garde seulement les MAX_FAITS entrées les plus récentes."""
    items = sorted(_memoire.items(), key=lambda x: x[1].get("timestamp", 0))
    a_supprimer = items[:len(_memoire) - MAX_FAITS]
    for cle, _ in a_supprimer:
        del _memoire[cle]
    _sauvegarder_memoire()


# ═══════════════════════════════════════════════════════════════
#  EXTRACTION AUTOMATIQUE DE FAITS DEPUIS LE TEXTE
# ═══════════════════════════════════════════════════════════════

_PATTERNS_MEMORISATION = [
    # FR
    (r"(?:souviens-toi|retiens|mémorise|note) (?:que )?(.+)", "fr"),
    (r"mon (\w+) (?:est|s'appelle|se nomme) (.+)",            "fr"),
    (r"j'(?:aime|adore|préfère) (.+)",                         "fr"),
    # PT
    (r"(?:lembra|guarda|anota) (?:que )?(.+)",                 "pt"),
    (r"meu (\w+) (?:é|se chama) (.+)",                         "pt"),
    # EN
    (r"(?:remember|note|save) (?:that )?(.+)",                 "en"),
    (r"my (\w+) (?:is|is called|is named) (.+)",               "en"),
    # ES
    (r"(?:recuerda|anota|guarda) (?:que )?(.+)",               "es"),
    # DE
    (r"(?:merke|speichere|notiere) (?:dass )?(.+)",            "de"),
]

def extraire_et_memoriser(texte: str, langue: str = "fr") -> Optional[str]:
    """
    Tente d'extraire un fait mémorisable du texte utilisateur.
    Retourne la clé mémorisée ou None.
    """
    for pattern, lang in _PATTERNS_MEMORISATION:
        m = re.search(pattern, texte, re.IGNORECASE)
        if m:
            groupes = m.groups()
            if len(groupes) == 1:
                cle = f"note_{int(time.time())}"
                valeur = groupes[0].strip()
            else:
                cle = groupes[0].strip()
                valeur = groupes[1].strip()
            memoriser(cle, valeur, langue)
            return cle
    return None


# Initialisation automatique au import
init_memoire()
