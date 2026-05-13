# ============================================================
#  executor_module.py — Autonomia Completa do Computador
#  R.O.N.Y — Execução irrestrita de tarefas no sistema
#
#  Capacidades:
#    • Shell: PowerShell, CMD, Python dinâmico
#    • Arquivos: criar, mover, copiar, deletar, zipar
#    • Processos: listar, iniciar, matar
#    • Serviços Windows: start/stop/restart/status
#    • Sistema: desligar, reiniciar, sleep, lock
#    • Volume: definir, mute, obter nível
#    • Janelas: listar, focar, fechar, minimizar, maximizar
#    • Clipboard: ler e escrever
#    • Rede: ping, ipconfig, netstat, DNS lookup
#    • Notificações: toast Windows
#    • Registro: ler e escrever chaves
#    • Tarefas agendadas: criar, listar, deletar
#    • Agente IA: Gemini function calling — execução autônoma
# ============================================================

import os
import io
import sys
import time
import json
import shutil
import signal
import asyncio
import subprocess
import contextlib
import winreg
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

# ── Diretórios ────────────────────────────────────────────────
from rony_paths import RONY_DIR, LOG_EXEC_FILE as LOG_EXEC

# ── Dependências opcionais ────────────────────────────────────
try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

try:
    import pyperclip
    CLIP_OK = True
except ImportError:
    CLIP_OK = False

try:
    import pygetwindow as gw
    GW_OK = True
except ImportError:
    GW_OK = False

try:
    from plyer import notification as _plyer_notif
    NOTIF_OK = True
except ImportError:
    NOTIF_OK = False

try:
    import send2trash
    TRASH_OK = True
except ImportError:
    TRASH_OK = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    import comtypes
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False


# ═══════════════════════════════════════════════════════════════
#  LOG DE EXECUÇÕES
# ═══════════════════════════════════════════════════════════════

