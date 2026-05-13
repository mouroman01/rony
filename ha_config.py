# ============================================================
#  ha_config.py — Configuration Home Assistant & Météo
#  R.O.N.Y — Personnalisez CE fichier selon votre installation
#  Compatible multilingue : réponses adaptées via language_manager
# ============================================================

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Connexion Home Assistant ──────────────────────────────────
HA_URL    = os.getenv("HA_URL", "")
HA_TOKEN  = os.getenv("HA_TOKEN", "")
HA_HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type" : "application/json",
}

# ── Ville et coordonnées par défaut ───────────────────────────
VILLE_PAR_DEFAUT = os.getenv("VILLE_DEFAUT", "Paris")
LAT_PAR_DEFAUT   = float(os.getenv("LAT_DEFAUT", "48.8566"))
LON_PAR_DEFAUT   = float(os.getenv("LON_DEFAUT", "2.3522"))

# ═══════════════════════════════════════════════════════════════
#  SECTION 1 — LUMIÈRES
# ═══════════════════════════════════════════════════════════════
PIECES_LUMIERES = {
    # Salon
    "salon"           : "light.salon",
    "living room"     : "light.salon",
    "sala"            : "light.salon",
    "plafond salon"   : "light.plafond",
    "canapes"         : "light.canapes",
    "lampadaire"      : "light.lampadaire",
    "lampe de chevet" : "light.lampe_de_chevet",

    # Cuisine / Kitchen / Cozinha
    "cuisine"         : "light.cuisine",
    "kitchen"         : "light.cuisine",
    "cozinha"         : "light.cuisine",

    # Bureau / Office / Escritório
    "bureau"          : "light.bureau",
    "office"          : "light.bureau",
    "escritorio"      : "light.bureau",
    "pc"              : "light.pc",

    # Chambre / Bedroom / Quarto
    "chambre"         : "light.chambre_parentale",
    "bedroom"         : "light.chambre_parentale",
    "quarto"          : "light.chambre_parentale",
    "parents"         : "light.chambre_parentale",

    # Global
    "toutes"          : "light.all",
    "tout"            : "light.all",
    "all"             : "light.all",
    "todas"           : "light.all",
    "tudo"            : "light.all",
    "alles"           : "light.all",
    "todas las luces" : "light.all",
}

# ═══════════════════════════════════════════════════════════════
#  SECTION 2 — PRISES CONNECTÉES
# ═══════════════════════════════════════════════════════════════
PIECES_PRISES = {
    "salon"     : "switch.prise_salon",
    "bureau"    : "switch.prise_bureau",
    "cuisine"   : "switch.prise_cuisine",
    "kitchen"   : "switch.prise_cuisine",
    "office"    : "switch.prise_bureau",
}

# ═══════════════════════════════════════════════════════════════
#  SECTION 3 — CAPTEURS TEMPÉRATURE
# ═══════════════════════════════════════════════════════════════
PIECES_CAPTEURS = {
    "salon"        : "sensor.salon_temperature",
    "living room"  : "sensor.salon_temperature",
    "sala"         : "sensor.salon_temperature",
    "chambre"      : "sensor.chambre_temperature",
    "bedroom"      : "sensor.chambre_temperature",
    "bureau"       : "sensor.bureau_temperature",
    "office"       : "sensor.bureau_temperature",
    "exterieur"    : "sensor.temperature_exterieure",
    "outside"      : "sensor.temperature_exterieure",
    "exterior"     : "sensor.temperature_exterieure",
    "dehors"       : "sensor.temperature_exterieure",
    "fora"         : "sensor.temperature_exterieure",
}

# ═══════════════════════════════════════════════════════════════
#  SECTION 4 — CAPTEURS HUMIDITÉ
# ═══════════════════════════════════════════════════════════════
PIECES_HUMIDITE = {
    "bureau"  : "sensor.bureau_humidite",
    "salon"   : "sensor.salon_humidite",
    "chambre" : "sensor.chambre_humidite",
}

