# ============================================================
#  obsidian_manager.py — Integração Obsidian para R.O.N.Y
#
#  Funcionalidades:
#    • Auto-detecta o vault Obsidian em locais comuns
#    • Cria notas a partir de comandos de voz
#    • Organiza notas por pasta/projeto do computador
#    • Sincroniza estrutura de pastas → estrutura do vault
#    • Adiciona anexos, tags e links automáticos
# ============================================================

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════
#  DETECÇÃO DO VAULT
# ═══════════════════════════════════════════════════════════════

def _detectar_vault() -> Optional[Path]:
    """Detecta o vault Obsidian em locais comuns do Windows."""
    # 1. Variável de ambiente
    vault_env = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
    if vault_env and Path(vault_env).is_dir():
        return Path(vault_env)

    # 2. Locais comuns
    candidatos = [
        Path.home() / "Documents" / "Obsidian",
        Path.home() / "Obsidian",
        Path.home() / "OneDrive" / "Obsidian",
        Path.home() / "Dropbox" / "Obsidian",
        Path.home() / "Desktop" / "Obsidian",
        Path.home() / "Documents" / "Notes",
        Path.home() / "Documents" / "Notas",
        Path.home() / "Documents" / "Vault",
    ]
    for c in candidatos:
        if c.is_dir():
            return c

    # 3. Busca por marcador .obsidian em subpastas de Documents
    docs = Path.home() / "Documents"
    if docs.is_dir():
        for sub in docs.iterdir():
            if sub.is_dir() and (sub / ".obsidian").is_dir():
                return sub

    return None


def get_vault() -> Optional[Path]:
    """Retorna o vault detectado ou None."""
    return _detectar_vault()


def vault_info(lingua: str = "pt") -> str:
    """Retorna uma string descrevendo o vault detectado."""
    v = get_vault()
    if not v:
        return {
            "pt": "Vault Obsidian não encontrado. Configure OBSIDIAN_VAULT_PATH no .env ou crie a pasta Obsidian em Documentos.",
            "en": "Obsidian vault not found. Set OBSIDIAN_VAULT_PATH in .env or create an Obsidian folder in Documents.",
        }.get(lingua, "Vault not found.")
    notas = sum(1 for f in v.rglob("*.md") if not f.name.startswith("."))
    return {
        "pt": f"Vault Obsidian em '{v.name}': {notas} notas.",
        "en": f"Obsidian vault at '{v.name}': {notas} notes.",
    }.get(lingua, f"Vault: {v.name}, {notas} notes.")


# ═══════════════════════════════════════════════════════════════
#  CRIAÇÃO DE NOTAS
# ═══════════════════════════════════════════════════════════════

def _sanitizar(nome: str) -> str:
    """Remove caracteres inválidos para nome de arquivo."""
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome).strip(" .")
    return nome or "nota"


def criar_nota(
    titulo: str,
    conteudo: str = "",
    tags: list[str] = None,
    pasta: str = "",
    vault: Path = None,
) -> Optional[Path]:
    """
    Cria uma nota .md no vault Obsidian.

    titulo   : título da nota (vira nome do arquivo)
    conteudo : corpo da nota em Markdown
    tags     : lista de tags Obsidian (ex: ["rony", "auto"])
    pasta    : subpasta dentro do vault (criada se não existir)
    vault    : caminho do vault (detectado automaticamente se None)
    """
    vault = vault or get_vault()
    if not vault:
        return None

    pasta_alvo = vault / _sanitizar(pasta) if pasta else vault
    pasta_alvo.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"{_sanitizar(titulo)}.md"
    caminho = pasta_alvo / nome_arquivo

    # Frontmatter YAML
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    tags_yaml = "\n".join(f"  - {t}" for t in (tags or ["rony", "auto"])) or "  - rony"
    frontmatter = f"""---
title: "{titulo}"
created: "{ts}"
tags:
{tags_yaml}
source: "Rony AI"
---

"""

    corpo = frontmatter + conteudo if conteudo else frontmatter + f"# {titulo}\n\n"

    try:
        caminho.write_text(corpo, encoding="utf-8")
        return caminho
    except Exception as e:
        print(f"[OBSIDIAN] Erro ao criar nota: {e}")
        return None