def _log(tipo: str, dados: dict) -> None:
    """Registra cada execução no log JSONL."""
    entrada = {"ts": datetime.now().isoformat(), "tipo": tipo, **dados}
    try:
        with open(LOG_EXEC, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  SHELL — PowerShell / CMD
# ═══════════════════════════════════════════════════════════════

def executar_shell(comando: str, tipo: str = "powershell",
                   timeout: int = 30, cwd: str = None) -> dict:
    """
    Executa um comando shell e retorna stdout, stderr e código de saída.
    tipo: 'powershell' | 'cmd' | 'python'
    """
    _log("shell", {"tipo": tipo, "comando": comando[:500]})
    try:
        if tipo == "powershell":
            args = ["powershell", "-NoProfile", "-NonInteractive",
                    "-ExecutionPolicy", "Bypass", "-Command", comando]
        elif tipo == "cmd":
            args = ["cmd", "/c", comando]
        else:
            args = ["python", "-c", comando]

        resultado = subprocess.run(
            args,
            capture_output=True, text=True,
            timeout=timeout,
            cwd=cwd or str(Path.home()),
            encoding="utf-8", errors="replace",
        )
        saida = {
            "stdout"  : resultado.stdout.strip(),
            "stderr"  : resultado.stderr.strip(),
            "codigo"  : resultado.returncode,
            "sucesso" : resultado.returncode == 0,
        }
        _log("shell_resultado", {"codigo": saida["codigo"], "stdout_len": len(saida["stdout"])})
        return saida
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout após {timeout}s", "codigo": -1, "sucesso": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "codigo": -1, "sucesso": False}


def executar_python(codigo: str, timeout: int = 15) -> dict:
    """
    Executa código Python dinamicamente e captura a saída.
    Tem acesso a Path, os, shutil, subprocess, json, datetime e psutil.
    """
    _log("python_exec", {"codigo": codigo[:500]})
    saida_buf = io.StringIO()
    erro_buf  = io.StringIO()
    namespace = {
        "Path": Path, "os": os, "shutil": shutil,
        "subprocess": subprocess, "json": json,
        "datetime": datetime, "time": time,
        "psutil": psutil if PSUTIL_OK else None,
        "RONY_DIR": RONY_DIR,
        "print": lambda *a, **k: print(*a, **k, file=saida_buf),
    }
    try:
        with contextlib.redirect_stdout(saida_buf), contextlib.redirect_stderr(erro_buf):
            exec(compile(codigo, "<rony>", "exec"), namespace)
        return {
            "stdout": saida_buf.getvalue().strip(),
            "stderr": erro_buf.getvalue().strip(),
            "codigo": 0, "sucesso": True,
        }
    except Exception as e:
        return {
            "stdout": saida_buf.getvalue().strip(),
            "stderr": f"{type(e).__name__}: {e}",
            "codigo": 1, "sucesso": False,
        }


# ═══════════════════════════════════════════════════════════════
#  ARQUIVOS E PASTAS
# ═══════════════════════════════════════════════════════════════

def criar_arquivo(caminho: str, conteudo: str = "", encoding: str = "utf-8") -> dict:
    """Cria ou sobrescreve um arquivo com o conteúdo dado."""
    try:
        p = Path(caminho)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding=encoding)
        _log("criar_arquivo", {"caminho": caminho})
        return {"sucesso": True, "caminho": str(p.resolve()), "bytes": len(conteudo.encode())}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def criar_pasta(caminho: str) -> dict:
    """Cria uma pasta (e toda a hierarquia necessária)."""
    try:
        p = Path(caminho)
        p.mkdir(parents=True, exist_ok=True)
        _log("criar_pasta", {"caminho": caminho})
        return {"sucesso": True, "caminho": str(p.resolve())}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def deletar(caminho: str, lixeira: bool = True) -> dict:
    """Deleta arquivo ou pasta. Por padrão envia para lixeira."""
    try:
        p = Path(caminho)
        if not p.exists():
            return {"sucesso": False, "erro": f"'{caminho}' não encontrado."}
        if lixeira and TRASH_OK:
            send2trash.send2trash(str(p))
            _log("deletar_lixeira", {"caminho": caminho})
            return {"sucesso": True, "lixeira": True}
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        _log("deletar_permanente", {"caminho": caminho})
        return {"sucesso": True, "lixeira": False}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def mover(origem: str, destino: str) -> dict:
    """Move arquivo ou pasta."""
    try:
        resultado = shutil.move(str(origem), str(destino))
        _log("mover", {"origem": origem, "destino": destino})
        return {"sucesso": True, "destino": str(resultado)}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def copiar(origem: str, destino: str) -> dict:
    """Copia arquivo ou pasta."""
    try:
        o, d = Path(origem), Path(destino)
        if o.is_dir():
            shutil.copytree(str(o), str(d), dirs_exist_ok=True)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(o), str(d))
        _log("copiar", {"origem": origem, "destino": destino})
        return {"sucesso": True, "destino": str(d.resolve())}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def renomear(caminho: str, novo_nome: str) -> dict:
    """Renomeia arquivo ou pasta."""
    try:
        p       = Path(caminho)
        destino = p.parent / novo_nome
        p.rename(destino)
        _log("renomear", {"de": caminho, "para": str(destino)})
        return {"sucesso": True, "novo_caminho": str(destino.resolve())}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def compactar(origem: str, destino: str = None, formato: str = "zip") -> dict:
    """Compacta arquivo ou pasta em zip/tar.gz."""
    try:
        p = Path(origem)
        saida = destino or str(p.parent / p.name)
        resultado = shutil.make_archive(saida, formato, str(p.parent), p.name)
        _log("compactar", {"origem": origem, "resultado": resultado})
        return {"sucesso": True, "arquivo": resultado}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def descompactar(arquivo: str, destino: str = None) -> dict:
    """Descompacta arquivo zip/tar."""
    try:
        p = Path(arquivo)
        dest = destino or str(p.parent / p.stem)
        shutil.unpack_archive(str(p), dest)
        _log("descompactar", {"arquivo": arquivo, "destino": dest})
        return {"sucesso": True, "destino": dest}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════
#  PROCESSOS
# ═══════════════════════════════════════════════════════════════

