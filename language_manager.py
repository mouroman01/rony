# ============================================================
#  language_manager.py — Gestão Multilíngue
#  R.O.N.Y — Responsive Omni-lingual Neural sYstem
#  Detecção automática + troca dinâmica entre idiomas
#  Suporte: FR · PT-BR · EN · ES · DE · IT · NL · PL · JA · ZH · AR · RU
# ============================================================

import re
from typing import Optional

# ── Idioma activo (padrão: português Brasil) ──────────────────
_langue_active = "pt"

# ── Vozes TTS por idioma (edge-tts — vozes mais expressivas/naturais) ────
# Selecionadas por naturalidade e expressividade de cada idioma
VOIX = {
    "fr": "fr-FR-DeniseNeural",           # Mais expressiva e natural (feminina)
    "pt": "pt-BR-ThalitaMultilingualNeural",  # Mais humana do PT-BR (2024)
    "en": "en-US-JennyNeural",            # Conversacional, calorosa
    "es": "es-ES-ElviraNeural",           # Mais natural para ES
    "de": "de-DE-KatjaNeural",            # Natural, expressiva
    "it": "it-IT-ElsaNeural",             # Mais fluida para IT
    "nl": "nl-NL-ColetteNeural",          # Natural para NL
    "pl": "pl-PL-ZofiaNeural",            # Melhor para PL
    "ru": "ru-RU-SvetlanaNeural",         # Mais expressiva para RU
    "ja": "ja-JP-NanamiNeural",           # Natural para JA
    "zh": "zh-CN-XiaoxiaoNeural",         # Líder em naturalidade para ZH
    "ar": "ar-SA-ZariyahNeural",          # Melhor para AR
    "tr": "tr-TR-EmelNeural",             # Natural para TR
    "ko": "ko-KR-SunHiNeural",            # Mais expressiva para KO
    "sv": "sv-SE-SofieNeural",            # Natural para SV
}

# ── Prosody por idioma (ritmo e pitch para soar mais humano) ─────────────
VOIX_PROSODY = {
    "pt": {"rate": "-8%",  "pitch": "+2Hz"},   # Um pouco mais devagar, tom caloroso
    "fr": {"rate": "-5%",  "pitch": "+0Hz"},
    "en": {"rate": "-5%",  "pitch": "+1Hz"},
    "es": {"rate": "-5%",  "pitch": "+1Hz"},
    "de": {"rate": "-8%",  "pitch": "-1Hz"},
    "it": {"rate": "-5%",  "pitch": "+2Hz"},
    "ja": {"rate": "-10%", "pitch": "+0Hz"},
    "zh": {"rate": "-8%",  "pitch": "+0Hz"},
    "ru": {"rate": "-8%",  "pitch": "-1Hz"},
    "ko": {"rate": "-8%",  "pitch": "+1Hz"},
}

# ── Noms des langues ─────────────────────────────────────────
NOMS_LANGUES = {
    "fr": "Français",
    "pt": "Português (Brasil)",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "it": "Italiano",
    "nl": "Nederlands",
    "pl": "Polski",
    "ru": "Русский",
    "ja": "日本語",
    "zh": "中文",
    "ar": "العربية",
    "tr": "Türkçe",
    "ko": "한국어",
    "sv": "Svenska",
}

