# ============================================================
#  camera_module.py — Câmera, Reconhecimento Facial e Objetos
#  R.O.N.Y — OpenCV + YOLO + Gemini Vision
#
#  Capacidades:
#    • Captura da webcam
#    • Detecção de rostos (local, Haar Cascade — sem internet)
#    • Reconhecimento de rostos conhecidos (salvo em rostos/)
#    • Detecção de objetos (YOLOv8 nano — auto-download ~6 MB)
#    • Análise de cena completa via Gemini Vision
#    • Respostas em voz em 5+ idiomas
# ============================================================

import io
import time
import base64
import asyncio
import json
from pathlib import Path
from typing import Optional

# ── Diretórios ────────────────────────────────────────────────
from rony_paths import RONY_DIR, ROSTOS_DIR, CAPTURES_DIR as CAPTURAS_DIR
# As pastas já foram criadas pelo rony_paths na importação

# ── Banco de rostos (LBPH — OpenCV nativo, sem dependências extras) ──
_banco_nomes: list[str]  = []    # nome[i] corresponde ao label i
_banco_label: dict[str, int] = {} # nome → label int
_modelo_lbph = None              # cv2.face.LBPHFaceRecognizer
_banco_carregado = False

# ── Detecção de dependências ──────────────────────────────────
try:
    import cv2
    CV2_OK = True
    # Cascades incluídos no OpenCV — sem download
    _CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    _FACE_CASCADE = cv2.CascadeClassifier(_CASCADE_PATH)
    _EYE_CASCADE  = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_eye.xml"
    )
    # LBPH disponível em opencv-contrib-python
    LBPH_OK = hasattr(cv2, "face")
except ImportError:
    CV2_OK        = False
    LBPH_OK       = False
    _FACE_CASCADE = None
    _EYE_CASCADE  = None
    _CASCADE_PATH = None
    print("[CAMERA] OpenCV nao instalado — instale com: pip install opencv-contrib-python")

try:
    import face_recognition as _fr
    FR_OK = True
except ImportError:
    _fr   = None
    FR_OK = False

try:
    from ultralytics import YOLO as _YOLO
    YOLO_OK = True
except ImportError:
    _YOLO   = None
    YOLO_OK = False

try:
    from PIL import Image as _PILImage
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Modelo YOLO (carregado uma só vez) ────────────────────────
_modelo_yolo = None


def _carregar_yolo():
    """Carrega o YOLOv8 nano (download automático ~6 MB na 1ª vez)."""
    global _modelo_yolo
    if _modelo_yolo is not None:
        return _modelo_yolo
    if not YOLO_OK:
        return None
    try:
        _modelo_yolo = _YOLO("yolov8n.pt")   # nano — rápido e leve
        print("[CAMERA] YOLOv8n carregado.")
        return _modelo_yolo
    except Exception as e:
        print(f"[CAMERA] Erro ao carregar YOLO: {e}")
        return None


# ─────────────────────────────────────────────────────────────
#  CAPTURA DA CÂMERA
# ─────────────────────────────────────────────────────────────

def capturar_camera(indice: int = 0, tentativas: int = 3) -> Optional[bytes]:
    """
    Captura um frame da webcam e retorna como bytes JPEG.
    indice: índice da câmera (0 = padrão).
    """
    if not CV2_OK:
        return None
    for _ in range(tentativas):
        cap = cv2.VideoCapture(indice, cv2.CAP_DSHOW)  # CAP_DSHOW = mais rápido no Windows
        if not cap.isOpened():
            cap = cv2.VideoCapture(indice)             # fallback
        if not cap.isOpened():
            continue
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # Descarta alguns frames para a câmera calibrar
            for _ in range(3):
                cap.read()
            ret, frame = cap.read()
            if ret and frame is not None:
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                return buf.tobytes()
        except Exception as e:
            print(f"[CAMERA] Erro ao capturar: {e}")
        finally:
            cap.release()
    print("[CAMERA] Não foi possível acessar a câmera.")
    return None


