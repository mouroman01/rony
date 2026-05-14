"""
criar_atalho.py - Cria atalho do R.O.N.Y na area de trabalho (Windows)
"""

import sys
from pathlib import Path

RONY_DIR = Path(__file__).parent.parent


def _atalho_paths():
    launcher = RONY_DIR / "Rony.exe"
    if not launcher.exists():
        launcher = RONY_DIR / "INICIAR_RONY.bat"

    icon = RONY_DIR / "app.ico"
    if not icon.exists() and launcher.suffix.lower() == ".exe":
        icon = launcher

    return launcher, icon


def criar_atalho_windows():
    """Cria atalho .lnk na area de trabalho usando win32com."""
    try:
        import winreg
        import win32com.client
    except ImportError:
        return criar_atalho_powershell()

    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            ) as key:
                desktop = Path(winreg.QueryValueEx(key, "Desktop")[0])
        except Exception:
            desktop = Path.home() / "OneDrive" / "Desktop"
            if not desktop.exists():
                desktop = Path.home() / "Desktop"

    atalho_path = desktop / "Rony.lnk"
    launcher, icon = _atalho_paths()

    if atalho_path.exists():
        print(f"Atalho ja existe: {atalho_path}")
        return True

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        atalho = shell.CreateShortCut(str(atalho_path))
        atalho.Targetpath = str(launcher)
        atalho.WorkingDirectory = str(RONY_DIR)
        atalho.WindowStyle = 1
        atalho.Description = "R.O.N.Y - Responsive Omni-lingual Neural sYstem"
        if icon.exists():
            atalho.IconLocation = f"{icon},0"
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
        capture_output=True,
        text=True,
    )
    desktop = result.stdout.strip()
    if not desktop:
        desktop = str(Path.home() / "Desktop")

    launcher_path, icon_path = _atalho_paths()
    launcher = str(launcher_path).replace("\\", "\\\\")
    work_dir = str(RONY_DIR).replace("\\", "\\\\")
    atalho_ps = f"{desktop}\\\\Rony.lnk"
    icon_ps = str(icon_path).replace("\\", "\\\\")

    script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{atalho_ps}")
$Shortcut.TargetPath = "{launcher}"
$Shortcut.WorkingDirectory = "{work_dir}"
$Shortcut.Description = "R.O.N.Y - Assistente Pessoal Inteligente"
$Shortcut.WindowStyle = 1
if (Test-Path "{icon_ps}") {{
    $Shortcut.IconLocation = "{icon_ps},0"
}}
$Shortcut.Save()
Write-Host "Atalho criado com sucesso"
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )
    if "sucesso" in result.stdout.lower() or result.returncode == 0:
        print("Atalho criado na area de trabalho.")
        return True

    print(f"Falha ao criar atalho: {result.stderr}")
    return False


if __name__ == "__main__":
    ok = criar_atalho_windows()
    sys.exit(0 if ok else 1)
