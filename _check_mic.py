import speech_recognition as sr

print("=== MICROFONES DISPONÍVEIS ===")
try:
    import pyaudio
    p = pyaudio.PyAudio()
    encontrou = False
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev["maxInputChannels"] > 0:
            print(f"  [{i}] {dev['name']}")
            encontrou = True
    p.terminate()
    if not encontrou:
        print("  Nenhum microfone encontrado!")
except Exception as e:
    print(f"  ERRO ao listar microfones: {e}")

print()
print("=== TESTE DE ESCUTA (fale algo em 5 segundos) ===")
try:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("  Microfone aberto. Fale agora...")
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source, timeout=5, phrase_time_limit=5)
    print("  Áudio capturado! Reconhecendo...")
    texto = r.recognize_google(audio, language="pt-BR")
    print(f"  Reconhecido: '{texto}'")
except sr.WaitTimeoutError:
    print("  Timeout — nenhum som detectado.")
except sr.UnknownValueError:
    print("  Som captado mas não reconhecido.")
except Exception as e:
    print(f"  ERRO: {e}")