# ── Mots-clés de détection par langue ────────────────────────
MOTS_CLE = {
    "fr": {
        "bonjour", "bonsoir", "merci", "ouvre", "ferme", "allume", "éteins",
        "joue", "arrête", "pause", "volume", "météo", "quelle", "quel", "quoi",
        "comment", "pourquoi", "où", "qui", "quand", "montre", "affiche",
        "lance", "cherche", "rappelle", "mets", "envoie", "appelle", "réponds",
        "lumière", "musique", "recherche", "fais", "aide", "salut", "oui", "non",
        "s'il", "plaît", "est-ce", "peux", "pourrais", "veux", "voudrais",
        "heure", "fichier", "dossier", "écran", "demain", "aujourd",
    },
    "pt": {
        "olá", "ola", "bom", "dia", "tarde", "noite", "obrigado", "obrigada",
        "abre", "fecha", "liga", "desliga", "toca", "para", "pausa",
        "qual", "quais", "como", "porque", "onde", "quando", "mostra",
        "inicia", "procura", "lembra", "coloca", "envia", "chama",
        "sim", "não", "nao", "por", "favor", "posso", "poderia", "quero",
        "gostaria", "hora", "arquivo", "pasta", "tela", "pesquisa",
        "acende", "apaga", "aumenta", "diminui", "silencia", "música",
    },
    "en": {
        "hello", "hi", "hey", "good", "morning", "evening", "night",
        "thanks", "thank", "open", "close", "turn", "play", "stop",
        "pause", "volume", "weather", "what", "which", "how", "why",
        "where", "who", "when", "show", "search", "find", "remind",
        "set", "send", "call", "reply", "light", "music", "help",
        "yes", "no", "please", "can", "could", "want", "would",
        "time", "file", "folder", "screen", "tomorrow", "today",
    },
    "es": {
        "hola", "buenos", "días", "tardes", "noches", "gracias",
        "abre", "cierra", "enciende", "apaga", "reproduce", "para",
        "pausa", "volumen", "clima", "qué", "cuál", "cómo", "por",
        "dónde", "quién", "cuándo", "muestra", "busca", "recuerda",
        "pon", "envía", "llama", "contesta", "luz", "música",
        "sí", "no", "favor", "puedo", "podría", "quiero", "quisiera",
        "hora", "archivo", "carpeta", "pantalla", "mañana", "hoy",
    },
    "de": {
        "hallo", "guten", "morgen", "abend", "nacht", "danke",
        "öffne", "schließe", "einschalten", "ausschalten", "spiele",
        "stoppe", "pause", "lautstärke", "wetter", "was", "wie",
        "warum", "wo", "wer", "wann", "zeige", "suche", "erinnere",
        "setze", "sende", "ruf", "antworte", "licht", "musik",
        "ja", "nein", "bitte", "kann", "könnte", "möchte", "hätte",
        "uhr", "datei", "ordner", "bildschirm", "morgen", "heute",
    },
    "it": {
        "ciao", "salve", "buon", "giorno", "sera", "notte", "grazie",
        "apri", "chiudi", "accendi", "spegni", "riproduci", "ferma",
        "pausa", "volume", "meteo", "cosa", "quale", "come", "perché",
        "dove", "chi", "quando", "mostra", "cerca", "ricorda",
        "metti", "invia", "chiama", "rispondi", "luce", "musica",
        "sì", "no", "prego", "posso", "potrei", "voglio", "vorrei",
        "ora", "file", "cartella", "schermo", "domani", "oggi",
    },
    "ru": {
        "привет", "здравствуй", "доброе", "утро", "вечер", "ночь",
        "спасибо", "открой", "закрой", "включи", "выключи", "играй",
        "стоп", "пауза", "громкость", "погода", "что", "как",
        "почему", "где", "кто", "когда", "покажи", "найди",
        "напомни", "поставь", "отправь", "позвони", "свет", "музыка",
        "да", "нет", "пожалуйста", "могу", "мог", "хочу", "хотел",
    },
    "ja": {
        "こんにちは", "おはよう", "こんばんは", "ありがとう",
        "開けて", "閉めて", "つけて", "消して", "再生", "止めて",
        "音量", "天気", "何", "どう", "なぜ", "どこ", "誰", "いつ",
        "見せて", "探して", "設定", "送って", "電話", "音楽",
        "はい", "いいえ", "お願い",
    },
    "zh": {
        "你好", "早上好", "晚上好", "谢谢", "打开", "关闭",
        "打开", "关掉", "播放", "停止", "暂停", "音量", "天气",
        "什么", "怎么", "为什么", "在哪", "谁", "什么时候",
        "显示", "搜索", "提醒", "发送", "打电话", "音乐",
        "是", "不", "请",
    },
    "ar": {
        "مرحبا", "صباح", "مساء", "شكرا", "افتح", "أغلق",
        "شغل", "أوقف", "صوت", "طقس", "ماذا", "كيف",
        "لماذا", "أين", "من", "متى", "اعرض", "ابحث", "ذكرني",
        "أرسل", "اتصل", "موسيقى", "نعم", "لا", "من فضلك",
    },
    "nl": {
        "hallo", "goedemorgen", "goedenavond", "dankjewel",
        "open", "sluit", "zet", "speel", "stop", "pauze", "volume",
        "weer", "wat", "hoe", "waarom", "waar", "wie", "wanneer",
        "toon", "zoek", "herinner", "stuur", "bel", "licht", "muziek",
        "ja", "nee", "alsjeblieft",
    },
    "pl": {
        "cześć", "dzień", "dobry", "wieczór", "dziękuję",
        "otwórz", "zamknij", "włącz", "wyłącz", "graj",
        "zatrzymaj", "pauza", "głośność", "pogoda", "co", "jak",
        "dlaczego", "gdzie", "kto", "kiedy", "pokaż", "szukaj",
        "przypomnij", "wyślij", "zadzwoń", "muzyka",
        "tak", "nie", "proszę",
    },
    "tr": {
        "merhaba", "günaydın", "iyi", "akşam", "teşekkür",
        "aç", "kapat", "çalıştır", "durdur", "duraklat", "ses",
        "hava", "ne", "nasıl", "neden", "nerede", "kim", "ne zaman",
        "göster", "ara", "hatırlat", "gönder", "ara", "müzik",
        "evet", "hayır", "lütfen",
    },
    "ko": {
        "안녕", "안녕하세요", "감사합니다", "열어", "닫아",
        "켜", "꺼", "재생", "정지", "일시정지", "볼륨", "날씨",
        "뭐", "어떻게", "왜", "어디", "누구", "언제",
        "보여줘", "찾아", "알려줘", "보내", "전화", "음악",
        "네", "아니", "제발",
    },
    "sv": {
        "hej", "godmorgon", "godkväll", "tack", "öppna",
        "stäng", "slå", "spela", "stopp", "paus", "volym", "väder",
        "vad", "hur", "varför", "var", "vem", "när",
        "visa", "sök", "påminn", "skicka", "ring", "musik",
        "ja", "nej", "tack",
    },
}