def adicionar_a_nota(
    titulo: str,
    texto: str,
    vault: Path = None,
) -> bool:
    """Adiciona texto ao final de uma nota existente."""
    vault = vault or get_vault()
    if not vault:
        return False

    resultados = list(vault.rglob(f"{_sanitizar(titulo)}.md"))
    if not resultados:
        return False

    caminho = resultados[0]
    try:
        conteudo_atual = caminho.read_text(encoding="utf-8")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        novo = f"\n\n---\n*Adicionado em {ts}:*\n\n{texto}"
        caminho.write_text(conteudo_atual + novo, encoding="utf-8")
        return True
    except Exception:
        return False


def buscar_notas(consulta: str, vault: Path = None, limite: int = 5) -> list[dict]:
    """Busca notas por título ou conteúdo."""
    vault = vault or get_vault()
    if not vault:
        return []

    consulta_lower = consulta.lower()
    resultados = []

    for nota in vault.rglob("*.md"):
        if nota.name.startswith("."):
            continue
        try:
            titulo_match = consulta_lower in nota.stem.lower()
            conteudo_match = False
            if not titulo_match:
                conteudo = nota.read_text(encoding="utf-8", errors="ignore")
                conteudo_match = consulta_lower in conteudo.lower()

            if titulo_match or conteudo_match:
                resultados.append({
                    "titulo": nota.stem,
                    "caminho": str(nota),
                    "pasta": nota.parent.name,
                    "relevancia": 2 if titulo_match else 1,
                })
        except Exception:
            continue

    resultados.sort(key=lambda x: x["relevancia"], reverse=True)
    return resultados[:limite]


# ═══════════════════════════════════════════════════════════════
#  ORGANIZAÇÃO AUTOMÁTICA — PASTAS → VAULT
# ═══════════════════════════════════════════════════════════════

