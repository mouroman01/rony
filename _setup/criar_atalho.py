"""
criar_atalho.py — Cria atalho do R.O.N.Y na area de trabalho (Windows)
"""

import sys
from pathlib import Path

RONY_DIR = Path(__file__).parent.parent


def criar_atalho_windows():
    """Cria atalho .lnk na area de trabalho usando win32com."""
    try:
        import winreg
        import win32com.client
    except ImportError:
        # Tenta via PowerShell como fallback
        return criar_atalho_powershell()

    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        # Desktop pode estar em OneDrive
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                desktop = Path(winreg.QueryValueEx(key, "Desktop")[0])
        except Exception:
            desktop = Path.home() / "OneDrive" / "Desktop"
            if not desktop.exists():
                desktop = Path.home() / "Desktop"

    atalho_path = desktop / "RONY.lnk"
    launcher    = RONY_DIR / "INICIAR_RONY.bat"
    icone       = RONY_DIR / "frontend" / "public" / "favicon.ico"

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        atalho = shell.CreateShortCut(str(atalho_path))
        atalho.Targetpath      = str(launcher)
        atalho.WorkingDirectory= str(RONY_DIR)
        atalho.WindowStyle     = 1
        atalho.Description     = "R.O.N.Y — Responsive Omni-lingual Neural sYstem"
        if icone.exists():
            atalho.IconLocation = str(icone)
        atalho.save()
        print(f"Atalho criado: {atalho_path}")
        return True
    except Exception as e:
        print(f"win32com falhou: {e}")
        return criar_atalho_powershell()


def criar_atalho_powershell():
    """Cria atalho via PowerShell (sem dependencias extras)."""
    import subprocess

    desktop_script = (
        "$desktop = [System.Environment]::GetFolderPath('Desktop'); "
        "$desktop"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", desktop_script],
        capture_output=True, text=True
    )
    desktop = result.stdout.strip()
    if not desktop:
        desktop = str(Path.home() / "Desktop")

    launcher  = str(RONY_DIR / "INICIAR_RONY.bat").replace("\\", "\\\\")
    work_dir  = str(RONY_DIR).replace("\\", "\\\\")
    atalho_ps = f"{desktop}\\\\RONY.lnk"

    script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{atalho_ps}")
$Shortcut.TargetPath = "{launcher}"
$Shortcut.WorkingDirectory = "{work_dir}"
$Shortcut.Description = "R.O.N.Y — Assistente Pessoal Inteligente"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "Atalho criado com sucesso"
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True
    )
    if "sucesso" in result.stdout.lower() or result.returncode == 0:
        print(f"Atalho criado na area de trabalho.")
        return True
    else:
        print(f"Falha ao criar atalho: {result.stderr}")
        return False


if __name__ == "__main__":
    ok = criar_atalho_windows()
    sys.exit(0 if ok else 1)