# ── Commandes de changement de langue ────────────────────────
COMMANDES_LANGUE = {
    "fr": [
        "parle français", "passe en français", "langue française",
        "réponds en français", "en français",
    ],
    "pt": [
        "fala português", "muda para português", "responde em português",
        "em português", "parle portugais", "passe en portugais",
    ],
    "en": [
        "speak english", "switch to english", "in english",
        "talk to me in english", "parle anglais", "passe en anglais",
    ],
    "es": [
        "habla español", "en español", "cambia a español",
        "parle espagnol", "passe en espagnol",
    ],
    "de": [
        "sprich deutsch", "auf deutsch", "wechsle zu deutsch",
        "parle allemand", "passe en allemand",
    ],
    "it": [
        "parla italiano", "in italiano", "cambia in italiano",
        "parle italien", "passe en italien",
    ],
    "ru": [
        "говори по-русски", "на русском", "parle russe", "passe en russe",
    ],
    "ja": [
        "日本語で話して", "日本語", "parle japonais", "passe en japonais",
    ],
    "zh": [
        "说中文", "中文", "parle chinois", "passe en chinois",
    ],
    "ar": [
        "تحدث عربي", "بالعربية", "parle arabe", "passe en arabe",
    ],
    "nl": [
        "spreek nederlands", "in het nederlands", "parle néerlandais",
    ],
    "pl": [
        "mów po polsku", "po polsku", "parle polonais",
    ],
    "tr": [
        "türkçe konuş", "türkçe", "parle turc",
    ],
    "ko": [
        "한국어로 말해", "한국어", "parle coréen",
    ],
    "sv": [
        "tala svenska", "på svenska", "parle suédois",
    ],
}

