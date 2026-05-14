# ============================================================
#  file_manager.py — Acesso completo ao sistema de arquivos
#  R.O.N.Y — Navegar, listar, abrir, ler, pesquisar
#  Aliases multilíngues + navegação natural por voz
# ============================================================

import os
import subprocess
import shutil
import stat
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Pasta atual de navegação (estado) ────────────────────────
_pasta_atual: Path = Path.home()

# ── Aliases de pastas (multilíngue) ──────────────────────────
ALIAS_DOSSIERS: dict[str, Path] = {
    # PT
    "área de trabalho" : Path.home() / "Desktop",
    "area de trabalho" : Path.home() / "Desktop",
    "desktop"          : Path.home() / "Desktop",
    "transferências"   : Path.home() / "Downloads",
    "transferencias"   : Path.home() / "Downloads",
    "downloads"        : Path.home() / "Downloads",
    "documentos"       : Path.home() / "Documents",
    "documents"        : Path.home() / "Documents",
    "imagens"          : Path.home() / "Pictures",
    "fotos"            : Path.home() / "Pictures",
    "pictures"         : Path.home() / "Pictures",
    "videos"           : Path.home() / "Videos",
    "músicas"          : Path.home() / "Music",
    "musicas"          : Path.home() / "Music",
    "music"            : Path.home() / "Music",
    "projetos"         : Path.home() / "Documents",
    "rony"             : Path("C:/Projetos/Rony"),

    # FR
    "bureau"           : Path.home() / "Desktop",
    "téléchargements"  : Path.home() / "Downloads",
    "telechargements"  : Path.home() / "Downloads",
    "images"           : Path.home() / "Pictures",
    "photos"           : Path.home() / "Pictures",
    "vidéos"           : Path.home() / "Videos",
    "musique"          : Path.home() / "Music",

    # EN
    "home"             : Path.home(),
    "inicio"           : Path.home(),
    "início"           : Path.home(),

    # ES
    "escritorio"       : Path.home() / "Desktop",
    "descargas"        : Path.home() / "Downloads",
    "imágenes"         : Path.home() / "Pictures",
    "imagenes"         : Path.home() / "Pictures",

    # DE
    "schreibtisch"     : Path.home() / "Desktop",
    "bilder"           : Path.home() / "Pictures",
    "musik"            : Path.home() / "Music",

    # Caminhos raiz úteis
    "c:"               : Path("C:/"),
    "raiz"             : Path("C:/"),
    "root"             : Path("C:/"),
    "program files"    : Path("C:/Program Files"),
    "usuário"          : Path.home(),
    "usuario"          : Path.home(),
    "user"             : Path.home(),
}

# ── Extensões por categoria ───────────────────────────────────
EXTENSOES_TEXTO   = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                     ".json", ".xml", ".csv", ".log", ".ini", ".yaml", ".yml",
                     ".env", ".bat", ".sh", ".sql", ".toml", ".cfg"}
EXTENSOES_IMAGEM  = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff"}
EXTENSOES_VIDEO   = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
EXTENSOES_AUDIO   = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
EXTENSOES_ARQUIVO = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}
EXTENSOES_DOC     = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods"}
EXTENSOES_CODIGO  = {".py", ".js", ".ts", ".java", ".cs", ".cpp", ".c", ".go",
                     ".rs", ".php", ".rb", ".swift", ".kt", ".dart", ".r"}


# ═══════════════════════════════════════════════════════════════
#  RESOLUÇÃO DE CAMINHO
# ═══════════════════════════════════════════════════════════════

def resoudre_chemin(nome: str) -> Optional[Path]:
    """Resolve um nome/alias em Path absoluto."""
    if not nome:
        return None
    nome_lower = nome.strip().lower()

    # 1. Alias direto
    if nome_lower in ALIAS_DOSSIERS:
        return ALIAS_DOSSIERS[nome_lower]

    # 2. Alias com sub-caminho ("desktop/projeto")
    for alias, base in ALIAS_DOSSIERS.items():
        if nome_lower.startswith(alias + "/") or nome_lower.startswith(alias + "\\"):
            sub = nome[len(alias):].lstrip("/\\")
            return base / sub

    # 3. Caminho absoluto
    p = Path(nome)
    if p.is_absolute():
        return p

    # 4. Relativo à pasta atual
    candidato = _pasta_atual / nome
    if candidato.exists():
        return candidato

    # 5. Busca em pastas comuns
    for base in [Path.home(), Path.home() / "Desktop",
                 Path.home() / "Documents", Path.home() / "Downloads"]:
        c = base / nome
        if c.exists():
            return c

    return None