def capturar_e_salvar(indice: int = 0) -> Optional[Path]:
    """Captura e salva foto na pasta captures/."""
    dados = capturar_camera(indice)
    if not dados:
        return None
    ts   = int(time.time())
    path = CAPTURAS_DIR / f"camera_{ts}.jpg"
    path.write_bytes(dados)
    print(f"[CAMERA] Foto salva: {path}")
    return path


def _bytes_para_frame(img_bytes: bytes):
    """Converte bytes JPEG em numpy array (frame OpenCV)."""
    import numpy as np
    arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


# ─────────────────────────────────────────────────────────────
#  DETECÇÃO DE ROSTOS (local, sem internet)
# ─────────────────────────────────────────────────────────────

def detectar_rostos(img_bytes: bytes) -> list[dict]:
    """
    Detecta rostos usando Haar Cascade (OpenCV built-in).
    Retorna lista de dicts com x, y, largura, altura.
    """
    if not CV2_OK or img_bytes is None:
        return []
    try:
        frame = _bytes_para_frame(img_bytes)
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostos = _FACE_CASCADE.detectMultiScale(
            cinza,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        resultado = []
        for (x, y, w, h) in rostos:
            resultado.append({"x": int(x), "y": int(y), "largura": int(w), "altura": int(h)})
        return resultado
    except Exception as e:
        print(f"[CAMERA] Erro Haar: {e}")
        return []


def contar_rostos(img_bytes: bytes) -> int:
    """Conta quantos rostos aparecem na imagem."""
    return len(detectar_rostos(img_bytes))


# ─────────────────────────────────────────────────────────────
#  RECONHECIMENTO DE ROSTOS CONHECIDOS
#  Estratégia em camadas:
#    1. LBPH (OpenCV contrib) — offline, sem dependências extras
#    2. face_recognition (dlib) — mais preciso, se disponível
# ─────────────────────────────────────────────────────────────

def _extrair_rosto_cinza(frame, x: int, y: int, w: int, h: int,
                          tam: int = 128):
    """Recorta e normaliza o rosto para o LBPH."""
    margem = int(max(w, h) * 0.1)
    x0 = max(0, x - margem);  y0 = max(0, y - margem)
    x1 = min(frame.shape[1], x + w + margem)
    y1 = min(frame.shape[0], y + h + margem)
    rosto = frame[y0:y1, x0:x1]
    cinza = cv2.cvtColor(rosto, cv2.COLOR_BGR2GRAY) if len(rosto.shape) == 3 else rosto
    return cv2.resize(cinza, (tam, tam))


def _inicializar_banco() -> None:
    """
    Lê as fotos da pasta rostos/ e treina o modelo LBPH.
    Também carrega encodings face_recognition se disponível.
    """
    global _banco_nomes, _banco_label, _modelo_lbph, _banco_carregado
    _banco_nomes  = []
    _banco_label  = {}
    _banco_carregado = True

    fotos = list(ROSTOS_DIR.glob("*.jpg")) + list(ROSTOS_DIR.glob("*.png"))
    if not fotos:
        return

    import numpy as np

    # ── LBPH (sempre disponível com opencv-contrib) ───────────
    if CV2_OK and LBPH_OK:
        imagens_lbph: list = []
        labels_lbph:  list = []
        label_idx = 0
        for foto in fotos:
            nome = foto.stem
            if nome not in _banco_label:
                _banco_label[nome] = label_idx
                _banco_nomes.append(nome)
                label_idx += 1
            label = _banco_label[nome]
            try:
                img   = cv2.imread(str(foto))
                cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # Detecta rosto na foto de referência
                rostos_ref = _FACE_CASCADE.detectMultiScale(cinza, 1.1, 5, minSize=(60, 60))
                if len(rostos_ref) > 0:
                    x, y, w, h = rostos_ref[0]
                    recorte = _extrair_rosto_cinza(img, x, y, w, h)
                else:
                    # Sem detecção → usa a imagem inteira redimensionada
                    recorte = cv2.resize(cinza, (128, 128))
                imagens_lbph.append(recorte)
                labels_lbph.append(label)
            except Exception as e:
                print(f"[CAMERA] Erro ao processar '{nome}': {e}")

        if imagens_lbph:
            _modelo_lbph = cv2.face.LBPHFaceRecognizer_create(
                radius=2, neighbors=8, grid_x=8, grid_y=8, threshold=80.0
            )
            _modelo_lbph.train(imagens_lbph, np.array(labels_lbph))
            print(f"[CAMERA] LBPH treinado com {len(imagens_lbph)} rosto(s): {list(_banco_label.keys())}")

    # ── face_recognition (mais preciso, se instalado) ─────────
    if FR_OK:
        for foto in fotos:
            nome = foto.stem
            try:
                img_rgb = _fr.load_image_file(str(foto))
                encs    = _fr.face_encodings(img_rgb)
                if encs:
                    # Armazenamos encoding junto ao nome no dicionário existente
                    _banco_label[f"__enc_{nome}"] = encs[0]
            except Exception:
                pass


def aprender_rosto(nome: str, indice_camera: int = 0, n_fotos: int = 5) -> str:
    """
    Captura múltiplos frames pela câmera para aprender o rosto de uma pessoa.
    Treina o LBPH e, se disponível, salva encoding face_recognition.
    """
    if not CV2_OK:
        return "OpenCV não instalado. Instale com: pip install opencv-contrib-python"

    nome_limpo = nome.strip().lower().replace(" ", "_")
    pasta_pessoa = ROSTOS_DIR / nome_limpo
    pasta_pessoa.mkdir(exist_ok=True)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Não consegui acessar a câmera."

    fotos_salvas = 0
    tentativas   = 0
    try:
        while fotos_salvas < n_fotos and tentativas < 30:
            tentativas += 1
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            cinza  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rostos = _FACE_CASCADE.detectMultiScale(cinza, 1.1, 5, minSize=(60, 60))
            if len(rostos) == 0:
                time.sleep(0.15)
                continue
            x, y, w, h = rostos[0]
            recorte = _extrair_rosto_cinza(frame, x, y, w, h)
            path_foto = pasta_pessoa / f"{nome_limpo}_{fotos_salvas}.jpg"
            cv2.imwrite(str(path_foto), recorte)
            # Também salva foto colorida para referência visual
            if fotos_salvas == 0:
                cv2.imwrite(str(ROSTOS_DIR / f"{nome_limpo}.jpg"), frame)
            fotos_salvas += 1
            time.sleep(0.2)
    finally:
        cap.release()

    if fotos_salvas == 0:
        return f"Nenhum rosto detectado durante a captura. Olhe diretamente para a câmera."

    # Re-treina o modelo com todos os rostos
    _inicializar_banco()
    return f"Aprendi o rosto de {nome} com {fotos_salvas} amostras! Já posso reconhecer você."


def reconhecer_rostos(img_bytes: bytes) -> list[str]:
    """
    Reconhece rostos na imagem usando LBPH (e face_recognition se disponível).
    Retorna lista de nomes (ou 'desconhecido').
    """
    global _banco_carregado
    if not CV2_OK or img_bytes is None:
        return []
    if not _banco_carregado:
        _inicializar_banco()
    if not _banco_nomes and not FR_OK:
        return []

    try:
        import numpy as np
        frame  = _bytes_para_frame(img_bytes)
        cinza  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostos = _FACE_CASCADE.detectMultiScale(cinza, 1.1, 5, minSize=(60, 60))
        if len(rostos) == 0:
            return []

        nomes_detectados = []
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if FR_OK else None

        for (x, y, w, h) in rostos:
            nome_detectado = "desconhecido"

            # ── Tenta face_recognition primeiro (mais preciso) ─
            if FR_OK and rgb is not None:
                try:
                    loc   = [(y, x + w, y + h, x)]
                    encs  = _fr.face_encodings(rgb, loc)
                    if encs:
                        for nm, enc_key in [(n, f"__enc_{n}") for n in _banco_nomes]:
                            ref = _banco_label.get(enc_key)
                            if ref is None:
                                continue
                            dist = _fr.face_distance([ref], encs[0])[0]
                            if dist < 0.5:
                                nome_detectado = nm.replace("_", " ").title()
                                break
                except Exception:
                    pass

            # ── Fallback: LBPH ────────────────────────────────
            if nome_detectado == "desconhecido" and _modelo_lbph and _banco_nomes:
                try:
                    recorte = _extrair_rosto_cinza(frame, x, y, w, h)
                    label, confianca = _modelo_lbph.predict(recorte)
                    # Confiança LBPH: menor = melhor (0 = perfeito)
                    if confianca < 75 and 0 <= label < len(_banco_nomes):
                        nome_detectado = _banco_nomes[label].replace("_", " ").title()
                except Exception:
                    pass

            nomes_detectados.append(nome_detectado)

        return nomes_detectados
    except Exception as e:
        print(f"[CAMERA] Erro reconhecimento: {e}")
        return []


# ─────────────────────────────────────────────────────────────
#  DETECÇÃO DE OBJETOS (YOLOv8)
# ─────────────────────────────────────────────────────────────

# Tradução dos nomes YOLO (inglês) para PT/FR/ES/DE
_NOMES_OBJETOS: dict[str, dict[str, str]] = {
    "person":        {"pt": "pessoa",       "fr": "personne",   "es": "persona",   "de": "Person"},
    "bicycle":       {"pt": "bicicleta",    "fr": "vélo",       "es": "bicicleta", "de": "Fahrrad"},
    "car":           {"pt": "carro",        "fr": "voiture",    "es": "coche",     "de": "Auto"},
    "motorcycle":    {"pt": "moto",         "fr": "moto",       "es": "moto",      "de": "Motorrad"},
    "airplane":      {"pt": "avião",        "fr": "avion",      "es": "avión",     "de": "Flugzeug"},
    "bus":           {"pt": "ônibus",       "fr": "bus",        "es": "autobús",   "de": "Bus"},
    "train":         {"pt": "trem",         "fr": "train",      "es": "tren",      "de": "Zug"},
    "truck":         {"pt": "caminhão",     "fr": "camion",     "es": "camión",    "de": "LKW"},
    "boat":          {"pt": "barco",        "fr": "bateau",     "es": "barco",     "de": "Boot"},
    "chair":         {"pt": "cadeira",      "fr": "chaise",     "es": "silla",     "de": "Stuhl"},
    "couch":         {"pt": "sofá",         "fr": "canapé",     "es": "sofá",      "de": "Sofa"},
    "bed":           {"pt": "cama",         "fr": "lit",        "es": "cama",      "de": "Bett"},
    "dining table":  {"pt": "mesa",         "fr": "table",      "es": "mesa",      "de": "Tisch"},
    "toilet":        {"pt": "banheiro",     "fr": "toilettes",  "es": "inodoro",   "de": "Toilette"},
    "tv":            {"pt": "televisão",    "fr": "télévision", "es": "televisión","de": "TV"},
    "laptop":        {"pt": "notebook",     "fr": "ordinateur", "es": "portátil",  "de": "Laptop"},
    "mouse":         {"pt": "mouse",        "fr": "souris",     "es": "ratón",     "de": "Maus"},
    "keyboard":      {"pt": "teclado",      "fr": "clavier",    "es": "teclado",   "de": "Tastatur"},
    "cell phone":    {"pt": "celular",      "fr": "téléphone",  "es": "móvil",     "de": "Handy"},
    "microwave":     {"pt": "micro-ondas",  "fr": "micro-ondes","es": "microondas","de": "Mikrowelle"},
    "oven":          {"pt": "forno",        "fr": "four",       "es": "horno",     "de": "Ofen"},
    "refrigerator":  {"pt": "geladeira",    "fr": "réfrigérateur","es":"nevera",   "de": "Kühlschrank"},
    "sink":          {"pt": "pia",          "fr": "évier",      "es": "fregadero", "de": "Spüle"},
    "book":          {"pt": "livro",        "fr": "livre",      "es": "libro",     "de": "Buch"},
    "clock":         {"pt": "relógio",      "fr": "horloge",    "es": "reloj",     "de": "Uhr"},
    "vase":          {"pt": "vaso",         "fr": "vase",       "es": "jarrón",    "de": "Vase"},
    "bottle":        {"pt": "garrafa",      "fr": "bouteille",  "es": "botella",   "de": "Flasche"},
    "cup":           {"pt": "xícara",       "fr": "tasse",      "es": "taza",      "de": "Tasse"},
    "fork":          {"pt": "garfo",        "fr": "fourchette", "es": "tenedor",   "de": "Gabel"},
    "knife":         {"pt": "faca",         "fr": "couteau",    "es": "cuchillo",  "de": "Messer"},
    "spoon":         {"pt": "colher",       "fr": "cuillère",   "es": "cuchara",   "de": "Cuchara"},
    "bowl":          {"pt": "tigela",       "fr": "bol",        "es": "cuenco",    "de": "Schüssel"},
    "banana":        {"pt": "banana",       "fr": "banane",     "es": "plátano",   "de": "Banane"},
    "apple":         {"pt": "maçã",         "fr": "pomme",      "es": "manzana",   "de": "Apfel"},
    "pizza":         {"pt": "pizza",        "fr": "pizza",      "es": "pizza",     "de": "Pizza"},
    "cat":           {"pt": "gato",         "fr": "chat",       "es": "gato",      "de": "Katze"},
    "dog":           {"pt": "cachorro",     "fr": "chien",      "es": "perro",     "de": "Hund"},
    "bird":          {"pt": "pássaro",      "fr": "oiseau",     "es": "pájaro",    "de": "Vogel"},
    "backpack":      {"pt": "mochila",      "fr": "sac à dos",  "es": "mochila",   "de": "Rucksack"},
    "umbrella":      {"pt": "guarda-chuva", "fr": "parapluie",  "es": "paraguas",  "de": "Regenschirm"},
    "handbag":       {"pt": "bolsa",        "fr": "sac à main", "es": "bolso",     "de": "Handtasche"},
    "sports ball":   {"pt": "bola",         "fr": "ballon",     "es": "pelota",    "de": "Ball"},
    "remote":        {"pt": "controle remoto","fr":"télécommande","es":"control remoto","de":"Fernbedienung"},
    "scissors":      {"pt": "tesoura",      "fr": "ciseaux",    "es": "tijeras",   "de": "Schere"},
    "toothbrush":    {"pt": "escova de dente","fr":"brosse à dents","es":"cepillo de dientes","de":"Zahnbürste"},
}

def _traduzir_objeto(nome_en: str, lingua: str) -> str:
    """Traduz nome de objeto YOLO para o idioma da interface."""
    t = _NOMES_OBJETOS.get(nome_en, {})
    return t.get(lingua, t.get("pt", nome_en))


def detectar_objetos(img_bytes: bytes, confianca: float = 0.45,
                     lingua: str = "pt") -> list[dict]:
    """
    Detecta objetos via YOLOv8n.
    Retorna lista de dicts: {objeto, confianca, x, y, largura, altura}
    """
    modelo = _carregar_yolo()
    if not modelo or img_bytes is None:
        return []
    try:
        import numpy as np
        frame = _bytes_para_frame(img_bytes)
        results = modelo(frame, verbose=False, conf=confianca)
        objetos = []
        for r in results:
            for box in r.boxes:
                cls_id    = int(box.cls[0])
                nome_en   = modelo.names[cls_id]
                conf      = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                objetos.append({
                    "objeto"    : _traduzir_objeto(nome_en, lingua),
                    "objeto_en" : nome_en,
                    "confianca" : round(conf, 2),
                    "x": x1, "y": y1,
                    "largura"   : x2 - x1,
                    "altura"    : y2 - y1,
                })
        return objetos
    except Exception as e:
        print(f"[CAMERA] Erro YOLO: {e}")
        return []


def _agrupar_objetos(objetos: list[dict], lingua: str = "pt") -> dict[str, int]:
    """Agrupa objetos por tipo e conta ocorrências."""
    contagem: dict[str, int] = {}
    for o in objetos:
        nome = o["objeto"]
        contagem[nome] = contagem.get(nome, 0) + 1
    return contagem


# ─────────────────────────────────────────────────────────────
#  ANÁLISE COMPLETA EM VOZ
# ─────────────────────────────────────────────────────────────

def ver_camera_local(indice: int = 0, lingua: str = "pt") -> str:
    """
    Analisa câmera localmente: conta rostos e detecta objetos com YOLO.
    Retorna texto falado sem precisar de internet.
    """
    dados = capturar_camera(indice)
    if not dados:
        msgs = {
            "pt": "Não consegui acessar a câmera. Verifique se ela está conectada.",
            "fr": "Je n'ai pas pu accéder à la caméra. Vérifiez qu'elle est connectée.",
            "en": "I couldn't access the camera. Check if it's connected.",
            "es": "No pude acceder a la cámara. Comprueba que esté conectada.",
            "de": "Ich konnte nicht auf die Kamera zugreifen. Prüfe ob sie verbunden ist.",
        }
        return msgs.get(lingua, msgs["en"])

    partes = []

    # ── Rostos ────────────────────────────────────────────────
    n_rostos = contar_rostos(dados)
    if _banco_nomes:
        nomes = reconhecer_rostos(dados)
        conhecidos   = [n for n in nomes if n != "desconhecido"]
        desconhecidos = [n for n in nomes if n == "desconhecido"]
        if conhecidos:
            nomes_str = ", ".join(conhecidos)
            partes.append({
                "pt": f"Reconheço {nomes_str} na câmera.",
                "fr": f"Je reconnais {nomes_str} dans la caméra.",
                "en": f"I recognize {nomes_str} in the camera.",
                "es": f"Reconozco a {nomes_str} en la cámara.",
                "de": f"Ich erkenne {nomes_str} in der Kamera.",
            }.get(lingua, ""))
        if desconhecidos:
            nd = len(desconhecidos)
            partes.append({
                "pt": f"Há {nd} pessoa(s) desconhecida(s).",
                "fr": f"Il y a {nd} personne(s) inconnue(s).",
                "en": f"There are {nd} unknown person(s).",
                "es": f"Hay {nd} persona(s) desconocida(s).",
                "de": f"Es gibt {nd} unbekannte Person(en).",
            }.get(lingua, ""))
    elif n_rostos > 0:
        partes.append({
            "pt": f"Vejo {n_rostos} rosto(s) na câmera.",
            "fr": f"Je vois {n_rostos} visage(s) dans la caméra.",
            "en": f"I see {n_rostos} face(s) in the camera.",
            "es": f"Veo {n_rostos} rostro(s) en la cámara.",
            "de": f"Ich sehe {n_rostos} Gesicht(er) in der Kamera.",
        }.get(lingua, ""))
    else:
        partes.append({
            "pt": "Não vejo nenhum rosto.",
            "fr": "Je ne vois aucun visage.",
            "en": "I don't see any faces.",
            "es": "No veo ningún rostro.",
            "de": "Ich sehe keine Gesichter.",
        }.get(lingua, ""))

    # ── Objetos ───────────────────────────────────────────────
    if YOLO_OK:
        objetos = detectar_objetos(dados, lingua=lingua)
        contagem = _agrupar_objetos(objetos, lingua)
        # Remove pessoas do YOLO se já contou via Haar
        contagem.pop({
            "pt": "pessoa", "fr": "personne", "en": "person",
            "es": "persona", "de": "Person",
        }.get(lingua, "person"), None)
        if contagem:
            lista_obj = ", ".join(
                f"{v}x {k}" if v > 1 else k for k, v in sorted(contagem.items())
            )
            partes.append({
                "pt": f"Também vejo: {lista_obj}.",
                "fr": f"Je vois aussi : {lista_obj}.",
                "en": f"I also see: {lista_obj}.",
                "es": f"También veo: {lista_obj}.",
                "de": f"Ich sehe auch: {lista_obj}.",
            }.get(lingua, ""))

    if not partes:
        return {
            "pt": "A câmera está funcionando mas não identifiquei nada específico.",
            "fr": "La caméra fonctionne mais je n'ai rien identifié de précis.",
            "en": "The camera is working but I couldn't identify anything specific.",
            "es": "La cámara funciona pero no identifiqué nada específico.",
            "de": "Die Kamera funktioniert, aber ich habe nichts Spezifisches erkannt.",
        }.get(lingua, "")

    return " ".join(partes)


async def analisar_camera_ia(client_gemini, indice: int = 0,
                              prompt_extra: str = None, lingua: str = "pt") -> str:
    """
    Captura da câmera e envia para Gemini Vision para análise completa.
    Combina detecção local (rostos/objetos) com descrição rica da IA.
    """
    dados = capturar_camera(indice)
    if not dados:
        msgs = {
            "pt": "Não consegui acessar a câmera.",
            "fr": "Je n'ai pas pu accéder à la caméra.",
            "en": "I couldn't access the camera.",
            "es": "No pude acceder a la cámara.",
            "de": "Ich konnte nicht auf die Kamera zugreifen.",
        }
        return msgs.get(lingua, msgs["en"])

    # Análise local para complementar
    n_rostos = contar_rostos(dados)
    nomes_conhecidos = reconhecer_rostos(dados) if _banco_nomes else []

    contexto_local = ""
    if nomes_conhecidos:
        nomes_str = ", ".join(n for n in nomes_conhecidos if n != "desconhecido")
        if nomes_str:
            contexto_local = f" (Rostos identificados localmente: {nomes_str}.)"

    prompts = {
        "pt": f"Analise esta imagem capturada pela câmera em tempo real.{contexto_local} Descreva: quem ou o que você vê, ambiente, objetos presentes, e qualquer detalhe relevante. Seja natural e direto, como se estivesse descrevendo para um amigo." + (f" Foco especial em: {prompt_extra}." if prompt_extra else ""),
        "fr": f"Analyse cette image capturée par la caméra en temps réel.{contexto_local} Décris : qui ou quoi tu vois, l'environnement, les objets présents. Sois naturel et direct." + (f" Focus particulier sur : {prompt_extra}." if prompt_extra else ""),
        "en": f"Analyze this real-time camera image.{contexto_local} Describe: who or what you see, the environment, objects present. Be natural and direct." + (f" Special focus on: {prompt_extra}." if prompt_extra else ""),
        "es": f"Analiza esta imagen capturada por la cámara en tiempo real.{contexto_local} Describe: quién o qué ves, el ambiente, objetos presentes. Sé natural y directo." + (f" Enfoque especial en: {prompt_extra}." if prompt_extra else ""),
        "de": f"Analysiere dieses Echtzeit-Kamerabild.{contexto_local} Beschreibe: was oder wen du siehst, die Umgebung, vorhandene Objekte. Sei natürlich und direkt." + (f" Besonderer Fokus auf: {prompt_extra}." if prompt_extra else ""),
    }
    prompt_final = prompts.get(lingua, prompts["en"])

    try:
        import google.genai as genai
        from google.genai import types

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client_gemini.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=dados, mime_type="image/jpeg"),
                    prompt_final,
                ],
            ),
        )
        return response.text or ""
    except Exception as e:
        print(f"[CAMERA IA] Erro Gemini: {e}")
        # Fallback para análise local
        return ver_camera_local(indice, lingua)


