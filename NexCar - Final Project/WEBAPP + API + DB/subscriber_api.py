# subscriber_api.py
"""
Escuta tópicos MQTT simulados e reais, agrega os valores obrigatórios
como time, temperature, humidity, etc., e envia-os para a API NEXCAR
via HTTP POST.

Agora **auto‑renova o JWT** sem precisar de refresh‑token: quando o
servidor devolver 401 ou quando o campo `exp` indicar menos de 5 min
até expirar, o script faz _login_ outra vez em /auth/login com as
credenciais do utilizador «iot», obtém um novo **access‑token** e segue.

Requisitos:
  - variáveis de ambiente
      • NEXCAR_USER       (ex.: "admin")
      • NEXCAR_PASSWORD   (ex.: "admin")
  - requests               (pip install requests)
  - paho-mqtt              (pip install paho-mqtt)
  - PyJWT                  (pip install PyJWT)

Se preferir continuar a exportar manualmente o `NEXCAR_JWT`, basta
pô‑lo no ambiente; o script só vai fazer _login_ quando esse token
expirar.
"""

import os
import time
import jwt  # PyJWT
import requests
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from typing import Dict, Any

# ───────────────────────────────────────────
#  Parametrização
# ───────────────────────────────────────────
BROKER_HOST = "192.168.0.103"
BROKER_PORT = 1883
API_BASE    = "http://192.168.0.103:3000/api/v1"
LOGIN_URL   = f"{API_BASE}/auth/login"

USER        = os.getenv("NEXCAR_USER", "admin")
PASSWORD    = os.getenv("NEXCAR_PASSWORD", "admin")

JWT_TOKEN   = os.getenv("NEXCAR_JWT")
HEADERS     = {"Content-Type": "application/json"}

exp_ts: float | None = None     # Unix‑epoch da expiração

# ───────────────────────────────────────────
#  Obter/renovar token
# ───────────────────────────────────────────

def login() -> None:
    """Faz login e actualiza HEADERS + exp_ts."""
    global JWT_TOKEN, exp_ts

    print("🔐  A obter novo access‑token …")
    try:
        r = requests.post(LOGIN_URL, json={"username": USER, "password": PASSWORD}, timeout=5)
        r.raise_for_status()
        JWT_TOKEN = r.json()["access_token"]
        HEADERS["Authorization"] = f"Bearer {JWT_TOKEN}"
        exp_ts = jwt.decode(JWT_TOKEN, options={"verify_signature": False})["exp"]
        print("     Obtido; expira em:", datetime.utcfromtimestamp(exp_ts))
    except requests.RequestException as e:
        raise SystemExit("✖  Falha de login: " + str(e))

# tentamos login já se não houver token no ambiente
if not JWT_TOKEN:
    login()
else:
    HEADERS["Authorization"] = f"Bearer {JWT_TOKEN}"
    try:
        exp_ts = jwt.decode(JWT_TOKEN, options={"verify_signature": False})["exp"]
    except Exception:
        exp_ts = None  # não tem exp; trataremos via 401


def ensure_valid_token() -> None:
    """Renova pró‑ativamente <5 min antes do exp."""
    if exp_ts and time.time() > exp_ts - 300:
        login()

# ───────────────────────────────────────────
#  Perfil dos tópicos
# ───────────────────────────────────────────
PERFIS = {
    "sim": {
        "map": {
            "temperatura": "temperature",
            "humidade":    "humidity",
            "fogo":        "fire",
            "colisao":     "colisao",
            "chuva":       "rain",
            "distancia":   "distance",
            "movimento":   "movement",
            "timestamp":   "time",
            "car_id":      "car_id",
        },
        "required": {"time","temperature","humidity","fire",
                     "colisao","rain","distance","movement","car_id"},
        "parse": lambda k,v: float(v) if k in ["temperature","humidity","colisao"] else int(v) if k!="time" else v,
    },
    "real": {
        "map": {
            "temperatura": "temperature",
            "humidade":    "humidity",
            "chama":       "fire",
            "chuva":       "rain",
            "distancia":   "distance",
            "movimento":   "movement",
            "colisao":     "colisao"
        },
        "required": {"temperature","humidity","fire","rain","distance","movement"},
        "parse": lambda k,v: float(v) if k in ["temperature","humidity"] else int(v),
        "defaults": {"car_id": 1},
    }
}

TOPICS = [("/simulados", "sim"), ("nexcar/sensor", "real")]

buffers: Dict[str, Dict[Any, Dict[str, Any]]] = {"sim": {}, "real": {}}

# ───────────────────────────────────────────
#  Função para enviar dados à API
# ───────────────────────────────────────────

def enviar_api(car_id: int, dados: dict):
    dados.setdefault("time", datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z")

    ensure_valid_token()  # renova se estiver perto do fim

    try:
        r = requests.post(f"{API_BASE}/cars/{car_id}/sensors", headers=HEADERS, json=dados, timeout=5)
        if r.status_code == 401:
            print("⚠  401 recebido; a tentar novo login …")
            login()
            r = requests.post(f"{API_BASE}/cars/{car_id}/sensors", headers=HEADERS, json=dados, timeout=5)
        r.raise_for_status()
        print(f"✔  POST /cars/{car_id}/sensors  → {r.status_code}")
    except requests.RequestException as e:
        print("✖ erro API:", e, "\n payload:", dados)

# ───────────────────────────────────────────
#  Callbacks MQTT
# ───────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    print("MQTT ligado.")
    for base, _ in TOPICS:
        client.subscribe(base + "/#")
        print(f"  ↳ subscrito {base}/#")


def on_message(client, userdata, msg):
    for base, perfil in TOPICS:
        if msg.topic.startswith(base + "/"):
            tratar(perfil, base, msg)
            break

def tratar(perfil, base, msg):
    cfg = PERFIS[perfil]
    suf = msg.topic[len(base) + 1:]
    if suf not in cfg["map"]:
        return

    campo = cfg["map"][suf]
    raw   = msg.payload.decode().strip()
    try:
        valor = cfg["parse"](campo, raw)
    except ValueError:
        return

    if perfil == "sim":
        buf = buffers["sim"].setdefault("default", {})
    else:
        car_id = valor if campo == "car_id" else cfg.get("defaults", {}).get("car_id", 0)
        buf = buffers["real"].setdefault(car_id, {})

    buf[campo] = valor
    for k, v in cfg.get("defaults", {}).items():
        buf.setdefault(k, v)

    if cfg["required"].issubset(buf.keys()):
        if perfil == "sim":
            dest_id = buf.get("car_id")
            enviar_api(dest_id, buf.copy())
            buffers["sim"].clear()
        else:
            enviar_api(car_id, buf.copy())
            buffers["real"][car_id] = {}

# ───────────────────────────────────────────
#  Execução principal
# ───────────────────────────────────────────

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"Ligando a {BROKER_HOST}:{BROKER_PORT} …")
client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_forever()