# ═══════════════════════════════════════════════════════════════
#  NAVEGAÇÃO
# ═══════════════════════════════════════════════════════════════

def get_pasta_atual() -> Path:
    return _pasta_atual


def navegar_para(destino: str) -> tuple[bool, Path]:
    """Navega para uma pasta. Retorna (sucesso, caminho)."""
    global _pasta_atual
    alvo = resoudre_chemin(destino)
    if not alvo:
        return False, _pasta_atual
    if alvo.is_dir():
        _pasta_atual = alvo
        return True, alvo
    if alvo.is_file():
        _pasta_atual = alvo.parent
        return True, alvo.parent
    return False, _pasta_atual


def voltar_pasta() -> Path:
    """Volta para a pasta pai."""
    global _pasta_atual
    if _pasta_atual.parent != _pasta_atual:
        _pasta_atual = _pasta_atual.parent
    return _pasta_atual


# ═══════════════════════════════════════════════════════════════
#  LISTAGEM
# ═══════════════════════════════════════════════════════════════

def listar_pasta(caminho: Path = None, max_items: int = 20,
                 so_arquivos: bool = False, so_pastas: bool = False,
                 ordenar: str = "nome") -> list[dict]:
    """Lista o conteúdo de uma pasta com metadados."""
    alvo = caminho or _pasta_atual
    try:
        entradas = []
        for e in alvo.iterdir():
            try:
                if so_arquivos and not e.is_file():
                    continue
                if so_pastas and not e.is_dir():
                    continue
                st = e.stat()
                entradas.append({
                    "nome"     : e.name,
                    "tipo"     : "pasta" if e.is_dir() else "arquivo",
                    "extensao" : e.suffix.lower() if e.is_file() else "",
                    "categoria": categoria_arquivo(e),
                    "tamanho"  : st.st_size if e.is_file() else None,
                    "modificado": st.st_mtime,
                    "caminho"  : str(e),
                })
            except (PermissionError, OSError):
                continue

        chaves = {"nome": lambda x: x["nome"].lower(),
                  "data": lambda x: x["modificado"],
                  "tamanho": lambda x: x["tamanho"] or 0}
        entradas.sort(key=chaves.get(ordenar, chaves["nome"]))
        return entradas[:max_items]
    except PermissionError:
        return []


def resumo_pasta_voz(caminho: Path = None, lingua: str = "pt") -> str:
    """Retorna um resumo falado do conteúdo de uma pasta."""
    alvo = caminho or _pasta_atual
    items = listar_pasta(alvo, max_items=50)
    pastas   = [i for i in items if i["tipo"] == "pasta"]
    arquivos = [i for i in items if i["tipo"] == "arquivo"]

    # Agrupa por categoria
    cats: dict[str, int] = {}
    for a in arquivos:
        c = a["categoria"]
        cats[c] = cats.get(c, 0) + 1

    templates = {
        "pt": (
            f"A pasta '{alvo.name}' tem {len(pastas)} subpasta(s) e {len(arquivos)} arquivo(s)."
            + (f" Categorias: " + ", ".join(f"{v} {k}(s)" for k, v in cats.items()) if cats else "")
        ),
        "fr": (
            f"Le dossier '{alvo.name}' contient {len(pastas)} sous-dossier(s) et {len(arquivos)} fichier(s)."
        ),
        "en": (
            f"The folder '{alvo.name}' has {len(pastas)} subfolder(s) and {len(arquivos)} file(s)."
            + (f" Types: " + ", ".join(f"{v} {k}(s)" for k, v in cats.items()) if cats else "")
        ),
        "es": (
            f"La carpeta '{alvo.name}' tiene {len(pastas)} subcarpeta(s) y {len(arquivos)} archivo(s)."
        ),
        "de": (
            f"Der Ordner '{alvo.name}' hat {len(pastas)} Unterordner und {len(arquivos)} Datei(en)."
        ),
    }
    return templates.get(lingua, templates["en"])