async def ver_camera(client_gemini=None, indice: int = 0,
                     lingua: str = "pt", modo: str = "auto") -> str:
    """
    Ponto de entrada unificado para ver pela câmera.
    modo: 'auto' (IA se disponível, senão local), 'local', 'ia'
    """
    if modo == "ia" and client_gemini:
        return await analisar_camera_ia(client_gemini, indice, lingua=lingua)
    if modo == "local":
        return await asyncio.get_event_loop().run_in_executor(
            None, ver_camera_local, indice, lingua
        )
    # auto: usa IA se disponível
    if client_gemini:
        return await analisar_camera_ia(client_gemini, indice, lingua=lingua)
    return await asyncio.get_event_loop().run_in_executor(
        None, ver_camera_local, indice, lingua
    )


# ─────────────────────────────────────────────────────────────
#  FUNÇÕES DE VOZ PARA main.py
# ─────────────────────────────────────────────────────────────

async def resposta_o_que_voce_ve(client_gemini=None, lingua: str = "pt") -> str:
    """'O que você vê?' — análise completa da câmera."""
    return await ver_camera(client_gemini, lingua=lingua)


async def resposta_tem_alguem(lingua: str = "pt") -> str:
    """'Tem alguém aí?' — resposta focada em rostos."""
    dados = capturar_camera()
    if not dados:
        return {
            "pt": "Câmera indisponível no momento.",
            "fr": "Caméra indisponible pour l'instant.",
            "en": "Camera unavailable right now.",
            "es": "Cámara no disponible en este momento.",
            "de": "Kamera gerade nicht verfügbar.",
        }.get(lingua, "")

    n = contar_rostos(dados)
    nomes = reconhecer_rostos(dados) if _banco_nomes else []
    conhecidos = [n2 for n2 in nomes if n2 != "desconhecido"]

    if n == 0:
        return {
            "pt": "Não vejo nenhuma pessoa na câmera agora.",
            "fr": "Je ne vois personne dans la caméra en ce moment.",
            "en": "I don't see anyone in the camera right now.",
            "es": "No veo a nadie en la cámara ahora mismo.",
            "de": "Ich sehe gerade niemanden in der Kamera.",
        }.get(lingua, "")
    if conhecidos:
        nomes_str = ", ".join(conhecidos)
        return {
            "pt": f"Sim! Vejo {nomes_str} aqui.",
            "fr": f"Oui ! Je vois {nomes_str} ici.",
            "en": f"Yes! I see {nomes_str} here.",
            "es": f"¡Sí! Veo a {nomes_str} aquí.",
            "de": f"Ja! Ich sehe {nomes_str} hier.",
        }.get(lingua, "")
    return {
        "pt": f"Vejo {n} pessoa(s) mas não reconheço quem é.",
        "fr": f"Je vois {n} personne(s) mais je ne sais pas qui c'est.",
        "en": f"I see {n} person/people but I don't recognize who.",
        "es": f"Veo {n} persona(s) pero no sé quién es.",
        "de": f"Ich sehe {n} Person(en), weiß aber nicht wer.",
    }.get(lingua, "")