# ═══════════════════════════════════════════════════════════════
#  SECTION 5 — COULEURS RGB (multilingue)
# ═══════════════════════════════════════════════════════════════
COULEURS_MAP = {
    # FR
    "rouge": [255, 0, 0], "bleu": [0, 0, 255], "vert": [0, 255, 0],
    "blanc": [255, 255, 255], "orange": [255, 140, 0], "violet": [148, 0, 211],
    "rose": [255, 20, 147], "jaune": [255, 255, 0], "cyan": [0, 255, 255],
    "magenta": [255, 0, 255], "turquoise": [64, 224, 208], "or": [255, 215, 0],
    # EN
    "red": [255, 0, 0], "blue": [0, 0, 255], "green": [0, 255, 0],
    "white": [255, 255, 255], "yellow": [255, 255, 0], "purple": [148, 0, 211],
    "pink": [255, 20, 147], "gold": [255, 215, 0], "silver": [192, 192, 192],
    # PT
    "vermelho": [255, 0, 0], "azul": [0, 0, 255], "verde": [0, 255, 0],
    "branco": [255, 255, 255], "amarelo": [255, 255, 0], "roxo": [148, 0, 211],
    "rosa": [255, 20, 147], "laranja": [255, 140, 0],
    # ES
    "rojo": [255, 0, 0], "azul": [0, 0, 255], "verde": [0, 255, 0],
    "blanco": [255, 255, 255], "amarillo": [255, 255, 0], "morado": [148, 0, 211],
    "naranja": [255, 140, 0],
    # DE
    "rot": [255, 0, 0], "blau": [0, 0, 255], "grün": [0, 255, 0],
    "weiß": [255, 255, 255], "gelb": [255, 255, 0], "lila": [148, 0, 211],
    "orange": [255, 140, 0],
}

# ── Codes météo Open-Meteo ────────────────────────────────────
CODES_METEO = {
    "fr": {
        0: "ciel dégagé", 1: "principalement clair", 2: "partiellement nuageux", 3: "couvert",
        45: "brouillard", 51: "bruine légère", 61: "pluie faible", 63: "pluie modérée", 65: "pluie forte",
        71: "neige faible", 73: "neige modérée", 75: "neige forte",
        80: "averses faibles", 95: "orage", 99: "orage violent",
    },
    "en": {
        0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "fog", 51: "light drizzle", 61: "light rain", 63: "moderate rain", 65: "heavy rain",
        71: "light snow", 73: "moderate snow", 75: "heavy snow",
        80: "light showers", 95: "thunderstorm", 99: "severe thunderstorm",
    },
    "pt": {
        0: "céu limpo", 1: "principalmente limpo", 2: "parcialmente nublado", 3: "nublado",
        45: "neblina", 51: "garoa leve", 61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte",
        71: "neve fraca", 73: "neve moderada", 75: "neve forte",
        80: "pancadas de chuva", 95: "tempestade", 99: "tempestade severa",
    },
    "es": {
        0: "cielo despejado", 1: "principalmente despejado", 2: "parcialmente nublado", 3: "nublado",
        45: "niebla", 51: "llovizna ligera", 61: "lluvia ligera", 63: "lluvia moderada", 65: "lluvia fuerte",
        71: "nieve ligera", 73: "nieve moderada", 75: "nieve fuerte",
        80: "chubascos", 95: "tormenta", 99: "tormenta severa",
    },
    "de": {
        0: "klarer Himmel", 1: "überwiegend klar", 2: "teilweise bewölkt", 3: "bedeckt",
        45: "Nebel", 51: "leichter Nieselregen", 61: "leichter Regen", 63: "mäßiger Regen", 65: "starker Regen",
        71: "leichter Schnee", 73: "mäßiger Schnee", 75: "starker Schnee",
        80: "Schauer", 95: "Gewitter", 99: "schweres Gewitter",
    },
}


def _get_desc_meteo(code: int, langue: str = "fr") -> str:
    table = CODES_METEO.get(langue, CODES_METEO["en"])
    return table.get(code, table.get(0, "unknown"))


# ═══════════════════════════════════════════════════════════════
#  FONCTIONS API HOME ASSISTANT
# ═══════════════════════════════════════════════════════════════

def ha_appeler_service(domaine, service, entity_id, donnees=None):
    if not HA_URL or not HA_TOKEN:
        print("[HA] URL ou token non configuré.")
        return False
    try:
        payload = {"entity_id": entity_id}
        if donnees:
            payload.update(donnees)
        r = requests.post(
            f"{HA_URL}/api/services/{domaine}/{service}",
            headers=HA_HEADERS, json=payload, timeout=5,
        )
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"[HA] Erreur service : {e}")
        return False


def ha_get_etat(entity_id, attribut=None):
    if not HA_URL or not HA_TOKEN:
        return "inconnu"
    try:
        r    = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=HA_HEADERS, timeout=5)
        data = r.json()
        if attribut:
            return data.get("attributes", {}).get(attribut, "inconnu")
        return data.get("state", "inconnu")
    except Exception as e:
        print(f"[HA] Erreur get etat : {e}")
        return "inconnu"