def listar_processos(filtro: str = "") -> list[dict]:
    """Lista processos em execução. Filtro por nome."""
    if not PSUTIL_OK:
        return []
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = p.info
            if filtro and filtro.lower() not in info["name"].lower():
                continue
            procs.append({
                "pid"    : info["pid"],
                "nome"   : info["name"],
                "cpu"    : info.get("cpu_percent", 0),
                "ram_mb" : round(info["memory_info"].rss / 1024 / 1024, 1) if info.get("memory_info") else 0,
                "status" : info.get("status", ""),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(procs, key=lambda x: x["ram_mb"], reverse=True)


def matar_processo(nome_ou_pid: str) -> dict:
    """Encerra um processo pelo nome ou PID."""
    if not PSUTIL_OK:
        return {"sucesso": False, "erro": "psutil não instalado"}
    mortos = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if (str(p.pid) == str(nome_ou_pid) or
                    p.name().lower() == str(nome_ou_pid).lower() or
                    str(nome_ou_pid).lower() in p.name().lower()):
                p.terminate()
                mortos.append(f"{p.name()} (PID {p.pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _log("matar_processo", {"alvo": nome_ou_pid, "mortos": mortos})
    if mortos:
        return {"sucesso": True, "encerrados": mortos}
    return {"sucesso": False, "erro": f"Processo '{nome_ou_pid}' não encontrado."}


def iniciar_processo(comando: str, janela_visivel: bool = True) -> dict:
    """Inicia um processo/aplicativo."""
    try:
        if janela_visivel:
            subprocess.Popen(comando, shell=True)
        else:
            subprocess.Popen(comando, shell=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        _log("iniciar_processo", {"comando": comando})
        return {"sucesso": True, "comando": comando}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════
#  SERVIÇOS WINDOWS
# ═══════════════════════════════════════════════════════════════

def gerenciar_servico(nome: str, acao: str) -> dict:
    """
    Gerencia serviços Windows.
    acao: 'start' | 'stop' | 'restart' | 'status' | 'enable' | 'disable'
    """
    try:
        if acao == "status":
            r = executar_shell(f"Get-Service '{nome}' | Select-Object Name, Status, StartType | ConvertTo-Json")
            return {"sucesso": True, "info": r["stdout"]}
        cmd_map = {
            "start"  : f"Start-Service '{nome}'",
            "stop"   : f"Stop-Service '{nome}' -Force",
            "restart": f"Restart-Service '{nome}'",
            "enable" : f"Set-Service '{nome}' -StartupType Automatic",
            "disable": f"Set-Service '{nome}' -StartupType Disabled",
        }
        if acao not in cmd_map:
            return {"sucesso": False, "erro": f"Ação '{acao}' inválida."}
        r = executar_shell(cmd_map[acao])
        _log("servico", {"nome": nome, "acao": acao})
        return {"sucesso": r["sucesso"], "stdout": r["stdout"], "stderr": r["stderr"]}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════
#  CONTROLE DO SISTEMA
# ═══════════════════════════════════════════════════════════════

def controle_sistema(acao: str, delay_seg: int = 0) -> dict:
    """
    Controla o estado do sistema.
    acao: 'desligar' | 'reiniciar' | 'hibernar' | 'dormir' | 'bloquear' | 'logoff'
    """
    _log("controle_sistema", {"acao": acao, "delay": delay_seg})
    cmds = {
        "desligar" : f"shutdown /s /t {delay_seg}",
        "shutdown"  : f"shutdown /s /t {delay_seg}",
        "reiniciar" : f"shutdown /r /t {delay_seg}",
        "restart"   : f"shutdown /r /t {delay_seg}",
        "hibernar"  : "shutdown /h",
        "hibernate" : "shutdown /h",
        "dormir"    : "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "sleep"     : "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "bloquear"  : "rundll32.exe user32.dll,LockWorkStation",
        "lock"      : "rundll32.exe user32.dll,LockWorkStation",
        "logoff"    : "shutdown /l",
    }
    cmd = cmds.get(acao.lower())
    if not cmd:
        return {"sucesso": False, "erro": f"Ação '{acao}' desconhecida."}
    r = executar_shell(cmd, tipo="cmd")
    return {"sucesso": True, "acao": acao}


def cancelar_desligamento() -> dict:
    """Cancela um desligamento/reinício agendado."""
    r = executar_shell("shutdown /a", tipo="cmd")
    return {"sucesso": r["codigo"] == 0}


# ═══════════════════════════════════════════════════════════════
#  VOLUME DE ÁUDIO
# ═══════════════════════════════════════════════════════════════

def _obter_interface_volume():
    """Retorna a interface COM do volume master do Windows."""
    if not AUDIO_OK:
        return None
    try:
        devices  = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return comtypes.cast(interface, comtypes.POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def obter_volume() -> int:
    """Retorna o volume atual (0-100)."""
    vol = _obter_interface_volume()
    if vol:
        return round(vol.GetMasterVolumeLevelScalar() * 100)
    r = executar_shell("(Get-AudioDevice -Playback).Volume")
    try:
        return int(r["stdout"].split(".")[0])
    except Exception:
        return -1


def definir_volume(nivel: int) -> dict:
    """Define o volume (0-100)."""
    nivel = max(0, min(100, int(nivel)))
    vol = _obter_interface_volume()
    if vol:
        vol.SetMasterVolumeLevelScalar(nivel / 100, None)
        _log("volume", {"nivel": nivel})
        return {"sucesso": True, "nivel": nivel}
    # Fallback PowerShell
    r = executar_shell(f"(New-Object -com Shell.Application).Windows() | ForEach-Object {{ $_.Document.Application.Volume = {nivel} }}")
    return {"sucesso": r["sucesso"], "nivel": nivel}


def mute_toggle(mudo: bool = None) -> dict:
    """Alterna ou define o mudo do áudio."""
    vol = _obter_interface_volume()
    if vol:
        estado_atual = vol.GetMute()
        novo_estado  = (not estado_atual) if mudo is None else mudo
        vol.SetMute(novo_estado, None)
        _log("mute", {"mudo": novo_estado})
        return {"sucesso": True, "mudo": novo_estado}
    return {"sucesso": False, "erro": "pycaw não disponível"}


# ═══════════════════════════════════════════════════════════════
#  JANELAS
# ═══════════════════════════════════════════════════════════════

def listar_janelas(filtro: str = "") -> list[dict]:
    """Lista janelas abertas visíveis."""
    if not GW_OK:
        r = executar_shell(
            "Get-Process | Where-Object {$_.MainWindowTitle} | "
            "Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json"
        )
        try:
            return json.loads(r["stdout"]) if r["sucesso"] else []
        except Exception:
            return []
    janelas = []
    for w in gw.getAllWindows():
        if w.title and (not filtro or filtro.lower() in w.title.lower()):
            janelas.append({"titulo": w.title, "visivel": w.visible,
                            "x": w.left, "y": w.top, "w": w.width, "h": w.height})
    return janelas


def controlar_janela(titulo: str, acao: str) -> dict:
    """
    Controla uma janela.
    acao: 'focar' | 'minimizar' | 'maximizar' | 'fechar' | 'restaurar'
    """
    if not GW_OK:
        return {"sucesso": False, "erro": "pygetwindow não disponível"}
    janelas = gw.getWindowsWithTitle(titulo)
    if not janelas:
        # Busca parcial
        todas = gw.getAllWindows()
        janelas = [w for w in todas if titulo.lower() in w.title.lower() and w.title]
    if not janelas:
        return {"sucesso": False, "erro": f"Janela '{titulo}' não encontrada."}
    w = janelas[0]
    try:
        if acao == "focar":
            w.activate()
        elif acao == "minimizar":
            w.minimize()
        elif acao == "maximizar":
            w.maximize()
        elif acao == "restaurar":
            w.restore()
        elif acao == "fechar":
            w.close()
        _log("janela", {"titulo": titulo, "acao": acao})
        return {"sucesso": True, "titulo": w.title, "acao": acao}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════
#  CLIPBOARD
# ═══════════════════════════════════════════════════════════════

def obter_clipboard() -> str:
    """Retorna o conteúdo atual do clipboard."""
    if CLIP_OK:
        try:
            return pyperclip.paste()
        except Exception:
            pass
    r = executar_shell("Get-Clipboard")
    return r["stdout"]


def definir_clipboard(texto: str) -> dict:
    """Define o texto no clipboard."""
    if CLIP_OK:
        try:
            pyperclip.copy(texto)
            return {"sucesso": True, "chars": len(texto)}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}
    r = executar_shell(f"Set-Clipboard '{texto}'")
    return {"sucesso": r["sucesso"]}


# ═══════════════════════════════════════════════════════════════
#  REDE
# ═══════════════════════════════════════════════════════════════

def ping(host: str, count: int = 4) -> dict:
    """Faz ping para um host e retorna resultado."""
    r = executar_shell(f"ping -n {count} {host}", tipo="cmd", timeout=15)
    sucesso = "TTL=" in r["stdout"] or "ttl=" in r["stdout"]
    return {"sucesso": sucesso, "host": host, "saida": r["stdout"]}


def info_rede() -> dict:
    """Retorna informações de rede (IP, gateway, DNS)."""
    r = executar_shell(
        "Get-NetIPConfiguration | Select-Object InterfaceAlias, "
        "@{n='IP';e={$_.IPv4Address.IPAddress}}, "
        "@{n='Gateway';e={$_.IPv4DefaultGateway.NextHop}}, "
        "@{n='DNS';e={$_.DNSServer.ServerAddresses}} | ConvertTo-Json"
    )
    try:
        return {"sucesso": True, "dados": json.loads(r["stdout"])}
    except Exception:
        return {"sucesso": False, "raw": r["stdout"]}


def lookup_dns(host: str) -> dict:
    """Resolve um hostname para IP."""
    r = executar_shell(f"Resolve-DnsName {host} | Select-Object Name, IPAddress | ConvertTo-Json")
    try:
        return {"sucesso": True, "dados": json.loads(r["stdout"])}
    except Exception:
        return {"sucesso": False, "raw": r["stdout"]}


def conexoes_ativas(filtro_porta: int = None) -> list[dict]:
    """Lista conexões de rede ativas."""
    cmd = "Get-NetTCPConnection -State Established | " \
          "Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State | " \
          "ConvertTo-Json"
    r = executar_shell(cmd)
    try:
        dados = json.loads(r["stdout"])
        if isinstance(dados, dict):
            dados = [dados]
        if filtro_porta:
            dados = [d for d in dados if d.get("LocalPort") == filtro_porta
                     or d.get("RemotePort") == filtro_porta]
        return dados
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  NOTIFICAÇÕES
# ═══════════════════════════════════════════════════════════════

def notificacao(titulo: str, mensagem: str, duracao: int = 5) -> dict:
    """Exibe uma notificação toast no Windows."""
    if NOTIF_OK:
        try:
            _plyer_notif.notify(
                title=titulo, message=mensagem,
                app_name="Rony", timeout=duracao,
            )
            return {"sucesso": True}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}
    # Fallback PowerShell
    r = executar_shell(
        f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
        f"ContentType = WindowsRuntime] | Out-Null; "
        f"$xml = [Windows.UI.Notifications.ToastNotificationManager]::"
        f"GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        f"$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{titulo}')); "
        f"$xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{mensagem}')); "
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Rony')"
        f".Show([Windows.UI.Notifications.ToastNotification]::new($xml))"
    )
    return {"sucesso": r["sucesso"]}


# ═══════════════════════════════════════════════════════════════
#  REGISTRO WINDOWS
# ═══════════════════════════════════════════════════════════════

_HIVES = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU" : winreg.HKEY_USERS,
    "HKCC": winreg.HKEY_CURRENT_CONFIG,
}

def _parse_chave(caminho: str):
    """Divide 'HKLM\\Software\\...' em (hive, subchave)."""
    partes = caminho.replace("/", "\\").split("\\", 1)
    hive_str = partes[0].upper()
    sub = partes[1] if len(partes) > 1 else ""
    return _HIVES.get(hive_str, winreg.HKEY_CURRENT_USER), sub


def ler_registro(caminho: str, valor: str = "") -> dict:
    """Lê um valor do registro do Windows."""
    try:
        hive, sub = _parse_chave(caminho)
        with winreg.OpenKey(hive, sub, 0, winreg.KEY_READ) as k:
            dados, tipo = winreg.QueryValueEx(k, valor)
        return {"sucesso": True, "valor": valor or "(Default)", "dados": dados, "tipo": tipo}
    except FileNotFoundError:
        return {"sucesso": False, "erro": f"Chave '{caminho}' não encontrada."}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def escrever_registro(caminho: str, valor: str, dados: Any,
                       tipo: str = "REG_SZ") -> dict:
    """Escreve um valor no registro do Windows."""
    tipos_map = {
        "REG_SZ"   : winreg.REG_SZ,
        "REG_DWORD": winreg.REG_DWORD,
        "REG_BINARY": winreg.REG_BINARY,
        "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
    }
    try:
        hive, sub = _parse_chave(caminho)
        with winreg.CreateKey(hive, sub) as k:
            winreg.SetValueEx(k, valor, 0, tipos_map.get(tipo, winreg.REG_SZ), dados)
        _log("registro_write", {"caminho": caminho, "valor": valor})
        return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════
#  TAREFAS AGENDADAS
# ═══════════════════════════════════════════════════════════════

def criar_tarefa_agendada(nome: str, comando: str, horario: str,
                           frequencia: str = "DAILY") -> dict:
    """
    Cria uma tarefa agendada no Windows.
    frequencia: 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'ONCE'
    horario: 'HH:MM' ex: '08:00'
    """
    cmd = (f'schtasks /create /tn "{nome}" /tr "{comando}" '
           f'/sc {frequencia} /st {horario} /f')
    r = executar_shell(cmd, tipo="cmd")
    _log("tarefa_agendada_criar", {"nome": nome, "comando": comando, "horario": horario})
    return {"sucesso": r["sucesso"], "saida": r["stdout"] or r["stderr"]}


def listar_tarefas(filtro: str = "") -> dict:
    """Lista tarefas agendadas."""
    cmd = f'schtasks /query /fo CSV /nh'
    if filtro:
        cmd += f' /tn "{filtro}"'
    r = executar_shell(cmd, tipo="cmd")
    return {"sucesso": r["sucesso"], "tarefas": r["stdout"]}


def deletar_tarefa(nome: str) -> dict:
    """Remove uma tarefa agendada."""
    r = executar_shell(f'schtasks /delete /tn "{nome}" /f', tipo="cmd")
    _log("tarefa_agendada_deletar", {"nome": nome})
    return {"sucesso": r["sucesso"]}


# ═══════════════════════════════════════════════════════════════
#  INFO SISTEMA
# ═══════════════════════════════════════════════════════════════

def info_sistema_completa() -> dict:
    """Retorna informações detalhadas do sistema."""
    info = {}
    if PSUTIL_OK:
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        info["cpu_cores"]   = psutil.cpu_count()
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / 1024**3, 2)
        info["ram_usada_gb"] = round(mem.used  / 1024**3, 2)
        info["ram_percent"]  = mem.percent
        disco = psutil.disk_usage("C:/")
        info["disco_total_gb"] = round(disco.total / 1024**3, 2)
        info["disco_livre_gb"] = round(disco.free  / 1024**3, 2)
        info["disco_percent"]  = disco.percent
        info["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).strftime("%d/%m/%Y %H:%M")
    r = executar_shell(
        "$os = Get-WmiObject Win32_OperatingSystem; "
        "$cpu = Get-WmiObject Win32_Processor; "
        "@{OS=$os.Caption; Version=$os.Version; CPU=$cpu.Name; "
        "Hostname=$env:COMPUTERNAME; User=$env:USERNAME} | ConvertTo-Json"
    )
    try:
        info["windows"] = json.loads(r["stdout"])
    except Exception:
        pass
    return info


def variaveis_ambiente() -> dict:
    """Retorna variáveis de ambiente do sistema."""
    return dict(os.environ)


def definir_variavel_ambiente(nome: str, valor: str, permanente: bool = False) -> dict:
    """Define uma variável de ambiente (sessão atual ou permanente)."""
    os.environ[nome] = valor
    if permanente:
        r = executar_shell(
            f'[System.Environment]::SetEnvironmentVariable("{nome}", "{valor}", "User")'
        )
        return {"sucesso": r["sucesso"], "permanente": True}
    return {"sucesso": True, "permanente": False}


# ═══════════════════════════════════════════════════════════════
#  AGENTE IA — GEMINI FUNCTION CALLING
#  Loop autônomo: Gemini decide quais ferramentas usar
# ═══════════════════════════════════════════════════════════════

# Mapa de ferramentas disponíveis para o agente
_FERRAMENTAS: dict[str, callable] = {
    "executar_shell"          : executar_shell,
    "executar_python"         : executar_python,
    "criar_arquivo"           : criar_arquivo,
    "criar_pasta"             : criar_pasta,
    "deletar"                 : deletar,
    "mover"                   : mover,
    "copiar"                  : copiar,
    "renomear"                : renomear,
    "compactar"               : compactar,
    "descompactar"            : descompactar,
    "listar_processos"        : listar_processos,
    "matar_processo"          : matar_processo,
    "iniciar_processo"        : iniciar_processo,
    "gerenciar_servico"       : gerenciar_servico,
    "controle_sistema"        : controle_sistema,
    "obter_volume"            : obter_volume,
    "definir_volume"          : definir_volume,
    "mute_toggle"             : mute_toggle,
    "listar_janelas"          : listar_janelas,
    "controlar_janela"        : controlar_janela,
    "obter_clipboard"         : obter_clipboard,
    "definir_clipboard"       : definir_clipboard,
    "ping"                    : ping,
    "info_rede"               : info_rede,
    "lookup_dns"              : lookup_dns,
    "notificacao"             : notificacao,
    "ler_registro"            : ler_registro,
    "escrever_registro"       : escrever_registro,
    "criar_tarefa_agendada"   : criar_tarefa_agendada,
    "listar_tarefas"          : listar_tarefas,
    "deletar_tarefa"          : deletar_tarefa,
    "info_sistema_completa"   : info_sistema_completa,
}


def _definicoes_ferramentas():
    """Retorna as declarações de ferramentas para o Gemini."""
    from google.genai import types

    return types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="executar_shell",
            description="Executa comando PowerShell, CMD ou Python no sistema. Use para instalar software, manipular sistema, consultar informações, etc.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "comando": types.Schema(type=types.Type.STRING, description="O comando a executar"),
                "tipo"   : types.Schema(type=types.Type.STRING, description="'powershell' (padrão), 'cmd' ou 'python'"),
                "timeout": types.Schema(type=types.Type.INTEGER, description="Timeout em segundos (padrão 30)"),
            }, required=["comando"]),
        ),
        types.FunctionDeclaration(
            name="executar_python",
            description="Executa código Python dinâmico com acesso a Path, os, shutil, psutil, subprocess. Use para lógica complexa.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "codigo": types.Schema(type=types.Type.STRING, description="Código Python a executar"),
            }, required=["codigo"]),
        ),
        types.FunctionDeclaration(
            name="criar_arquivo",
            description="Cria ou sobrescreve um arquivo com conteúdo de texto.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "caminho"  : types.Schema(type=types.Type.STRING, description="Caminho completo do arquivo"),
                "conteudo" : types.Schema(type=types.Type.STRING, description="Conteúdo do arquivo"),
            }, required=["caminho"]),
        ),
        types.FunctionDeclaration(
            name="criar_pasta",
            description="Cria uma pasta (e subpastas necessárias).",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "caminho": types.Schema(type=types.Type.STRING, description="Caminho da pasta a criar"),
            }, required=["caminho"]),
        ),
        types.FunctionDeclaration(
            name="deletar",
            description="Deleta arquivo ou pasta. Por padrão envia para lixeira.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "caminho" : types.Schema(type=types.Type.STRING, description="Caminho do arquivo/pasta"),
                "lixeira" : types.Schema(type=types.Type.BOOLEAN, description="True=lixeira (padrão), False=permanente"),
            }, required=["caminho"]),
        ),
        types.FunctionDeclaration(
            name="mover",
            description="Move arquivo ou pasta de um local para outro.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "origem"  : types.Schema(type=types.Type.STRING),
                "destino" : types.Schema(type=types.Type.STRING),
            }, required=["origem", "destino"]),
        ),
        types.FunctionDeclaration(
            name="copiar",
            description="Copia arquivo ou pasta.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "origem"  : types.Schema(type=types.Type.STRING),
                "destino" : types.Schema(type=types.Type.STRING),
            }, required=["origem", "destino"]),
        ),
        types.FunctionDeclaration(
            name="renomear",
            description="Renomeia um arquivo ou pasta.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "caminho"   : types.Schema(type=types.Type.STRING),
                "novo_nome" : types.Schema(type=types.Type.STRING),
            }, required=["caminho", "novo_nome"]),
        ),
        types.FunctionDeclaration(
            name="listar_processos",
            description="Lista processos em execução com uso de CPU e RAM.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "filtro": types.Schema(type=types.Type.STRING, description="Filtrar por nome (opcional)"),
            }),
        ),
        types.FunctionDeclaration(
            name="matar_processo",
            description="Encerra um processo pelo nome ou PID.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "nome_ou_pid": types.Schema(type=types.Type.STRING),
            }, required=["nome_ou_pid"]),
        ),
        types.FunctionDeclaration(
            name="iniciar_processo",
            description="Inicia um programa, script ou comando.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "comando"       : types.Schema(type=types.Type.STRING),
                "janela_visivel": types.Schema(type=types.Type.BOOLEAN),
            }, required=["comando"]),
        ),
        types.FunctionDeclaration(
            name="gerenciar_servico",
            description="Gerencia serviços Windows (start/stop/restart/status/enable/disable).",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "nome" : types.Schema(type=types.Type.STRING),
                "acao" : types.Schema(type=types.Type.STRING, description="'start'|'stop'|'restart'|'status'|'enable'|'disable'"),
            }, required=["nome", "acao"]),
        ),
        types.FunctionDeclaration(
            name="controle_sistema",
            description="Controla o estado do sistema: desligar, reiniciar, hibernar, dormir, bloquear, logoff.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "acao"     : types.Schema(type=types.Type.STRING),
                "delay_seg": types.Schema(type=types.Type.INTEGER, description="Delay em segundos antes da ação"),
            }, required=["acao"]),
        ),
        types.FunctionDeclaration(
            name="definir_volume",
            description="Define o volume do áudio (0-100).",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "nivel": types.Schema(type=types.Type.INTEGER),
            }, required=["nivel"]),
        ),
        types.FunctionDeclaration(
            name="obter_volume",
            description="Retorna o volume atual do áudio (0-100).",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="mute_toggle",
            description="Ativa ou desativa o mudo do áudio.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "mudo": types.Schema(type=types.Type.BOOLEAN, description="True=mutar, False=desmutar, omitir=alternar"),
            }),
        ),
        types.FunctionDeclaration(
            name="listar_janelas",
            description="Lista janelas abertas no sistema.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "filtro": types.Schema(type=types.Type.STRING),
            }),
        ),
        types.FunctionDeclaration(
            name="controlar_janela",
            description="Foca, minimiza, maximiza, restaura ou fecha uma janela.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "titulo": types.Schema(type=types.Type.STRING),
                "acao"  : types.Schema(type=types.Type.STRING, description="'focar'|'minimizar'|'maximizar'|'restaurar'|'fechar'"),
            }, required=["titulo", "acao"]),
        ),
        types.FunctionDeclaration(
            name="obter_clipboard",
            description="Retorna o conteúdo atual do clipboard.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="definir_clipboard",
            description="Copia texto para o clipboard.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "texto": types.Schema(type=types.Type.STRING),
            }, required=["texto"]),
        ),
        types.FunctionDeclaration(
            name="ping",
            description="Faz ping para um host/IP e verifica conectividade.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "host" : types.Schema(type=types.Type.STRING),
                "count": types.Schema(type=types.Type.INTEGER),
            }, required=["host"]),
        ),
        types.FunctionDeclaration(
            name="info_rede",
            description="Retorna informações de rede: IPs, gateway, DNS.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="notificacao",
            description="Exibe uma notificação toast no Windows.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "titulo"  : types.Schema(type=types.Type.STRING),
                "mensagem": types.Schema(type=types.Type.STRING),
                "duracao" : types.Schema(type=types.Type.INTEGER),
            }, required=["titulo", "mensagem"]),
        ),
        types.FunctionDeclaration(
            name="criar_tarefa_agendada",
            description="Cria uma tarefa agendada no Windows.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={
                "nome"      : types.Schema(type=types.Type.STRING),
                "comando"   : types.Schema(type=types.Type.STRING),
                "horario"   : types.Schema(type=types.Type.STRING, description="Formato HH:MM ex: 08:00"),
                "frequencia": types.Schema(type=types.Type.STRING, description="'DAILY'|'WEEKLY'|'MONTHLY'|'ONCE'"),
            }, required=["nome", "comando", "horario"]),
        ),
        types.FunctionDeclaration(
            name="info_sistema_completa",
            description="Retorna informações completas do sistema: CPU, RAM, disco, SO, hostname.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
    ])


