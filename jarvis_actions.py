import os
import re
import unicodedata
import urllib.parse
import webbrowser
import json
from pathlib import Path
from typing import Optional

from app_launcher import lancer_app
from executor_module import controle_sistema, definir_volume, mute_toggle, obter_volume
from file_manager import (
    ALIAS_DOSSIERS,
    abrir_arquivo,
    abrir_pasta,
    pesquisar_arquivos,
    resoudre_chemin,
)
from internet_search import pesquisar_e_resumir, pesquisar_viabilidade
from rony_paths import DATA_DIR
from vision_module import capturer_et_sauvegarder


SITES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "whatsapp web": "https://web.whatsapp.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
}

MEMORIA_JARVIS = DATA_DIR / "jarvis_actions.json"
_ACAO_PENDENTE: dict[str, object] | None = None


OPEN_TRIGGERS = (
    "abre", "abra", "abrir", "abrir o", "abrir a",
    "vai para", "va para", "ir para", "entra no", "entrar no",
    "navega para", "open", "go to", "launch",
)


def _carregar_memoria() -> dict:
    try:
        return json.loads(MEMORIA_JARVIS.read_text(encoding="utf-8"))
    except Exception:
        return {"favoritos": {}}


def _salvar_memoria(dados: dict) -> None:
    MEMORIA_JARVIS.parent.mkdir(parents=True, exist_ok=True)
    MEMORIA_JARVIS.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _extract_after_trigger(texto: str, triggers: tuple[str, ...] = OPEN_TRIGGERS) -> str:
    t = _strip_wake_word(texto)
    for gatilho in sorted(triggers, key=len, reverse=True):
        if t.startswith(gatilho + " "):
            return t[len(gatilho):].strip(" ,.!?")
        marker = f" {gatilho} "
        if marker in t:
            return t.split(marker, 1)[-1].strip(" ,.!?")
    return ""


def _site_search_url(site: str, consulta: str) -> str:
    q = urllib.parse.quote_plus(consulta)
    if site == "youtube":
        return f"https://www.youtube.com/results?search_query={q}"
    if site == "google":
        return f"https://www.google.com/search?q={q}"
    return SITES[site]


def _extrair_consulta_web(texto: str) -> str:
    t = _strip_wake_word(texto)
    padroes = [
        r"(?:pesquisa|pesquisar|busca|buscar|procura|procurar)\s+(?:na internet|na web|online|no google)\s+(?:sobre\s+)?(.+)",
        r"(?:pesquisa|pesquisar|busca|buscar|procura|procurar)\s+(?:sobre\s+)?(.+?)\s+(?:na internet|na web|online|no google)",
        r"(?:me resume|resume|resuma)\s+(?:uma busca\s+)?(?:sobre\s+)?(.+)",
        r"(?:o que a internet diz sobre|o que dizem sobre)\s+(.+)",
    ]
    for padrao in padroes:
        m = re.search(padrao, t)
        if m:
            consulta = m.group(1).strip(" .,!?'\"")
            consulta = re.sub(r"\s+(?:e\s+)?(?:me\s+)?(?:resume|resuma|resumir|explique|explica)$", "", consulta).strip()
            return consulta
    return ""


def _extrair_consulta_viabilidade(texto: str) -> str:
    t = _strip_wake_word(texto)
    padroes = [
        r"(?:faz|faca|faça|realiza|monte|verifica|verifique)\s+(?:uma\s+)?(?:busca|pesquisa|analise|análise)\s+(?:de\s+)?(?:viabilidade\s+)?(?:completa\s+)?(?:sobre\s+|para\s+|de\s+)?(.+)",
        r"(?:vale a pena|compensa)\s+(.+)",
        r"(?:onde comprar|onde encontro|procura lojas?|buscar lojas?|pesquisa lojas?)\s+(?:de\s+|para\s+)?(.+)",
        r"(?:procura|pesquisa|busca|buscar)\s+(?:localidade|locais|lugares|perto|perto de mim|na minha regiao|na minha região)\s+(?:de\s+|para\s+|sobre\s+)?(.+)",
        r"(?:compara|compare|analisa|analise|avalia|avalie)\s+(?:opcoes|opções|precos|preços|lojas|localidades)?\s*(?:de\s+|para\s+|sobre\s+)?(.+)",
    ]
    for padrao in padroes:
        m = re.search(padrao, t)
        if m:
            consulta = m.group(1).strip(" .,!?'\"")
            consulta = re.sub(r"\s+(?:e\s+)?(?:me\s+)?(?:resume|resuma|resumir)$", "", consulta).strip()
            return consulta
    return ""


