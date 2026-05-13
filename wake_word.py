# ============================================================
#  wake_word.py — Détection du mot de réveil
#  R.O.N.Y — Écoute passive jusqu'à entendre "Rony"
#  Supporte toutes les langues configurées
# ============================================================

import re

# ── Mots de réveil acceptés (toutes langues) ─────────────────
WAKE_WORDS: set[str] = {
    # Universel
    "rony", "hey rony", "ok rony", "oi rony",

    # FR
    "hé rony", "eh rony", "bonjour rony", "salut rony",
    "dis rony", "roni",

    # PT
    "olá rony", "ola rony", "ei rony",

    # EN
    "hello rony", "hi rony", "yo rony",

    # ES
    "hola rony", "oye rony",

    # DE
    "hallo rony", "hey roni",

    # IT
    "ciao rony", "ehi rony",

    # RU
    "рони", "рони привет",

    # JA
    "ロニー",

    # ZH
    "罗尼",
}

# Mots d'arrêt (retour au mode veille)
MOTS_ARRET: set[str] = {
    "au revoir rony", "dors rony", "stop rony", "merci rony",
    "tchau rony", "bye rony", "adios rony", "ciao rony",
    "hasta luego rony", "tschüss rony",
}

# Mots d'arrêt session (sans "rony")
MOTS_ARRET_SIMPLES: set[str] = {
    "au revoir", "dors", "bonne nuit", "à plus",
    "tchau", "bye", "hasta luego", "tschüss", "ciao",
    "goodnight", "good night", "goodbye",
}


def contient_wake_word(texte: str) -> bool:
    """Retourne True si le texte contient un mot de réveil."""
    t = texte.lower().strip()
    # Vérification exacte
    if t in WAKE_WORDS:
        return True
    # Vérification partielle (le mot est contenu dans la phrase)
    for ww in WAKE_WORDS:
        if ww in t:
            return True
    return False


def contient_mot_arret(texte: str) -> bool:
    """Retourne True si le texte demande à Rony de se rendormir."""
    t = texte.lower().strip()
    for mot in MOTS_ARRET:
        if mot in t:
            return True
    # Mots simples seulement si la phrase est courte (< 4 mots)
    if len(t.split()) <= 3:
        for mot in MOTS_ARRET_SIMPLES:
            if mot in t:
                return True
    return False


def nettoyer_commande(texte: str) -> str:
    """
    Retire le wake word du début de la commande.
    Ex: "hey Rony quelle heure est-il" → "quelle heure est-il"
    """
    t = texte.strip()
    # Retire les wake words du début
    for ww in sorted(WAKE_WORDS, key=len, reverse=True):
        pattern = re.compile(r"^" + re.escape(ww) + r"[\s,\.!?]*", re.IGNORECASE)
        t = pattern.sub("", t).strip()
    return t if t else texte.strip()