def listar_arquivos_recentes(pasta: Path = None, n: int = 5, lingua: str = "pt") -> str:
    """Retorna os n arquivos mais recentes como texto falado."""
    base = pasta or Path.home() / "Desktop"
    try:
        arquivos = [p for p in base.iterdir() if p.is_file()]
        recentes = sorted(arquivos, key=lambda p: p.stat().st_mtime, reverse=True)[:n]
        if not recentes:
            msgs = {"pt": "Nenhum arquivo encontrado.", "fr": "Aucun fichier trouvé.",
                    "en": "No files found.", "es": "No se encontraron archivos.", "de": "Keine Dateien gefunden."}
            return msgs.get(lingua, msgs["en"])
        nomes = ", ".join(p.name for p in recentes)
        prefixos = {
            "pt": f"Os {len(recentes)} arquivos mais recentes em '{base.name}': {nomes}.",
            "fr": f"Les {len(recentes)} fichiers les plus récents dans '{base.name}' : {nomes}.",
            "en": f"The {len(recentes)} most recent files in '{base.name}': {nomes}.",
            "es": f"Los {len(recentes)} archivos más recientes en '{base.name}': {nomes}.",
            "de": f"Die {len(recentes)} neuesten Dateien in '{base.name}': {nomes}.",
        }
        return prefixos.get(lingua, prefixos["en"])
    except Exception as e:
        return str(e)


# ═══════════════════════════════════════════════════════════════
#  ABERTURA DE ARQUIVOS / PASTAS
# ═══════════════════════════════════════════════════════════════

def abrir_arquivo(caminho: Path) -> str:
    """Abre um arquivo com o programa padrão do Windows."""
    try:
        os.startfile(str(caminho))
        return f"Abrindo {caminho.name}."
    except Exception as e:
        return f"Não consegui abrir {caminho.name}: {e}"


def abrir_pasta(caminho: Path) -> str:
    """Abre uma pasta no Explorador de Arquivos."""
    try:
        subprocess.Popen(f'explorer "{caminho}"', shell=True)
        return f"Abrindo pasta {caminho.name} no explorador."
    except Exception as e:
        return f"Erro ao abrir pasta: {e}"


def ouvrir_fichier(caminho: Path) -> str:
    return abrir_arquivo(caminho)

def ouvrir_dossier(caminho: Path) -> str:
    return abrir_pasta(caminho)

