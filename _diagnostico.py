"""Testa todos os imports do main.py e reporta erros."""
import sys, os
os.environ["PYTHONUTF8"] = "1"

modulos = [
    "pygame", "cv2", "psutil", "pyaudio", "edge_tts",
    "speech_recognition", "websockets", "requests", "PIL",
    "dotenv", "webview",
    "language_manager", "memory_manager", "app_launcher",
    "file_manager", "music_controller", "ha_config",
    "vision_module", "google_services", "wake_word",
    "camera_module", "specialist_module", "executor_module",
    "rony_paths", "rony_updater",
    "intent_router", "internet_search", "jarvis_actions", "vision_actions",
]

ok, erros = [], []
for m in modulos:
    try:
        __import__(m)
        ok.append(m)
    except Exception as e:
        erros.append((m, str(e)))

print(f"\n✅ OK ({len(ok)}): {', '.join(ok)}")
print(f"\n❌ ERROS ({len(erros)}):")
for m, e in erros:
    print(f"  [{m}] {e}")