def ha_lumiere(entity_id, etat="on", luminosite=None, rgb=None):
    service = "toggle" if etat == "toggle" else ("turn_on" if etat == "on" else "turn_off")
    donnees = {}
    if etat == "on":
        if luminosite is not None:
            donnees["brightness"] = int(luminosite)
        if rgb is not None:
            donnees["rgb_color"] = rgb
    return ha_appeler_service("light", service, entity_id, donnees or None)


def ha_interrupteur(entity_id, etat="on"):
    service = "turn_on" if etat == "on" else "turn_off"
    return ha_appeler_service("switch", service, entity_id)


def ha_thermostat(entity_id, temperature):
    return ha_appeler_service("climate", "set_temperature", entity_id, {"temperature": temperature})


def ha_scene(scene_id):
    return ha_appeler_service("scene", "turn_on", scene_id)


# ═══════════════════════════════════════════════════════════════
#  FONCTIONS MÉTÉO
# ═══════════════════════════════════════════════════════════════

def geocoder_ville(ville: str):
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ville, "count": 1, "language": "fr", "format": "json"},
            timeout=5,
        )
        data = r.json()
        if data.get("results"):
            res = data["results"][0]
            return res["latitude"], res["longitude"], res.get("name", ville), res.get("country", "")
    except Exception as e:
        print(f"[MÉTÉO] Erreur géocodage : {e}")
    return None, None, ville, ""


def get_meteo_actuelle(ville: str = None, langue: str = "fr") -> str:
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, pays = geocoder_ville(nom_ville)
        if lat is None:
            lat, lon, nom_affiche = LAT_PAR_DEFAUT, LON_PAR_DEFAUT, VILLE_PAR_DEFAUT

        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude" : lat, "longitude": lon,
                "current"  : "temperature_2m,weathercode,wind_speed_10m,relative_humidity_2m",
                "timezone" : "auto",
                "forecast_days": 1,
            },
            timeout=8,
        )
        data = r.json()
        cur  = data["current"]
        code = cur.get("weathercode", 0)
        desc = _get_desc_meteo(code, langue)
        temp = round(float(cur.get("temperature_2m", 0)))

        templates = {
            "fr": f"À {nom_affiche}, il fait {temp}°C et le ciel est {desc}.",
            "en": f"In {nom_affiche}, it's {temp}°C and {desc}.",
            "pt": f"Em {nom_affiche}, está {temp}°C e o tempo está {desc}.",
            "es": f"En {nom_affiche}, hace {temp}°C y el cielo está {desc}.",
            "de": f"In {nom_affiche} sind es {temp}°C und der Himmel ist {desc}.",
            "it": f"A {nom_affiche} ci sono {temp}°C e il cielo è {desc}.",
        }
        return templates.get(langue, templates["en"])
    except Exception as e:
        print(f"[MÉTÉO] Erreur : {e}")
        errors = {"fr": "Impossible de récupérer la météo.", "en": "Unable to get weather.", "pt": "Não foi possível obter o clima."}
        return errors.get(langue, errors["en"])


def get_meteo_previsions(ville: str = None, jours: int = 3, langue: str = "fr") -> str:
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, _ = geocoder_ville(nom_ville)
        if lat is None:
            lat, lon, nom_affiche = LAT_PAR_DEFAUT, LON_PAR_DEFAUT, VILLE_PAR_DEFAUT

        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude"    : lat, "longitude": lon,
                "daily"       : "temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum",
                "timezone"    : "auto",
                "forecast_days": jours,
            },
            timeout=8,
        )
        data  = r.json()
        daily = data["daily"]
        lignes = []
        for i in range(min(jours, len(daily["weathercode"]))):
            date  = daily["time"][i]
            tmax  = round(daily["temperature_2m_max"][i])
            tmin  = round(daily["temperature_2m_min"][i])
            desc  = _get_desc_meteo(daily["weathercode"][i], langue)
            pluie = daily.get("precipitation_sum", [0]*jours)[i] or 0
            ligne = f"{date}: {tmin}–{tmax}°C, {desc}"
            if pluie > 0:
                ligne += f", {round(pluie)}mm"
            lignes.append(ligne)

        return f"{nom_affiche} — " + " | ".join(lignes)
    except Exception as e:
        print(f"[MÉTÉO PRÉV.] Erreur : {e}")
        return "Prévisions indisponibles."
