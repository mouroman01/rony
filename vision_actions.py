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
from vision_module import analyser_ecran_ia, capturer_et_sauvegarder


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


async def executar_acao_visao(
    texto: str,
    client_gemini=None,
    lingua: str = "pt",
    nome_usuario: str = "usuario",
) -> Optional[str]:
    """Executa comandos naturais de visao/tela/camera."""
    t = _strip_wake_word(texto)

    if any(p in t for p in ("status da camera", "camera funciona", "camera ok", "camera disponivel")):
        return status_camera(lingua)

    if any(p in t for p in ("print", "screenshot", "captura de tela", "capturar tela", "tira print")):
        caminho = capturer_et_sauvegarder()
        return "Captura de tela salva." if caminho else "Nao consegui capturar a tela."

    if any(p in t for p in (
        "analisa a tela", "analise a tela", "olha a tela", "veja a tela",
        "o que tem na tela", "o que esta na tela", "o que está na tela",
        "leia a tela", "ler a tela", "leia o que esta escrito",
        "o que eu faco nessa tela", "o que faço nessa tela", "proximo passo na tela",
    )):
        if not client_gemini:
            return "Consigo tirar print, mas para analisar a tela preciso da chave Gemini configurada."
        return await analyser_ecran_ia(client_gemini, prompt=_prompt_tela(t, lingua), langue=lingua)

    if any(p in t for p in (
        "tira foto", "tira uma foto", "take photo", "take a picture",
        "foto pela camera", "captura pela camera", "selfie",
    )):
        caminho = await asyncio.get_event_loop().run_in_executor(None, capturar_e_salvar)
        return "Foto tirada e salva em captures." if caminho else "Nao consegui tirar a foto. Camera inacessivel."

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