def organizar_pasta_em_vault(
    pasta_origem: Path,
    vault: Path = None,
    client_gemini=None,
    lingua: str = "pt",
    profundidade_max: int = 3,
) -> dict:
    """
    Varre uma pasta do computador e cria/atualiza notas no Obsidian
    para cada subpasta relevante encontrada.

    Retorna: {"notas_criadas": N, "resumo_voz": "..."}
    """
    vault = vault or get_vault()
    if not vault:
        return {
            "notas_criadas": 0,
            "resumo_voz": {
                "pt": "Vault Obsidian não encontrado.",
                "en": "Obsidian vault not found.",
            }.get(lingua, "Vault not found."),
        }

    if not pasta_origem.is_dir():
        return {
            "notas_criadas": 0,
            "resumo_voz": {
                "pt": f"Pasta '{pasta_origem}' não encontrada.",
                "en": f"Folder '{pasta_origem}' not found.",
            }.get(lingua, f"Folder not found."),
        }

    notas_criadas = 0
    pasta_vault_alvo = vault / "Projetos" / pasta_origem.name
    pasta_vault_alvo.mkdir(parents=True, exist_ok=True)

    def _varrer(pasta: Path, nivel: int = 0):
        nonlocal notas_criadas
        if nivel > profundidade_max:
            return

        try:
            itens = list(pasta.iterdir())
        except PermissionError:
            return

        arquivos = [i for i in itens if i.is_file() and not i.name.startswith(".")]
        subpastas = [i for i in itens if i.is_dir() and not i.name.startswith(".")]

        if not arquivos and not subpastas:
            return

        # Cria nota de índice para a pasta
        titulo_nota = f"📁 {pasta.name}"
        ts = datetime.now().strftime("%Y-%m-%d")

        linhas = [f"# {pasta.name}\n", f"*Escaneado em {ts} pelo R.O.N.Y*\n\n"]

        if subpastas:
            linhas.append("## Subpastas\n")
            for sp in sorted(subpastas, key=lambda x: x.name)[:20]:
                linhas.append(f"- [[📁 {sp.name}]]")
            linhas.append("")

        if arquivos:
            linhas.append("## Arquivos\n")
            by_ext: dict[str, list] = {}
            for arq in sorted(arquivos, key=lambda x: x.name)[:50]:
                ext = arq.suffix.lower() or "(sem extensão)"
                by_ext.setdefault(ext, []).append(arq.name)
            for ext, nomes in sorted(by_ext.items()):
                linhas.append(f"### {ext}")
                for nome in nomes[:15]:
                    linhas.append(f"- {nome}")
                linhas.append("")

        conteudo = "\n".join(linhas)
        pasta_relativa = pasta.relative_to(pasta_origem.parent) if nivel > 0 else Path(pasta.name)
        subpasta_vault = pasta_vault_alvo / Path(*pasta_relativa.parts[1:]) if nivel > 0 else pasta_vault_alvo
        subpasta_vault.mkdir(parents=True, exist_ok=True)

        nota_path = subpasta_vault / f"{_sanitizar(pasta.name)}.md"
        try:
            nota_path.write_text(
                f"""---
title: "{pasta.name}"
created: "{ts}"
tags:
  - rony
  - auto
  - pasta
path: "{str(pasta)}"
---

""" + conteudo,
                encoding="utf-8",
            )
            notas_criadas += 1
        except Exception as e:
            print(f"[OBSIDIAN] Erro ao criar nota de pasta: {e}")

        for sp in subpastas[:10]:
            _varrer(sp, nivel + 1)

    _varrer(pasta_origem)

    resumo = {
        "pt": f"Organizei '{pasta_origem.name}' no Obsidian. {notas_criadas} notas criadas em '{pasta_vault_alvo.name}'.",
        "en": f"Organized '{pasta_origem.name}' in Obsidian. {notas_criadas} notes created.",
    }.get(lingua, f"Organized. {notas_criadas} notes created.")

    return {"notas_criadas": notas_criadas, "resumo_voz": resumo}


# ═══════════════════════════════════════════════════════════════
#  CRIAÇÃO RÁPIDA DE NOTA POR VOZ
# ═══════════════════════════════════════════════════════════════

def _extrair_titulo_e_conteudo(instrucao: str) -> tuple[str, str]:
    """Extrai título e conteúdo de uma instrução de voz."""
    instrucao = instrucao.strip()

    # Padrões: "cria uma nota sobre X", "anota que Y", "salva a nota Z"
    padroes_titulo = [
        r"(?:cria|crie|criar|salva|salvar|faz|fazer)\s+(?:uma?\s+)?nota\s+(?:sobre|de|para|chamada?|intitulada?)?\s+[\"']?(.+?)[\"']?\s*(?:com|sobre|dizendo|que diz)?",
        r"anota\s+(?:que\s+)?(.+)",
        r"lembra\s+(?:de\s+)?(?:que\s+)?(.+)",
        r"nota\s+(?:sobre\s+)?(.+)",
    ]
    for p in padroes_titulo:
        m = re.search(p, instrucao, re.IGNORECASE)
        if m:
            titulo = m.group(1).strip()[:60]
            # Conteúdo é o restante da instrução
            conteudo_match = re.search(r"(?:dizendo|que diz|conteudo|conteúdo|com o texto|com)\s+[\"']?(.+)[\"']?", instrucao, re.IGNORECASE)
            conteudo = conteudo_match.group(1) if conteudo_match else ""
            return titulo, conteudo

    # Fallback: título = primeiras palavras da instrução
    palavras = instrucao.split()[:6]
    titulo = " ".join(palavras)
    return titulo, instrucao