# ── Réponses système par langue ───────────────────────────────
REPONSES = {
    "fr": {
        "demarrage":      "Bonjour, je suis Rony. Comment puis-je vous aider ?",
        "pas_compris":    "Désolé, je n'ai pas compris. Pouvez-vous répéter ?",
        "erreur_ia":      "Une erreur est survenue. Je réessaie dans un instant.",
        "quota":          "Je suis en pause momentanément. Je reviens dans quelques secondes.",
        "langue_change":  "Je passe en {langue}.",
        "micro_off":      "Microphone désactivé.",
        "micro_on":       "Je vous écoute.",
        "au_revoir":      "Au revoir ! À bientôt.",
        "rappel":         "Je note ça pour vous.",
        "erreur_service": "Ce service n'est pas disponible pour le moment.",
        "volume_max":     "Volume au maximum.",
        "volume_min":     "Volume au minimum.",
    },
    "pt": {
        "demarrage":      "Olá, eu sou o Rony. Como posso ajudar você ?",
        "pas_compris":    "Desculpe, não entendi. Pode repetir ?",
        "erreur_ia":      "Ocorreu um erro. Vou tentar novamente em instantes.",
        "quota":          "Estou em pausa momentânea. Volto em alguns segundos.",
        "langue_change":  "Mudando para {langue}.",
        "micro_off":      "Microfone desativado.",
        "micro_on":       "Estou ouvindo você.",
        "au_revoir":      "Até logo ! Tchau.",
        "rappel":         "Anotado.",
        "erreur_service": "Este serviço não está disponível no momento.",
        "volume_max":     "Volume no máximo.",
        "volume_min":     "Volume no mínimo.",
    },
    "en": {
        "demarrage":      "Hello, I'm Rony. How can I help you ?",
        "pas_compris":    "Sorry, I didn't catch that. Could you repeat ?",
        "erreur_ia":      "An error occurred. I'll retry in a moment.",
        "quota":          "I'm momentarily paused. I'll be back in a few seconds.",
        "langue_change":  "Switching to {langue}.",
        "micro_off":      "Microphone disabled.",
        "micro_on":       "I'm listening.",
        "au_revoir":      "Goodbye ! See you soon.",
        "rappel":         "Got it, noted.",
        "erreur_service": "This service is unavailable at the moment.",
        "volume_max":     "Volume at maximum.",
        "volume_min":     "Volume at minimum.",
    },
    "es": {
        "demarrage":      "Hola, soy Rony. ¿En qué puedo ayudarte ?",
        "pas_compris":    "Lo siento, no entendí. ¿Puedes repetir ?",
        "erreur_ia":      "Ocurrió un error. Lo intentaré de nuevo en un momento.",
        "quota":          "Estoy en pausa momentánea. Vuelvo en unos segundos.",
        "langue_change":  "Cambiando a {langue}.",
        "micro_off":      "Micrófono desactivado.",
        "micro_on":       "Te escucho.",
        "au_revoir":      "¡Hasta luego !",
        "rappel":         "Anotado.",
        "erreur_service": "Este servicio no está disponible por el momento.",
        "volume_max":     "Volumen al máximo.",
        "volume_min":     "Volumen al mínimo.",
    },
    "de": {
        "demarrage":      "Hallo, ich bin Rony. Wie kann ich Ihnen helfen ?",
        "pas_compris":    "Entschuldigung, ich habe das nicht verstanden. Können Sie wiederholen ?",
        "erreur_ia":      "Ein Fehler ist aufgetreten. Ich versuche es gleich erneut.",
        "quota":          "Ich bin kurz pausiert. Ich bin gleich wieder da.",
        "langue_change":  "Wechsle zu {langue}.",
        "micro_off":      "Mikrofon deaktiviert.",
        "micro_on":       "Ich höre zu.",
        "au_revoir":      "Auf Wiedersehen !",
        "rappel":         "Notiert.",
        "erreur_service": "Dieser Dienst ist momentan nicht verfügbar.",
        "volume_max":     "Lautstärke auf Maximum.",
        "volume_min":     "Lautstärke auf Minimum.",
    },
    "it": {
        "demarrage":      "Ciao, sono Rony. Come posso aiutarti ?",
        "pas_compris":    "Scusa, non ho capito. Puoi ripetere ?",
        "erreur_ia":      "Si è verificato un errore. Riproverò tra un momento.",
        "quota":          "Sono in pausa momentanea. Torno tra pochi secondi.",
        "langue_change":  "Passo a {langue}.",
        "micro_off":      "Microfono disattivato.",
        "micro_on":       "Ti ascolto.",
        "au_revoir":      "Arrivederci !",
        "rappel":         "Annotato.",
        "erreur_service": "Questo servizio non è disponibile al momento.",
        "volume_max":     "Volume al massimo.",
        "volume_min":     "Volume al minimo.",
    },
    "ru": {
        "demarrage":      "Привет, я Рони. Чем могу помочь ?",
        "pas_compris":    "Извините, я не понял. Можете повторить ?",
        "erreur_ia":      "Произошла ошибка. Попробую снова через мгновение.",
        "quota":          "Я на паузе. Вернусь через несколько секунд.",
        "langue_change":  "Переключаюсь на {langue}.",
        "micro_off":      "Микрофон отключён.",
        "micro_on":       "Слушаю вас.",
        "au_revoir":      "До свидания !",
        "rappel":         "Записано.",
        "erreur_service": "Этот сервис временно недоступен.",
        "volume_max":     "Громкость на максимум.",
        "volume_min":     "Громкость на минимум.",
    },
    "ja": {
        "demarrage":      "こんにちは、私はロニーです。どうぞお手伝いします。",
        "pas_compris":    "すみません、聞き取れませんでした。もう一度お願いします。",
        "erreur_ia":      "エラーが発生しました。もう一度試みます。",
        "quota":          "少し待ってください。すぐに戻ります。",
        "langue_change":  "{langue}に切り替えます。",
        "micro_off":      "マイクが無効になりました。",
        "micro_on":       "聞いています。",
        "au_revoir":      "さようなら！",
        "rappel":         "メモしました。",
        "erreur_service": "このサービスは現在利用できません。",
        "volume_max":     "音量を最大にしました。",
        "volume_min":     "音量を最小にしました。",
    },
    "zh": {
        "demarrage":      "您好，我是Rony。我能帮您什么？",
        "pas_compris":    "对不起，我没听清楚。能再说一遍吗？",
        "erreur_ia":      "发生了错误。我稍后再试。",
        "quota":          "我暂时暂停了。几秒钟后回来。",
        "langue_change":  "切换到{langue}。",
        "micro_off":      "麦克风已禁用。",
        "micro_on":       "我在听。",
        "au_revoir":      "再见！",
        "rappel":         "已记录。",
        "erreur_service": "此服务目前不可用。",
        "volume_max":     "音量已调至最大。",
        "volume_min":     "音量已调至最小。",
    },
}

