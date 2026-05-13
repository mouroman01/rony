# ============================================================
#  rony_paths.py — Caminhos centralizados do Rony
#
#  Separa dados do usuário (AppData) do código do programa.
#
#  Programa (RONY_DIR):  código, frontend, .env
#  Dados (APPDATA_DIR):  memória, histórico, config, capturas,
#                        rostos, logs, updates
# ============================================================

import os
import shutil
from pathlib import Path

# ── Diretório do programa (onde o código está instalado) ──────
RONY_DIR = Path(__file__).parent

# ── Diretório de dados do usuário ─────────────────────────────
#    Windows: %LOCALAPPDATA%\Rony\
#    Fallback: ~/AppData/Local/Rony/
_local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
APPDATA_DIR  = Path(_local) / "Rony"

DATA_DIR     = APPDATA_DIR / "data"       # JSON de memória e config
LOG_DIR      = APPDATA_DIR / "logs"       # logs de execução
CAPTURES_DIR = APPDATA_DIR / "captures"   # screenshots e capturas
ROSTOS_DIR   = DATA_DIR    / "rostos"     # banco de rostos LBPH
UPDATES_DIR  = APPDATA_DIR / "updates"    # instaladores de atualização

# ── Arquivos de dados ─────────────────────────────────────────
CONFIG_FILE     = DATA_DIR / "rony_config.json"
MEMOIRE_FILE    = DATA_DIR / "rony_memoire.json"
HISTORIQUE_FILE = DATA_DIR / "rony_historique.json"
LOG_EXEC_FILE   = LOG_DIR  / "executor_log.jsonl"


# ═══════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════

def _criar_estrutura() -> None:
    """Cria a estrutura de diretórios no AppData."""
    for d in [DATA_DIR, LOG_DIR, CAPTURES_DIR, ROSTOS_DIR, UPDATES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _migrar_dados_legados() -> None:
    """
    Migra dados da pasta do programa para AppData (execução única).
    Copia sem apagar os originais para garantir segurança.
    """
    # Arquivos JSON simples
    migracoes = [
        (RONY_DIR / "rony_config.json",     CONFIG_FILE),
        (RONY_DIR / "rony_memoire.json",    MEMOIRE_FILE),
        (RONY_DIR / "rony_historique.json", HISTORIQUE_FILE),
    ]
    for origem, destino in migracoes:
        if origem.exists() and not destino.exists():
            try:
                shutil.copy2(origem, destino)
                print(f"[PATHS] Migrado: {origem.name} -> AppData/data/")
            except Exception:
                pass  # falha silenciosa — dados originais continuam no lugar

    # Rostos — copia pasta inteira
    origem_rostos = RONY_DIR / "rostos"
    if origem_rostos.exists():
        for arq in origem_rostos.iterdir():
            if arq.is_file():
                destino_arq = ROSTOS_DIR / arq.name
                if not destino_arq.exists():
                    try:
                        shutil.copy2(arq, destino_arq)
                    except Exception:
                        pass

    # Capturas — copia pasta inteira
    origem_cap = RONY_DIR / "captures"
    if origem_cap.exists():
        for arq in origem_cap.iterdir():
            if arq.is_file():
                destino_arq = CAPTURES_DIR / arq.name
                if not destino_arq.exists():
                    try:
                        shutil.copy2(arq, destino_arq)
                    except Exception:
                        pass


# ── Executa ao importar ───────────────────────────────────────
_criar_estrutura()
_migrar_dados_legados()