async def resposta_o_que_e_isso(client_gemini=None, objeto_hint: str = "",
                                 lingua: str = "pt") -> str:
    """'O que é isso?' — identifica objeto específico."""
    return await ver_camera(client_gemini, lingua=lingua,
                            modo="ia" if client_gemini else "local")


def status_camera(lingua: str = "pt") -> str:
    """Retorna status das capacidades da câmera."""
    ok = "OK"
    no = {"pt": "não instalado", "fr": "non installé", "en": "not installed",
          "es": "no instalado",  "de": "nicht installiert"}.get(lingua, "not installed")

    cam  = ok if CV2_OK  else no
    lbph = ok if (CV2_OK and LBPH_OK) else no
    fr   = ok if FR_OK   else f"{'opcional' if lingua=='pt' else 'optional'}"
    yolo = ok if YOLO_OK else no
    n    = len(_banco_nomes)

    return {
        "pt": f"Câmera: OpenCV {cam}, LBPH {lbph}, face_recognition {fr}, YOLO {yolo}. {n} rosto(s) treinado(s).",
        "fr": f"Caméra : OpenCV {cam}, LBPH {lbph}, face_recognition {fr}, YOLO {yolo}. {n} visage(s) appris.",
        "en": f"Camera: OpenCV {cam}, LBPH {lbph}, face_recognition {fr}, YOLO {yolo}. {n} trained face(s).",
        "es": f"Cámara: OpenCV {cam}, LBPH {lbph}, face_recognition {fr}, YOLO {yolo}. {n} rostro(s) entrenado(s).",
        "de": f"Kamera: OpenCV {cam}, LBPH {lbph}, face_recognition {fr}, YOLO {yolo}. {n} trainierte(s) Gesicht(er).",
    }.get(lingua, "")


# ─────────────────────────────────────────────────────────────
#  INICIALIZAÇÃO
# ─────────────────────────────────────────────────────────────

def inicializar_camera() -> None:
    """Inicializa o módulo: carrega banco de rostos e pré-aquece YOLO."""
    import threading
    # Carrega banco de rostos + treina LBPH
    _inicializar_banco()
    if YOLO_OK:
        # Pré-carrega YOLOv8 em background (evita delay no 1º uso)
        threading.Thread(target=_carregar_yolo, daemon=True).start()
    print(f"[CAMERA] CV2={CV2_OK} | LBPH={LBPH_OK} | FaceRec(dlib)={FR_OK} | YOLO={YOLO_OK} | Rostos treinados: {len(_banco_nomes)}")