# Fallback pour les langues sans réponses complètes
for _l in VOIX:
    if _l not in REPONSES:
        REPONSES[_l] = REPONSES["en"]

# ── Labels UI ─────────────────────────────────────────────────
UI_LABELS = {
    "fr": {"ecoute": "écoute...", "reflexion": "réflexion...", "connecte": "connecté", "deconnecte": "déconnecté"},
    "pt": {"ecoute": "ouvindo...", "reflexion": "pensando...", "connecte": "conectado", "deconnecte": "desconectado"},
    "en": {"ecoute": "listening...", "reflexion": "thinking...", "connecte": "connected", "deconnecte": "disconnected"},
    "es": {"ecoute": "escuchando...", "reflexion": "pensando...", "connecte": "conectado", "deconnecte": "desconectado"},
    "de": {"ecoute": "höre zu...", "reflexion": "denke...", "connecte": "verbunden", "deconnecte": "getrennt"},
    "it": {"ecoute": "ascolto...", "reflexion": "penso...", "connecte": "connesso", "deconnecte": "disconnesso"},
    "ru": {"ecoute": "слушаю...", "reflexion": "думаю...", "connecte": "подключено", "deconnecte": "отключено"},
    "ja": {"ecoute": "聞いています...", "reflexion": "考えています...", "connecte": "接続済み", "deconnecte": "切断"},
    "zh": {"ecoute": "听着...", "reflexion": "思考中...", "connecte": "已连接", "deconnecte": "已断开"},
}
for _l in VOIX:
    if _l not in UI_LABELS:
        UI_LABELS[_l] = UI_LABELS["en"]


# ── API publique ──────────────────────────────────────────────

def detecter_langue(texte: str) -> str:
    """Détecte la langue d'un texte par comptage de mots-clés."""
    if not texte:
        return _langue_active
    mots = set(re.findall(r'\b\w+\b', texte.lower()))
    scores = {lang: len(mots & mots_cle) for lang, mots_cle in MOTS_CLE.items()}
    meilleur = max(scores, key=scores.get)
    return meilleur if scores[meilleur] > 0 else _langue_active


def definir_langue(langue: str) -> None:
    global _langue_active
    if langue in VOIX:
        _langue_active = langue


def get_langue() -> str:
    return _langue_active


def get_voix() -> str:
    return VOIX.get(_langue_active, VOIX["fr"])


def get_prosody() -> dict:
    """Retorna rate e pitch para o idioma atual (para edge-tts mais humanizado)."""
    return VOIX_PROSODY.get(_langue_active, {"rate": "-5%", "pitch": "+0Hz"})


def get_label(cle: str) -> str:
    return UI_LABELS.get(_langue_active, UI_LABELS["en"]).get(cle, cle)


def get_reponse(cle: str, **kwargs) -> str:
    reponse = REPONSES.get(_langue_active, REPONSES["en"]).get(cle, cle)
    try:
        return reponse.format(**kwargs)
    except KeyError:
        return reponse


def get_nom_langue(code: Optional[str] = None) -> str:
    code = code or _langue_active
    return NOMS_LANGUES.get(code, code)


def langues_disponibles() -> list[str]:
    return list(VOIX.keys())


def verifier_changement_langue(texte: str) -> Optional[str]:
    """Retourne le code langue si une commande de changement est détectée."""
    texte_lower = texte.lower().strip()
    for langue, commandes in COMMANDES_LANGUE.items():
        for cmd in commandes:
            if cmd in texte_lower:
                return langue
    return None


def traiter_langue_auto(texte: str, auto_switch: bool = True) -> str:
    """Traite le texte, détecte la langue et met à jour si auto_switch=True."""
    changement = verifier_changement_langue(texte)
    if changement:
        definir_langue(changement)
        return changement
    if auto_switch:
        langue = detecter_langue(texte)
        definir_langue(langue)
        return langue
    return _langue_active
