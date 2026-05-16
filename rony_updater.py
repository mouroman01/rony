# ============================================================
#  rony_updater.py — Auto-update via GitHub Releases
#
#  Fluxo:
#    1. Lê update_manifest.json do repositório GitHub
#    2. Compara versão remota com versão local
#    3. Se nova versão: notifica via toast + diálogo PyWebView
#    4. Se aceito: baixa instalador em AppData/updates/
#    5. Executa instalador silencioso e encerra o Rony
#
#  update_manifest.json (hosted no GitHub raw):
#    {
#      "latest_version": "1.0.1",
#      "download_url": "https://github.com/.../Rony_Setup_1.0.1.exe",
#      "notes": "O que mudou nesta versão.",
#      "mandatory": false
#    }
# ============================================================

import json
import os
import threading
import time
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

from rony_paths import UPDATES_DIR

# ── URL do manifesto (raw GitHub) ─────────────────────────────
MANIFEST_URL = (
    "https://raw.githubusercontent.com/mouroman01/rony/main/update_manifest.json"
)
TIMEOUT_HTTP = 12  # segundos


# ═══════════════════════════════════════════════════════════════
#  UTILITÁRIOS DE VERSÃO
# ═══════════════════════════════════════════════════════════════

def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in str(v).strip().split("."))
    except Exception:
        return (0,)


def _e_mais_novo(remoto: str, atual: str) -> bool:
    return _version_tuple(remoto) > _version_tuple(atual)


# ═══════════════════════════════════════════════════════════════
#  LEITURA DO MANIFESTO
# ═══════════════════════════════════════════════════════════════

