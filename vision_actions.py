import asyncio
import re
import unicodedata
from typing import Optional

from camera_module import (
    aprender_rosto,
    capturar_e_salvar,
    resposta_o_que_e_isso,
    resposta_o_que_voce_ve,
    resposta_tem_alguem,
    status_camera,
)
from vision_module import (
    analyser_ecran_ia,
    capturer_et_sauvegarder,
    cliquer_coordonnees as clicar_coordonnees,
    taper_texte,
    appuyer_touche,
    raccourci,
    scroll,
    get_resolution_ecran,
    capturer_ecran,
)


def _norm(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", texto)


def _strip_wake_word(texto: str) -> str:
    t = _norm(texto)
    for prefixo in ("hey rony", "ok rony", "oi rony", "rony"):
        if t.startswith(prefixo + " "):
            return t[len(prefixo):].strip(" ,.!?")
    return t


def _extrair_nome_rosto(texto: str, nome_padrao: str = "usuario") -> str:
    t = _strip_wake_word(texto)
    for prep in ("me chamo ", "meu nome e ", "meu nome é ", "sou o ", "sou a ", "de "):
        if prep in t:
            nome = t.split(prep, 1)[-1].strip().split()[0]
            return nome or nome_padrao
    return nome_padrao


def _prompt_tela(texto: str, lingua: str) -> str:
    t = _strip_wake_word(texto)
    if any(p in t for p in ("leia", "ler", "texto", "ocr", "escrito", "escrita")):
        return {
            "pt": "Leia o texto visivel na tela. Resuma o conteudo e destaque qualquer botao, alerta ou campo importante.",
            "en": "Read the visible text on the screen. Summarize it and highlight important buttons, alerts or fields.",
            "es": "Lee el texto visible en la pantalla. Resume el contenido y destaca botones, alertas o campos importantes.",
            "fr": "Lis le texte visible a l'ecran. Resume le contenu et signale les boutons, alertes ou champs importants.",
        }.get(lingua, "Read the visible text on the screen and summarize it.")
    if any(p in t for p in ("o que eu faco", "o que faço", "proximo passo", "próximo passo", "como resolvo", "ajuda na tela")):
        return {
            "pt": "Analise a tela e diga qual e o proximo passo mais provavel. Seja pratico e objetivo.",
            "en": "Analyze the screen and say the most likely next step. Be practical and concise.",
            "es": "Analiza la pantalla y di cual es el siguiente paso mas probable. Se practico y breve.",
            "fr": "Analyse l'ecran et dis quelle est probablement la prochaine action. Sois pratique et concis.",
        }.get(lingua, "Analyze the screen and suggest the next practical step.")
    return {
        "pt": "Descreva o que voce ve na tela, incluindo texto visivel, janelas, botoes e acoes possiveis.",
        "en": "Describe what you see on the screen, including visible text, windows, buttons and possible actions.",
        "es": "Describe lo que ves en la pantalla, incluyendo texto visible, ventanas, botones y acciones posibles.",
        "fr": "Decris ce que tu vois a l'ecran, y compris le texte, les fenetres, boutons et actions possibles.",
    }.get(lingua, "Describe what you see on the screen.")


# ── Mapeamento de teclas (voz → pyautogui) ────────────────────
_KEY_MAP: dict[str, str] = {
    # Enter / Return
    "enter": "enter", "entrar": "enter", "confirmar": "enter", "confirma": "enter",
    "return": "enter",
    # Escape
    "escape": "escape", "esc": "escape", "escapar": "escape", "cancela": "escape",
    # Tab
    "tab": "tab",
    # Backspace / Delete
    "backspace": "backspace", "apaga": "backspace", "apagar": "backspace",
    "delete": "delete", "del": "delete", "deletar": "delete",
    # Setas
    "cima": "up", "seta cima": "up", "up": "up",
    "baixo": "down", "seta baixo": "down", "down": "down",
    "esquerda": "left", "seta esquerda": "left", "left": "left",
    "direita": "right", "seta direita": "right", "right": "right",
    # Function keys
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5",
    "f6": "f6", "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10",
    "f11": "f11", "f12": "f12",
    # Space, Home, End, PageUp/Down
    "espaço": "space", "espaco": "space", "space": "space",
    "home": "home", "inicio": "home",
    "end": "end", "fim": "end",
    "page up": "pageup", "pagina cima": "pageup", "pgup": "pageup",
    "page down": "pagedown", "pagina baixo": "pagedown", "pgdn": "pagedown",
    # Print Screen / Pause
    "print screen": "printscreen", "imprimir tela": "printscreen",
    "pause": "pause", "pausar": "pause",
    # Windows key
    "windows": "win", "tecla windows": "win",
}

# Mapeamento de atalhos compostos (voz → lista de teclas pyautogui)
_SHORTCUT_MAP: dict[str, list[str]] = {
    "ctrl c": ["ctrl", "c"], "copiar": ["ctrl", "c"], "copia": ["ctrl", "c"],
    "ctrl v": ["ctrl", "v"], "colar": ["ctrl", "v"], "cola": ["ctrl", "v"],
    "ctrl x": ["ctrl", "x"], "recortar": ["ctrl", "x"], "recorta": ["ctrl", "x"],
    "ctrl z": ["ctrl", "z"], "desfazer": ["ctrl", "z"], "desfaz": ["ctrl", "z"],
    "ctrl y": ["ctrl", "y"], "refazer": ["ctrl", "y"],
    "ctrl a": ["ctrl", "a"], "selecionar tudo": ["ctrl", "a"], "seleciona tudo": ["ctrl", "a"],
    "ctrl s": ["ctrl", "s"], "salvar": ["ctrl", "s"], "salva": ["ctrl", "s"],
    "ctrl n": ["ctrl", "n"], "novo": ["ctrl", "n"],
    "ctrl w": ["ctrl", "w"], "fechar aba": ["ctrl", "w"], "fecha aba": ["ctrl", "w"],
    "ctrl t": ["ctrl", "t"], "nova aba": ["ctrl", "t"],
    "ctrl r": ["ctrl", "r"], "recarregar": ["ctrl", "r"], "atualizar pagina": ["ctrl", "r"],
    "ctrl f": ["ctrl", "f"], "buscar": ["ctrl", "f"], "pesquisar na pagina": ["ctrl", "f"],
    "ctrl p": ["ctrl", "p"], "imprimir": ["ctrl", "p"],
    "ctrl h": ["ctrl", "h"], "substituir": ["ctrl", "h"],
    "ctrl l": ["ctrl", "l"], "barra de endereco": ["ctrl", "l"],
    "ctrl shift t": ["ctrl", "shift", "t"], "reabrir aba": ["ctrl", "shift", "t"],
    "alt tab": ["alt", "tab"], "trocar janela": ["alt", "tab"],
    "alt f4": ["alt", "f4"], "fechar janela": ["alt", "f4"],
    "ctrl alt delete": ["ctrl", "alt", "delete"],
    "win d": ["win", "d"], "mostrar desktop": ["win", "d"], "minimizar tudo": ["win", "d"],
    "win e": ["win", "e"], "explorador": ["win", "e"], "abrir explorador": ["win", "e"],
    "win l": ["win", "l"], "bloquear tela": ["win", "l"],
    "print screen": ["printscreen"],
    "alt print screen": ["alt", "printscreen"],
}


def _detectar_atalho(t: str) -> Optional[list[str]]:
    """Detecta se o texto é um atalho de teclado e retorna as teclas."""
    for nome, teclas in sorted(_SHORTCUT_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if nome in t:
            return teclas
    # Padrão ctrl+X, alt+X, etc.
    m = re.search(r"(ctrl|control)\s*\+\s*(\w+)", t)
    if m:
        return ["ctrl", m.group(2).lower()]
    m = re.search(r"alt\s*\+\s*(\w+)", t)
    if m:
        return ["alt", m.group(1).lower()]
    m = re.search(r"shift\s*\+\s*(\w+)", t)
    if m:
        return ["shift", m.group(1).lower()]
    return None


def _detectar_tecla(t: str) -> Optional[str]:
    """Detecta se o texto menciona uma tecla simples."""
    for nome, tecla in sorted(_KEY_MAP.items(), key=len, reverse=True):
        if nome in t:
            return tecla
    # F-keys numéricas
    m = re.search(r"\bf(\d{1,2})\b", t)
    if m:
        return f"f{m.group(1)}"
    return None


async def _clicar_elemento_ia(
    elemento: str,
    client_gemini,
    lingua: str,
    duplo: bool = False,
) -> str:
    """
    Usa Gemini Vision para localizar um elemento na tela e clicar nele.
    Estratégia: screenshot → prompt JSON → parse x,y → click.
    """
    img_bytes = capturer_ecran()
    if not img_bytes:
        return {
            "pt": "Não consigo capturar a tela para encontrar o elemento.",
            "en": "Can't capture screen to find the element.",
        }.get(lingua, "Can't capture screen.")

    largura, altura = get_resolution_ecran()

    prompt = (
        f"This is a screenshot ({largura}x{altura} px). "
        f"Find the UI element: \"{elemento}\". "
        f"Respond with ONLY the pixel coordinates as: x,y (two integers). "
        f"If you cannot find the element, respond with: not_found"
    )

    try:
        import google.genai as genai
        from google.genai import types

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client_gemini.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            ),
        )

        resposta = (response.text or "").strip().lower()

        if "not_found" in resposta or "nao encontrei" in resposta:
            return {
                "pt": f"Não encontrei '{elemento}' na tela.",
                "en": f"Couldn't find '{elemento}' on screen.",
                "es": f"No encontré '{elemento}' en la pantalla.",
            }.get(lingua, f"Element not found: {elemento}")

        m = re.search(r"(\d+)\s*[,;\s]\s*(\d+)", resposta)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            # Valida que está dentro dos limites da tela
            if 0 <= x <= largura and 0 <= y <= altura:
                ok = clicar_coordonnees(x, y, double=duplo)
                if ok:
                    acao = "Duplo clique" if duplo else "Clique"
                    return {
                        "pt": f"{acao} em '{elemento}' realizado.",
                        "en": f"{'Double-clicked' if duplo else 'Clicked'} '{elemento}'.",
                        "es": f"{'Doble clic' if duplo else 'Clic'} en '{elemento}' realizado.",
                    }.get(lingua, f"Clicked '{elemento}'.")
                return {
                    "pt": "Clique falhou. Tente novamente.",
                    "en": "Click failed. Try again.",
                }.get(lingua, "Click failed.")
            else:
                return {
                    "pt": f"Coordenadas inválidas ({x},{y}) para tela {largura}x{altura}.",
                    "en": f"Invalid coordinates ({x},{y}) for screen {largura}x{altura}.",
                }.get(lingua, "Invalid coordinates.")

        return {
            "pt": f"Não consegui identificar a posição de '{elemento}' na tela.",
            "en": f"Couldn't determine position of '{elemento}' on screen.",
        }.get(lingua, f"Couldn't find position of '{elemento}'.")

    except Exception as e:
        return {
            "pt": f"Erro ao tentar clicar: {e}",
            "en": f"Error trying to click: {e}",
        }.get(lingua, str(e))