def _pesquisa_viabilidade(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    gatilhos = (
        "viabilidade", "vale a pena", "compensa", "onde comprar", "onde encontro",
        "loja", "lojas", "preco", "preço", "mais barato", "oferta",
        "localidade", "locais", "lugares", "perto de mim", "na minha regiao",
        "na minha região", "comparar", "compare", "custo beneficio", "custo benefício",
    )
    if not any(g in t for g in gatilhos):
        return None
    consulta = _extrair_consulta_viabilidade(t) or _extrair_consulta_web(t)
    if not consulta or len(consulta) < 3:
        return "O que voce quer que eu avalie em uma busca completa?"
    try:
        return pesquisar_viabilidade(consulta)
    except Exception as exc:
        return f"Nao consegui completar a pesquisa de viabilidade: {exc}"


def _buscar_na_internet(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    if not any(p in t for p in ("internet", "web", "online", "google", "resume", "resuma")):
        return None
    if "youtube" in t:
        return None
    consulta = _extrair_consulta_web(t)
    if not consulta or len(consulta) < 3:
        return "O que voce quer que eu pesquise na internet?"
    try:
        return pesquisar_e_resumir(consulta)
    except Exception as exc:
        return f"Nao consegui completar a busca na internet: {exc}"


def _confirmacao_pendente(texto: str) -> Optional[str]:
    global _ACAO_PENDENTE
    t = _strip_wake_word(texto)
    if not _ACAO_PENDENTE:
        return None

    if any(p in t for p in ("cancela", "cancelar", "nao", "não", "deixa", "esquece")):
        _ACAO_PENDENTE = None
        return "Tudo bem, cancelei."

    if not any(p in t for p in ("confirma", "confirmo", "sim", "pode", "executa", "confirmar")):
        return None

    acao = str(_ACAO_PENDENTE.get("acao", ""))
    delay = int(_ACAO_PENDENTE.get("delay", 0))
    _ACAO_PENDENTE = None
    resultado = controle_sistema(acao, delay)
    if resultado.get("sucesso"):
        nomes = {
            "desligar": "desligamento iniciado.",
            "reiniciar": "reinicializacao iniciada.",
            "bloquear": "tela bloqueada.",
            "hibernar": "modo dormir iniciado.",
            "logoff": "logoff iniciado.",
        }
        return nomes.get(acao, "Acao executada.")
    return f"Nao consegui executar: {resultado.get('erro', 'erro desconhecido')}."


def _acao_perigosa(texto: str) -> Optional[str]:
    global _ACAO_PENDENTE
    t = _strip_wake_word(texto)
    acoes = [
        ("desligar", ("desliga o pc", "desliga o computador", "desligar pc", "shutdown")),
        ("reiniciar", ("reinicia o pc", "reinicia o computador", "restart", "reboot")),
        ("bloquear", ("bloqueia a tela", "bloquear a tela", "lock screen")),
        ("hibernar", ("modo dormir", "hiberna", "sleep mode")),
        ("logoff", ("fazer logoff", "sair do windows", "logout", "logoff")),
    ]
    for acao, termos in acoes:
        if any(termo in t for termo in termos):
            _ACAO_PENDENTE = {"acao": acao, "delay": 0}
            return f"Isso é uma ação sensível: {acao}. Diga confirma para executar ou cancela para abortar."
    return None


def _memoria_preferencias(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    m = re.search(r"(?:lembre que|memoriza que|salva que)\s+(?:meu|minha)\s+(.+?)\s+(?:e|é)\s+(.+)", t)
    if not m:
        return None
    chave = m.group(1).strip()
    valor = m.group(2).strip()
    dados = _carregar_memoria()
    dados.setdefault("favoritos", {})[chave] = valor
    _salvar_memoria(dados)
    return f"Memorizei: {chave} é {valor}."


def _abrir_site(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)

    pesquisa = re.search(r"(?:pesquisa|pesquisar|procura|procurar|busca|buscar)\s+(.*?)\s+(?:no|na|em)\s+(youtube|google)", t)
    if pesquisa:
        consulta, site = pesquisa.group(1).strip(), pesquisa.group(2).strip()
        webbrowser.open(_site_search_url(site, consulta))
        return f"Pesquisando {consulta} no {site}."

    pesquisa = re.search(r"(?:youtube|google)\s+(?:pesquisa|procura|busca)\s+(.*)", t)
    if pesquisa:
        site = "youtube" if "youtube" in t else "google"
        consulta = pesquisa.group(1).strip()
        webbrowser.open(_site_search_url(site, consulta))
        return f"Pesquisando {consulta} no {site}."

    if any(g in t for g in OPEN_TRIGGERS):
        for nome, url in SITES.items():
            if nome in t:
                webbrowser.open(url)
                return f"Abrindo {nome}."
    return None


def _controlar_volume(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    if "volume" not in t and "som" not in t:
        return None

    match = re.search(r"(?:volume|som)\s+(?:em|para|no|a|to)\s*(\d{1,3})", t)
    if not match:
        match = re.search(r"(\d{1,3})\s*(?:%|por cento)?\s*(?:de\s*)?volume", t)
    if match:
        nivel = max(0, min(100, int(match.group(1))))
        definir_volume(nivel)
        return f"Volume definido em {nivel}%."

    if any(p in t for p in ("aumenta", "aumentar", "sobe", "mais", "volume up")):
        atual = obter_volume() or 50
        nivel = min(100, atual + 15)
        definir_volume(nivel)
        return f"Volume aumentado para {nivel}%."

    if any(p in t for p in ("diminui", "diminuir", "baixa", "menos", "volume down")):
        atual = obter_volume() or 50
        nivel = max(0, atual - 15)
        definir_volume(nivel)
        return f"Volume diminuido para {nivel}%."

    if any(p in t for p in ("muta", "silencia", "sem som", "mute")):
        resultado = mute_toggle()
        return "Som silenciado." if resultado.get("mudo", True) else "Som ativado."

    if any(p in t for p in ("qual", "atual", "quanto")):
        return f"O volume esta em {obter_volume()}%."

    return None


def _captura_tela(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    if not any(p in t for p in ("print", "screenshot", "captura de tela", "capturar tela", "tira print")):
        return None
    caminho = capturer_et_sauvegarder()
    return "Captura de tela salva." if caminho else "Nao consegui capturar a tela."


def _abrir_camera(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    if not any(palavra in t for palavra in ("camera", "webcam")):
        return None
    if not any(g in t for g in ("abre", "abra", "abrir", "liga", "ligar", "open")):
        return None
    try:
        os.startfile("microsoft.windows.camera:")
        return "Abrindo a camera."
    except Exception as exc:
        return f"Nao consegui abrir a camera: {exc}"


def _resolver_alvo(nome: str) -> Optional[Path]:
    if not nome:
        return None
    caminho = resoudre_chemin(nome)
    if caminho:
        return caminho
    resultados = pesquisar_arquivos(nome)
    return resultados[0] if resultados else None


def _abrir_arquivo_ou_pasta(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    alvo = _extract_after_trigger(t)
    if not alvo:
        return None

    alvo = re.sub(r"^(o|a|os|as|arquivo|arquivos|pasta|folder|file)\s+", "", alvo).strip()
    if not alvo:
        return "Qual arquivo ou pasta voce quer abrir?"

    for alias, caminho in sorted(ALIAS_DOSSIERS.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in alvo:
            return abrir_pasta(caminho)

    caminho = _resolver_alvo(alvo)
    if caminho and caminho.is_file():
        _registrar_recente("arquivo", str(caminho))
        return abrir_arquivo(caminho)
    if caminho and caminho.is_dir():
        _registrar_recente("pasta", str(caminho))
        return abrir_pasta(caminho)

    if any(p in t for p in ("arquivo", "file")):
        return f"Nao encontrei o arquivo {alvo}."
    if any(p in t for p in ("pasta", "folder", "downloads", "documentos", "desktop")):
        return f"Nao encontrei a pasta {alvo}."
    return None


def _registrar_recente(tipo: str, valor: str) -> None:
    dados = _carregar_memoria()
    recentes = dados.setdefault("recentes", [])
    recentes.insert(0, {"tipo": tipo, "valor": valor})
    dados["recentes"] = recentes[:20]
    _salvar_memoria(dados)


def _abrir_recente(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    if not any(p in t for p in ("ultimo arquivo", "último arquivo", "arquivo recente", "ultima pasta", "última pasta")):
        return None
    dados = _carregar_memoria()
    quer_pasta = "pasta" in t
    for item in dados.get("recentes", []):
        if (quer_pasta and item.get("tipo") == "pasta") or (not quer_pasta and item.get("tipo") == "arquivo"):
            caminho = Path(str(item.get("valor", "")))
            if caminho.is_file():
                return abrir_arquivo(caminho)
            if caminho.is_dir():
                return abrir_pasta(caminho)
    return "Ainda nao tenho um item recente desse tipo."


def _abrir_aplicativo(texto: str) -> Optional[str]:
    t = _strip_wake_word(texto)
    if not any(g in t for g in ("abre", "abra", "abrir", "open", "lance", "inicia")):
        return None
    alvo = _extract_after_trigger(t, ("abre", "abra", "abrir", "open", "lance", "inicia"))
    if not alvo:
        return None
    if alvo in SITES or "camera" in alvo or "webcam" in alvo:
        return None
    if any(p in alvo for p in ("arquivo", "pasta", "folder", "file")):
        return None
    return lancer_app(alvo)


def executar_intencao_rapida(texto: str) -> Optional[str]:
    """Executa acoes locais obvias antes da IA conversacional."""
    for handler in (
        _confirmacao_pendente,
        _acao_perigosa,
        _memoria_preferencias,
        _pesquisa_viabilidade,
        _buscar_na_internet,
        _controlar_volume,
        _captura_tela,
        _abrir_site,
        _abrir_camera,
        _abrir_recente,
        _abrir_arquivo_ou_pasta,
        _abrir_aplicativo,
    ):
        resposta = handler(texto)
        if resposta:
            return resposta
    return None