def fichiers_recents(pasta: Path = None, n: int = 10) -> list[Path]:
    base = pasta or Path.home() / "Desktop"
    try:
        return sorted([p for p in base.iterdir() if p.is_file()],
                      key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  LEITURA DE CONTEÚDO
# ═══════════════════════════════════════════════════════════════

def ler_arquivo_texto(caminho: Path, max_chars: int = 3000) -> str:
    """Lê o conteúdo de um arquivo de texto para leitura em voz alta."""
    if caminho.suffix.lower() not in EXTENSOES_TEXTO:
        return f"Este tipo de arquivo ({caminho.suffix}) não pode ser lido diretamente."
    try:
        conteudo = caminho.read_text(encoding="utf-8", errors="replace")
        if len(conteudo) > max_chars:
            return conteudo[:max_chars] + f"\n\n[... arquivo continua — {len(conteudo) - max_chars} caracteres omitidos]"
        return conteudo
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"


# ═══════════════════════════════════════════════════════════════
#  PESQUISA
# ═══════════════════════════════════════════════════════════════

def pesquisar_arquivos(consulta: str, pasta: Path = None,
                       extensao: str = None, max_resultados: int = 10) -> list[Path]:
    """Pesquisa recursiva de arquivos por nome."""
    base = pasta or Path.home()
    resultados = []
    try:
        for p in base.rglob(f"*{consulta}*"):
            if extensao and p.suffix.lower() != extensao.lower():
                continue
            if p.is_file():
                resultados.append(p)
                if len(resultados) >= max_resultados:
                    break
    except PermissionError:
        pass
    return resultados


def pesquisar_e_falar(consulta: str, pasta: Path = None, lingua: str = "pt") -> str:
    """Pesquisa arquivos e retorna resultado falado."""
    resultados = pesquisar_arquivos(consulta, pasta)
    if not resultados:
        msgs = {
            "pt": f"Não encontrei nenhum arquivo com '{consulta}'.",
            "fr": f"Aucun fichier trouvé avec '{consulta}'.",
            "en": f"No file found matching '{consulta}'.",
            "es": f"No encontré ningún archivo con '{consulta}'.",
            "de": f"Keine Datei mit '{consulta}' gefunden.",
        }
        return msgs.get(lingua, msgs["en"])
    nomes = ", ".join(p.name for p in resultados[:5])
    prefixos = {
        "pt": f"Encontrei {len(resultados)} arquivo(s): {nomes}.",
        "fr": f"J'ai trouvé {len(resultados)} fichier(s) : {nomes}.",
        "en": f"Found {len(resultados)} file(s): {nomes}.",
        "es": f"Encontré {len(resultados)} archivo(s): {nomes}.",
        "de": f"Gefunden: {len(resultados)} Datei(en): {nomes}.",
    }
    return prefixos.get(lingua, prefixos["en"])


# ═══════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════

def formatar_tamanho(octets: int) -> str:
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if abs(octets) < 1024.0:
            return f"{octets:.1f} {unidade}"
        octets /= 1024.0
    return f"{octets:.1f} PB"


def categoria_arquivo(caminho: Path) -> str:
    ext = caminho.suffix.lower()
    if ext in EXTENSOES_IMAGEM  : return "imagem"
    if ext in EXTENSOES_VIDEO   : return "vídeo"
    if ext in EXTENSOES_AUDIO   : return "áudio"
    if ext in EXTENSOES_CODIGO  : return "código"
    if ext in EXTENSOES_TEXTO   : return "texto"
    if ext in EXTENSOES_ARQUIVO : return "arquivo compactado"
    if ext in EXTENSOES_DOC     : return "documento"
    return "arquivo"


def info_arquivo_voz(caminho: Path, lingua: str = "pt") -> str:
    """Retorna informações de um arquivo como texto falado."""
    try:
        st = caminho.stat()
        tamanho = formatar_tamanho(st.st_size)
        data    = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y às %H:%M")
        cat     = categoria_arquivo(caminho)
        templates = {
            "pt": f"{caminho.name}: {cat}, {tamanho}, modificado em {data}.",
            "fr": f"{caminho.name} : {cat}, {tamanho}, modifié le {data}.",
            "en": f"{caminho.name}: {cat}, {tamanho}, last modified {data}.",
            "es": f"{caminho.name}: {cat}, {tamanho}, modificado el {data}.",
            "de": f"{caminho.name}: {cat}, {tamanho}, zuletzt geändert am {data}.",
        }
        return templates.get(lingua, templates["en"])
    except Exception as e:
        return str(e)


# Aliases para retrocompatibilidade com main.py
def lister_dossier(caminho: Path, max_items: int = 20) -> list[dict]:
    return listar_pasta(caminho, max_items)

def fichiers_recents(pasta: Path = None, n: int = 10) -> list[Path]:
    base = pasta or Path.home() / "Desktop"
    try:
        return sorted([p for p in base.iterdir() if p.is_file()],
                      key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  MAPEAMENTO COMPLETO DE PASTA
# ═══════════════════════════════════════════════════════════════

def mapear_pasta_completo(caminho: Path, lingua: str = "pt") -> dict:
    """
    Mapeia recursivamente uma pasta inteira e retorna estrutura completa.
    Ideal para vaults Obsidian e pastas de projeto.
    Retorna dict com: arvore, estatisticas, resumo_voz, lista_arquivos.
    """
    stats: dict[str, int] = {}
    lista_arquivos: list[dict] = []
    total_tamanho = 0
    total_pastas = 0

    def _varrer(pasta: Path, nivel: int = 0) -> list[dict]:
        nonlocal total_tamanho, total_pastas
        nos = []
        try:
            entradas = sorted(pasta.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return nos
        for e in entradas:
            try:
                if e.is_dir():
                    total_pastas += 1
                    filhos = _varrer(e, nivel + 1)
                    nos.append({"nome": e.name, "tipo": "pasta", "nivel": nivel, "filhos": filhos})
                elif e.is_file():
                    st = e.stat()
                    cat = categoria_arquivo(e)
                    ext = e.suffix.lower()
                    stats[cat] = stats.get(cat, 0) + 1
                    total_tamanho += st.st_size
                    info = {
                        "nome": e.name,
                        "tipo": "arquivo",
                        "categoria": cat,
                        "extensao": ext,
                        "tamanho": st.st_size,
                        "modificado": datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y"),
                        "caminho": str(e),
                        "nivel": nivel,
                    }
                    nos.append(info)
                    lista_arquivos.append(info)
            except (PermissionError, OSError):
                continue
        return nos

    arvore = _varrer(caminho)
    total_arquivos = len(lista_arquivos)
    tamanho_fmt = formatar_tamanho(total_tamanho)

    # Resumo falado
    cats_str = ", ".join(f"{v} {k}(s)" for k, v in sorted(stats.items(), key=lambda x: -x[1]))
    resumos = {
        "pt": (
            f"A pasta '{caminho.name}' tem {total_pastas} subpasta(s) e {total_arquivos} arquivo(s), "
            f"ocupando {tamanho_fmt} no total."
            + (f" Tipos: {cats_str}." if cats_str else "")
        ),
        "en": (
            f"Folder '{caminho.name}' has {total_pastas} subfolder(s) and {total_arquivos} file(s), "
            f"totaling {tamanho_fmt}."
            + (f" Types: {cats_str}." if cats_str else "")
        ),
        "fr": (
            f"Le dossier '{caminho.name}' contient {total_pastas} sous-dossier(s) et {total_arquivos} fichier(s), "
            f"pour un total de {tamanho_fmt}."
        ),
    }

    return {
        "arvore": arvore,
        "lista_arquivos": lista_arquivos,
        "estatisticas": stats,
        "total_arquivos": total_arquivos,
        "total_pastas": total_pastas,
        "tamanho_total": total_tamanho,
        "tamanho_fmt": tamanho_fmt,
        "resumo_voz": resumos.get(lingua, resumos["pt"]),
        "caminho": str(caminho),
    }


# ═══════════════════════════════════════════════════════════════
#  ABERTURA DE QUALQUER ARQUIVO
# ═══════════════════════════════════════════════════════════════

def abrir_qualquer_arquivo(nome: str) -> str:
    """
    Tenta abrir qualquer arquivo por nome, caminho parcial ou extensão.
    Busca em Desktop, Documentos, Downloads, pasta atual e caminho absoluto.
    """
    # 1. Caminho absoluto direto
    p = Path(nome)
    if p.is_absolute() and p.exists():
        return abrir_arquivo(p)

    # 2. Alias conhecido
    resolvido = resoudre_chemin(nome)
    if resolvido:
        if resolvido.is_file():
            return abrir_arquivo(resolvido)
        if resolvido.is_dir():
            return abrir_pasta(resolvido)

    # 3. Busca por nome nas pastas mais comuns
    bases = [
        _pasta_atual,
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
        Path.home(),
    ]
    for base in bases:
        try:
            for candidato in base.rglob(f"*{nome}*"):
                if candidato.is_file():
                    return abrir_arquivo(candidato)
        except PermissionError:
            continue

    # 4. Busca com extensões comuns se não tem extensão
    if "." not in nome:
        extensoes = [".pdf", ".docx", ".xlsx", ".txt", ".md", ".pptx",
                     ".mp4", ".mp3", ".jpg", ".png"]
        for base in bases:
            for ext in extensoes:
                candidato = base / f"{nome}{ext}"
                if candidato.exists():
                    return abrir_arquivo(candidato)

    return f"Não encontrei o arquivo '{nome}'. Verifique o nome ou me diga o caminho completo."
