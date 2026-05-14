"""
launcher.py — Rony Desktop Launcher
Compilado com PyInstaller para gerar Rony.exe

Localiza o venv na pasta de instalação e inicia main.py.
Se o venv não existir, executa INSTALAR.bat automaticamente.
"""
import sys
import subprocess
import ctypes
import os
from pathlib import Path


def _app_dir() -> Path:
    """Retorna o diretório onde o launcher (ou main.py) está instalado."""
    if hasattr(sys, "_MEIPASS"):
        # Modo PyInstaller --onefile: executável extraído em temp,
        # mas o .exe fica no diretório de instalação
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _mostrar_erro(msg: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, msg, "Rony — Erro", 0x10)


def main() -> None:
    app_dir  = _app_dir()
    venv_dir = app_dir / "venv" / "Scripts"
    venv_py  = venv_dir / "python.exe"
    venv_gui = venv_dir / "pythonw.exe"
    main_py  = app_dir / "main.py"
    instalar = app_dir / "INSTALAR.bat"

    # ── Verifica main.py ─────────────────────────────────────
    if not main_py.exists():
        _mostrar_erro(
            f"main.py não encontrado em:\n{app_dir}\n\n"
            "Reinstale o Rony."
        )
        return

    # ── Instala venv se necessário ───────────────────────────
    if not venv_py.exists():
        if instalar.exists():
            result = subprocess.run(
                ["cmd", "/c", str(instalar)],
                cwd=str(app_dir),
            )
            if result.returncode != 0 or not venv_py.exists():
                _mostrar_erro(
                    "A instalação das dependências falhou.\n"
                    "Verifique sua conexão com a internet e tente novamente."
                )
                return
        else:
            _mostrar_erro(
                f"Ambiente virtual não encontrado em:\n{venv_py}\n\n"
                "Execute INSTALAR.bat para configurar o Rony."
            )
            return

    # ── Inicia o Rony sem abrir janela de terminal ────────────
    runtime_py = venv_gui if venv_gui.exists() else venv_py
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        subprocess.Popen(
            [str(runtime_py), str(main_py)],
            cwd=str(app_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo,
            close_fds=True,
        )
    except Exception as e:
        _mostrar_erro(f"Não foi possível iniciar o Rony.\n\n{e}")


if __name__ == "__main__":
    main()