async def executar_com_agente(
    texto: str,
    client_gemini,
    system_prompt: str,
    historico: list[dict],
    lingua: str = "pt",
    max_iteracoes: int = 6,
) -> str:
    """
    Loop de agente autônomo com Gemini Function Calling.
    O Gemini decide quais ferramentas usar para completar a tarefa.
    Retorna a resposta final em linguagem natural.
    """
    import google.genai as genai
    from google.genai import types

    # Instrução adicional de autonomia
    instrucao_autonomia = {
        "pt": "\n\nVOCÊ TEM AUTONOMIA TOTAL DO COMPUTADOR. Use as ferramentas disponíveis para executar qualquer tarefa solicitada. Execute, verifique o resultado e informe o que foi feito de forma clara e direta.",
        "en": "\n\nYOU HAVE FULL COMPUTER AUTONOMY. Use the available tools to execute any requested task. Execute, verify the result and report what was done clearly.",
        "fr": "\n\nVOUS AVEZ UNE AUTONOMIE TOTALE SUR L'ORDINATEUR. Utilisez les outils disponibles pour exécuter toute tâche demandée.",
        "es": "\n\nTIENES AUTONOMÍA TOTAL DEL COMPUTADOR. Usa las herramientas disponibles para ejecutar cualquier tarea solicitada.",
    }.get(lingua, "")

    system_final = system_prompt + instrucao_autonomia
    ferramentas  = _definicoes_ferramentas()

    # Monta histórico
    contents = []
    for m in historico[-8:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["text"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=texto)]))

    config = types.GenerateContentConfig(
        system_instruction=system_final,
        tools=[ferramentas],
        temperature=0.3,
        max_output_tokens=2048,
    )

    acoes_executadas = []

    for iteracao in range(max_iteracoes):
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda c=contents[:]: client_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=c,
                config=config,
            ),
        )

        # Verifica se há chamadas de função
        fn_calls = []
        texto_resposta = ""
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fn_calls.append(part.function_call)
                elif hasattr(part, "text") and part.text:
                    texto_resposta += part.text

        if not fn_calls:
            # Sem mais chamadas — resposta final
            return texto_resposta.strip() or (
                {"pt": "Tarefa concluída.", "en": "Task completed.",
                 "fr": "Tâche terminée.", "es": "Tarea completada."}.get(lingua, "Done.")
            )

        # Executa todas as funções chamadas
        results_parts = []
        for fn in fn_calls:
            nome_fn = fn.name
            args    = dict(fn.args) if fn.args else {}
            print(f"[AGENTE] Executando: {nome_fn}({list(args.keys())})")

            fn_callable = _FERRAMENTAS.get(nome_fn)
            if fn_callable:
                try:
                    resultado = await asyncio.get_event_loop().run_in_executor(
                        None, lambda f=fn_callable, a=args: f(**a)
                    )
                    acoes_executadas.append(f"{nome_fn}: OK")
                except Exception as e:
                    resultado = {"sucesso": False, "erro": str(e)}
                    acoes_executadas.append(f"{nome_fn}: ERRO")
            else:
                resultado = {"sucesso": False, "erro": f"Ferramenta '{nome_fn}' não encontrada."}

            results_parts.append(
                types.Part.from_function_response(
                    name=nome_fn,
                    response={"result": json.dumps(resultado, ensure_ascii=False, default=str)},
                )
            )

        # Adiciona a resposta do modelo (com chamadas de função) ao histórico
        contents.append(types.Content(role="model", parts=[
            types.Part(function_call=fc) for fc in fn_calls
        ] + ([types.Part(text=texto_resposta)] if texto_resposta else [])))

        # Adiciona os resultados das ferramentas
        contents.append(types.Content(role="user", parts=results_parts))

    # Fallback se excedeu iterações
    resumo = ", ".join(acoes_executadas) if acoes_executadas else "nenhuma"
    return {
        "pt": f"Executei as ações necessárias ({resumo}) mas não finalizei em tempo. Verifique o resultado.",
        "en": f"Executed actions ({resumo}) but didn't finalize in time. Please check the result.",
        "fr": f"Actions exécutées ({resumo}) mais pas finalisé à temps. Vérifiez le résultat.",
        "es": f"Acciones ejecutadas ({resumo}) pero no finalicé a tiempo. Verifica el resultado.",
    }.get(lingua, "Max iterations reached.")


def resposta_voz_execucao(resultado: dict, lingua: str = "pt") -> str:
    """Converte resultado de execução em mensagem de voz amigável."""
    if not resultado:
        return {"pt": "Ação executada.", "en": "Action executed.",
                "fr": "Action exécutée.", "es": "Acción ejecutada."}.get(lingua, "Done.")
    if resultado.get("sucesso"):
        stdout = resultado.get("stdout", "") or resultado.get("saida", "")
        if stdout and len(stdout) < 200:
            return stdout
        return {"pt": "Feito.", "en": "Done.", "fr": "Fait.", "es": "Listo."}.get(lingua, "Done.")
    erro = resultado.get("erro", resultado.get("stderr", "Erro desconhecido"))
    return {"pt": f"Erro: {erro}", "en": f"Error: {erro}",
            "fr": f"Erreur : {erro}", "es": f"Error: {erro}"}.get(lingua, f"Error: {erro}")