def _ler_manifesto() -> dict | None:
    try:
        req = urllib.request.Request(
            MANIFEST_URL,
            headers={"User-Agent": "Rony-Updater/1.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_HTTP) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[UPDATE] Sem conexao ou URL invalida: {e.reason}")
        return None
    except Exception as e:
        print(f"[UPDATE] Falha ao ler manifesto: {e}")
        return None


def _formatar_notas_update(manifesto: dict) -> str:
    """Monta um texto curto e legivel com o que sera atualizado."""
    notas = str(manifesto.get("notes", "")).strip()
    mudancas = manifesto.get("changes", [])

    linhas: list[str] = []
    if isinstance(mudancas, list):
        for item in mudancas:
            item_txt = str(item).strip()
            if item_txt:
                linhas.append(item_txt)
    elif isinstance(mudancas, str) and mudancas.strip():
        linhas.extend(l.strip() for l in mudancas.splitlines() if l.strip())

    if not linhas and notas:
        linhas.extend(l.strip(" -") for l in notas.splitlines() if l.strip())

    if linhas:
        return "\n".join(f"- {linha}" for linha in linhas[:8])

    return "- Melhorias e correcoes internas do R.O.N.Y."


def _resumir_notas_update(texto: str, limite: int = 160) -> str:
    texto = " ".join(l.strip(" -") for l in texto.splitlines() if l.strip())
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "..."


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD DO INSTALADOR
# ═══════════════════════════════════════════════════════════════

def _baixar_installer(versao: str, url: str) -> Path | None:
    destino = UPDATES_DIR / f"Rony_Setup_{versao}.exe"
    if destino.exists() and destino.stat().st_size > 100_000:
        print(f"[UPDATE] Instalador ja baixado: {destino.name}")
        return destino
    try:
        print(f"[UPDATE] Baixando Rony v{versao}...")

        def _progresso(bloco, tam_bloco, tam_total):
            if tam_total > 0:
                pct = min(100, bloco * tam_bloco * 100 // tam_total)
                print(f"[UPDATE] Download: {pct}%", end="\r")

        urllib.request.urlretrieve(url, destino, reporthook=_progresso)
        print(f"\n[UPDATE] Download concluido: {destino.name}")
        return destino
    except Exception as e:
        print(f"[UPDATE] Falha no download: {e}")
        if destino.exists():
            destino.unlink()
        return None


# ═══════════════════════════════════════════════════════════════
#  INSTALAÇÃO SILENCIOSA
# ═══════════════════════════════════════════════════════════════

def _instalar(installer: Path) -> None:
    """Executa o instalador Inno Setup em modo silencioso e encerra o Rony."""
    print(f"[UPDATE] Instalando {installer.name} ...")
    try:
        subprocess.Popen(
            [str(installer), "/VERYSILENT", "/NORESTART"],
            shell=False,
            close_fds=True,
        )
    except Exception as e:
        print(f"[UPDATE] Falha ao executar instalador: {e}")
        return
    time.sleep(1)
    print("[UPDATE] Encerrando Rony para concluir instalacao...")
    os._exit(0)


# ═══════════════════════════════════════════════════════════════
#  ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def verificar_atualizacao(
    versao_atual: str,
    janela_pywebview=None,
    notif_fn=None,
    ws_broadcast_fn=None,
) -> None:
    """
    Verifica atualizações em thread background. Não bloqueia.

    Args:
        versao_atual:     versão atual do Rony (ex: "1.0.0")
        janela_pywebview: objeto window do pywebview (confirm() nativo)
        notif_fn:         função notificacao(titulo, msg, duration) do executor_module
        ws_broadcast_fn:  coroutine ou callable para broadcast WebSocket ao frontend
    """

    def _tarefa():
        # Aguarda 8s após o boot para não atrasar o startup
        time.sleep(8)

        manifesto = _ler_manifesto()
        if not manifesto:
            return

        versao_nova  = manifesto.get("latest_version", "").strip()
        url_download = manifesto.get("download_url",   "").strip()
        notas        = manifesto.get("notes", "").strip()
        obrigatoria  = bool(manifesto.get("mandatory", False))
        detalhes     = _formatar_notas_update(manifesto)

        if not versao_nova:
            return

        if not _e_mais_novo(versao_nova, versao_atual):
            print(f"[UPDATE] Rony esta atualizado (v{versao_atual}).")
            return

        print(f"[UPDATE] Nova versao disponivel: v{versao_nova}")

        # ── Toast desktop ─────────────────────────────────────
        if notif_fn:
            try:
                notif_fn(
                    "Rony — Atualizacao disponivel",
                    f"v{versao_nova} esta pronta: {_resumir_notas_update(detalhes)}",
                    8,
                )
            except Exception:
                pass

        # ── Notifica frontend via WebSocket ───────────────────
        if ws_broadcast_fn:
            try:
                payload = json.dumps({
                    "action"  : "update_available",
                    "versao"  : versao_nova,
                    "notas"   : notas,
                    "detalhes": detalhes,
                    "changes" : manifesto.get("changes", []),
                    "mandatory": obrigatoria,
                    "download_url": url_download,
                })
                result = ws_broadcast_fn(payload)
                # Se retornou coroutine (chamada assíncrona), descarta sem await
                # para evitar RuntimeWarning — o broadcast é best-effort
                if hasattr(result, "close"):
                    result.close()
            except Exception:
                pass

        # ── Sem URL — só notifica, não baixa ──────────────────
        if not url_download:
            print("[UPDATE] Sem URL de download configurada — notificacao enviada.")
            return

        # ── Confirmação obrigatória antes de qualquer download ────
        # Nunca baixa/instala sem consentimento explícito do usuário.
        confirmado = False

        if obrigatoria:
            # Atualização crítica: prossegue sem diálogo
            confirmado = True
            print(f"[UPDATE] Atualizacao obrigatoria v{versao_nova} — iniciando...")
        elif janela_pywebview:
            try:
                msg_js = json.dumps(
                    f"Nova versao do Rony disponivel!\n\n"
                    f"Versao atual : {versao_atual}\n"
                    f"Nova versao  : {versao_nova}\n\n"
                    f"O que sera atualizado:\n{detalhes}\n\n"
                    f"Deseja atualizar agora?"
                )
                aceite = janela_pywebview.evaluate_js(f"confirm({msg_js})")
                confirmado = bool(aceite)
                if not confirmado:
                    print("[UPDATE] Atualizacao adiada pelo usuario.")
                    return
            except Exception as e:
                print(f"[UPDATE] Dialogo PyWebView falhou: {e} — atualizacao nao sera instalada.")
                return
        else:
            # Modo navegador: WebSocket já notificou o frontend.
            # Aguarda ação do usuário pela interface — não baixa automaticamente.
            print("[UPDATE] Notificacao enviada ao frontend via WebSocket — aguardando confirmacao do usuario.")
            return

        # ── Download + instalação ─────────────────────────────
        if confirmado:
            installer = _baixar_installer(versao_nova, url_download)
            if installer:
                _instalar(installer)

    t = threading.Thread(target=_tarefa, daemon=True, name="rony-updater")
    t.start()