def criar_nota_por_voz(
    instrucao: str,
    vault: Path = None,
    lingua: str = "pt",
    tags_extra: list[str] = None,
) -> str:
    """
    Cria uma nota Obsidian a partir de uma instrução de voz.
    Retorna mensagem para falar.
    """
    vault = vault or get_vault()
    if not vault:
        return {
            "pt": "Vault Obsidian não configurado. Instale o Obsidian e crie um vault, ou defina OBSIDIAN_VAULT_PATH no .env.",
            "en": "Obsidian vault not configured.",
        }.get(lingua, "Vault not configured.")

    titulo, conteudo = _extrair_titulo_e_conteudo(instrucao)
    tags = ["rony", "voz"] + (tags_extra or [])

    # Detecta pasta baseada em palavras-chave
    pasta = ""
    kw_pasta = {
        "trabalho": "Trabalho", "work": "Trabalho",
        "pessoal": "Pessoal", "personal": "Pessoal",
        "projeto": "Projetos", "project": "Projetos",
        "ideia": "Ideias", "idea": "Ideias",
        "reunião": "Reunioes", "reuniao": "Reunioes", "meeting": "Reunioes",
        "tarefa": "Tarefas", "task": "Tarefas", "todo": "Tarefas",
        "compra": "Compras", "shopping": "Compras",
        "receita": "Receitas", "recipe": "Receitas",
    }
    for kw, nome_pasta in kw_pasta.items():
        if kw in instrucao.lower():
            pasta = nome_pasta
            break

    caminho = criar_nota(titulo, conteudo, tags=tags, pasta=pasta, vault=vault)
    if caminho:
        pasta_info = f" na pasta {pasta}" if pasta else ""
        return {
            "pt": f"Nota '{titulo}' criada no Obsidian{pasta_info}.",
            "en": f"Note '{titulo}' created in Obsidian{' in ' + pasta if pasta else ''}.",
        }.get(lingua, f"Note '{titulo}' created.")
    return {
        "pt": "Não consegui criar a nota no Obsidian.",
        "en": "Couldn't create the note in Obsidian.",
    }.get(lingua, "Failed to create note.")


# ═══════════════════════════════════════════════════════════════
#  INTERFACE DE VOZ — DETECTAR INTENÇÃO OBSIDIAN
# ═══════════════════════════════════════════════════════════════

_TRIGGERS_CRIAR_NOTA = {
    "cria uma nota", "crie uma nota", "criar uma nota", "faz uma nota",
    "anota", "anotar", "salva uma nota", "salvar uma nota",
    "nota no obsidian", "cria no obsidian", "adiciona ao obsidian",
    "lembra disso no obsidian", "registra no obsidian",
    "create a note", "note this", "add to obsidian",
}

_TRIGGERS_BUSCAR_NOTA = {
    "busca a nota", "busca no obsidian", "procura a nota", "procura no obsidian",
    "encontra a nota", "onde está a nota", "abre a nota",
    "search note", "find note",
}

_TRIGGERS_ORGANIZAR = {
    "organiza no obsidian", "organiza o obsidian", "sincroniza com obsidian",
    "mapeia para o obsidian", "cria estrutura no obsidian",
    "organize in obsidian", "sync obsidian",
}

_TRIGGERS_STATUS = {
    "status do obsidian", "obsidian ok", "quantas notas",
    "vault status", "obsidian status",
}


def detectar_acao_obsidian(texto: str) -> Optional[str]:
    """
    Retorna a ação Obsidian detectada:
    'criar_nota' | 'buscar_nota' | 'organizar' | 'status' | None
    """
    t = texto.lower().strip()
    if any(k in t for k in _TRIGGERS_CRIAR_NOTA):
        return "criar_nota"
    if any(k in t for k in _TRIGGERS_BUSCAR_NOTA):
        return "buscar_nota"
    if any(k in t for k in _TRIGGERS_ORGANIZAR):
        return "organizar"
    if any(k in t for k in _TRIGGERS_STATUS):
        return "status"
    return None