async def executar_acao_visao(
    texto: str,
    client_gemini=None,
    lingua: str = "pt",
    nome_usuario: str = "usuario",
) -> Optional[str]:
    """Executa comandos naturais de visao/tela/camera/mouse/teclado."""
    t = _strip_wake_word(texto)

    # ── Status câmera ─────────────────────────────────────────
    if any(p in t for p in ("status da camera", "camera funciona", "camera ok", "camera disponivel")):
        return status_camera(lingua)

    # ── Screenshot ────────────────────────────────────────────
    if any(p in t for p in ("print", "screenshot", "captura de tela", "capturar tela", "tira print")):
        caminho = capturer_et_sauvegarder()
        return {
            "pt": "Captura de tela salva.",
            "en": "Screenshot saved.",
            "es": "Captura de pantalla guardada.",
        }.get(lingua, "Screenshot saved.") if caminho else {
            "pt": "Nao consegui capturar a tela.",
            "en": "Couldn't capture screen.",
        }.get(lingua, "Couldn't capture screen.")

    # ── Analisa tela via IA ───────────────────────────────────
    if any(p in t for p in (
        "analisa a tela", "analise a tela", "olha a tela", "veja a tela",
        "o que tem na tela", "o que esta na tela", "o que está na tela",
        "leia a tela", "ler a tela", "leia o que esta escrito",
        "o que eu faco nessa tela", "o que faço nessa tela", "proximo passo na tela",
    )):
        if not client_gemini:
            return "Consigo tirar print, mas para analisar a tela preciso da chave Gemini configurada."
        return await analyser_ecran_ia(client_gemini, prompt=_prompt_tela(t, lingua), langue=lingua)

    # ── ATALHOS DE TECLADO ────────────────────────────────────
    # Deve vir antes dos cliques para evitar conflito com "ctrl" etc.
    triggers_atalho = {
        "usa o atalho", "use o atalho", "atalho", "pressiona", "aperta", "aperte",
        "tecla", "shortcut", "ctrl", "alt+", "shift+", "win+",
    }
    if any(p in t for p in triggers_atalho):
        teclas = _detectar_atalho(t)
        if teclas:
            ok = raccourci(teclas)
            nomes = "+".join(k.upper() for k in teclas)
            return {
                "pt": f"Atalho {nomes} executado." if ok else f"Falha ao executar {nomes}.",
                "en": f"Shortcut {nomes} executed." if ok else f"Failed to execute {nomes}.",
                "es": f"Atajo {nomes} ejecutado." if ok else f"Error al ejecutar {nomes}.",
            }.get(lingua, f"Shortcut {nomes}.")
        tecla = _detectar_tecla(t)
        if tecla:
            ok = appuyer_touche(tecla)
            return {
                "pt": f"Tecla {tecla.upper()} pressionada." if ok else f"Falha ao pressionar {tecla}.",
                "en": f"Key {tecla.upper()} pressed." if ok else f"Failed to press {tecla}.",
                "es": f"Tecla {tecla.upper()} presionada." if ok else f"Error al presionar {tecla}.",
            }.get(lingua, f"Key {tecla}.")

    # ── PRESSIONAR TECLA SIMPLES ──────────────────────────────
    triggers_tecla = {
        "pressiona a tecla", "aperta a tecla", "pressiona o", "aperta o",
        "aperta enter", "aperta escape", "aperta tab",
        "press enter", "press escape",
    }
    if any(p in t for p in triggers_tecla):
        tecla = _detectar_tecla(t)
        if tecla:
            ok = appuyer_touche(tecla)
            return {
                "pt": f"Tecla {tecla.upper()} pressionada." if ok else "Falha ao pressionar a tecla.",
                "en": f"Key {tecla.upper()} pressed." if ok else "Failed to press key.",
            }.get(lingua, f"Key {tecla}.")

    # ── DIGITAR / ESCREVER TEXTO ──────────────────────────────
    triggers_digitar = {
        "digita ", "digitar ", "escreve ", "escrever ", "escrevia ",
        "type ", "write ", "typo ", "tipos ",
    }
    for gatilho in triggers_digitar:
        if gatilho in t:
            texto_digitar = t.split(gatilho, 1)[-1].strip().strip('"\'')
            if texto_digitar:
                ok = taper_texte(texto_digitar)
                return {
                    "pt": f"Texto digitado: '{texto_digitar}'." if ok else "Falha ao digitar.",
                    "en": f"Typed: '{texto_digitar}'." if ok else "Failed to type.",
                    "es": f"Texto escrito: '{texto_digitar}'." if ok else "Error al escribir.",
                }.get(lingua, f"Typed: '{texto_digitar}'.")

    # ── SCROLL ────────────────────────────────────────────────
    triggers_scroll = {"rola", "rolar", "scroll", "descer", "subir a pagina"}
    if any(p in t for p in triggers_scroll):
        direcao = "up" if any(p in t for p in ("cima", "subir", "up", "para cima")) else "down"
        # Extrai quantidade (ex: "rola 5 vezes")
        m_qtd = re.search(r"(\d+)\s*(?:vezes?|clicks?|cliques?)?", t)
        clics = int(m_qtd.group(1)) if m_qtd else 3
        clics = max(1, min(clics, 20))
        ok = scroll(direcao, clics)
        return {
            "pt": f"Rolado {'para cima' if direcao == 'up' else 'para baixo'}." if ok else "Falha no scroll.",
            "en": f"Scrolled {'up' if direcao == 'up' else 'down'}." if ok else "Scroll failed.",
            "es": f"Desplazado {'arriba' if direcao == 'up' else 'abajo'}." if ok else "Error en scroll.",
        }.get(lingua, "Scrolled.")

    # ── CLICAR EM ELEMENTO (por nome / descrição) ─────────────
    triggers_clique = {
        "clica em ", "clique em ", "clica no ", "clica na ", "clique no ", "clique na ",
        "click em ", "click no ", "click na ", "click on ",
        "clica o botao ", "clique o botao ", "clica o ", "clique o ",
        "clica na opcao ", "clique na opcao ",
        "seleciona ", "selecione ", "select ",
    }
    duplo = any(p in t for p in ("duplo", "double", "dois cliques", "double click", "duplo clique"))
    for gatilho in sorted(triggers_clique, key=len, reverse=True):
        if gatilho in t:
            elemento = t.split(gatilho, 1)[-1].strip().strip('"\'.,!?')
            if elemento and len(elemento) >= 2:
                if not client_gemini:
                    return {
                        "pt": "Para clicar em elementos preciso do Gemini configurado. Veja o .env.",
                        "en": "Clicking elements requires Gemini API key. Check .env.",
                    }.get(lingua, "Gemini required for smart click.")
                return await _clicar_elemento_ia(elemento, client_gemini, lingua, duplo=duplo)

    # ── CLICAR EM COORDENADAS DIRETAS ("clica em x=100 y=200") ─
    m_coord = re.search(r"(?:clica|click|clique)\s+(?:em\s+)?(?:x\s*[=:]\s*)?(\d+)\s*[,\s]+(?:y\s*[=:]\s*)?(\d+)", t)
    if m_coord:
        x, y = int(m_coord.group(1)), int(m_coord.group(2))
        ok = clicar_coordonnees(x, y, double=duplo)
        return {
            "pt": f"Clique em ({x},{y}) realizado." if ok else f"Falha ao clicar em ({x},{y}).",
            "en": f"Clicked at ({x},{y})." if ok else f"Failed to click at ({x},{y}).",
        }.get(lingua, f"Clicked ({x},{y}).")

    # ── Tira foto pela câmera ─────────────────────────────────
    if any(p in t for p in (
        "tira foto", "tira uma foto", "take photo", "take a picture",
        "foto pela camera", "captura pela camera", "selfie",
    )):
        caminho = await asyncio.get_event_loop().run_in_executor(None, capturar_e_salvar)
        return {
            "pt": "Foto tirada e salva em captures.",
            "en": "Photo taken and saved.",
        }.get(lingua, "Photo saved.") if caminho else {
            "pt": "Nao consegui tirar a foto. Camera inacessivel.",
            "en": "Couldn't take photo. Camera inaccessible.",
        }.get(lingua, "Camera inaccessible.")

    if any(p in t for p in (
        "tem alguem", "tem alguém", "quem esta ai", "quem está aí",
        "quem esta aqui", "tem pessoa", "ve alguem", "vê alguém",
    )):
        return await resposta_tem_alguem(lingua=lingua)

    if any(p in t for p in (
        "aprende meu rosto", "aprende o rosto", "memoriza meu rosto",
        "lembra do meu rosto", "me reconhece", "learn my face",
    )):
        nome = _extrair_nome_rosto(t, nome_usuario or "usuario")
        return await asyncio.get_event_loop().run_in_executor(None, aprender_rosto, nome)

    if any(p in t for p in (
        "o que e isso", "o que é isso", "que objeto e esse", "que objeto é esse",
        "identifica isso", "identifica esse objeto", "what is this",
    )):
        dica = ""
        for prep in ("esse ", "essa ", "este ", "esta ", "this "):
            if prep in t:
                dica = t.split(prep, 1)[-1].strip()
                break
        return await resposta_o_que_e_isso(client_gemini=client_gemini, objeto_hint=dica, lingua=lingua)

    if any(p in t for p in (
        "o que voce ve", "o que você vê", "o que vc ve", "o que a camera ve",
        "olha pela camera", "veja pela camera", "analisa a camera",
        "descreve a camera", "descreve o ambiente", "what do you see",
    )):
        return await resposta_o_que_voce_ve(client_gemini=client_gemini, lingua=lingua)

    return None
