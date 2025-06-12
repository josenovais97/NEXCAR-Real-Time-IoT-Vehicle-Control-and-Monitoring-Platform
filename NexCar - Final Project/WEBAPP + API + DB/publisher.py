import numpy as np
import sys
from datetime import datetime, timedelta, timezone
import paho.mqtt.client as mqtt

# -------------------------------------------------
# CONFIGURAÇÕES MQTT
# -------------------------------------------------
BROKER_HOST = "localhost"  # IP ou hostname do broker
BROKER_PORT = 1883
TOPIC_BASE = "/simulados"   # prefixo dos tópicos

# -------------------------------------------------
# Obter o car_id via argumento de linha de comando
# -------------------------------------------------
if len(sys.argv) > 1:
    try:
        CAR_ID = int(sys.argv[1])
    except ValueError:
        print("ERRO: O argumento deve ser um número inteiro representando o ID do carro.")
        sys.exit(1)
else:
    CAR_ID = 1  # se não for passado via cmd

print(f"A gerar dados para car_id={CAR_ID}")

# -------------------------------------------------
# Conectar no broker MQTT
# -------------------------------------------------
client = mqtt.Client()
try:
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()  # Inicia loop p/ publicar
    print(f"Conectado ao broker MQTT em {BROKER_HOST}:{BROKER_PORT}")
except Exception as e:
    print(f"ERRO ao conectar ao broker MQTT: {e}")
    sys.exit(1)

# -------------------------------------------------
# Função para gerar valores simulados
# -------------------------------------------------
def gerar_valores(timestamp_atual, ultimo_valores):
    temperature = round(ultimo_valores["temperature"] + np.random.uniform(-0.2, 0.2), 2)
    temperature = np.clip(temperature, 15, 26)

    humidity = round(ultimo_valores["humidity"] + np.random.uniform(-0.2, 0.2), 2)
    humidity = np.clip(humidity, 50, 60)

    dados = {
        "time": timestamp_atual.isoformat(timespec='seconds').replace('+00:00', 'Z'),
        "temperature": temperature,
        "humidity": humidity,
        "fire": int(np.random.choice([0, 1], p=[0.9, 0.1])),
        "colisao": int(np.random.choice([0, 1], p=[0.9, 0.1])),
        "rain": int(np.random.choice([0, 1], p=[0.7, 0.3])),
        "distance": int(round(np.random.uniform(2, 170))),
        "movement": int(np.random.choice([0, 1], p=[0.8, 0.2])),
        "car_id": CAR_ID
    }
    return dados

# -------------------------------------------------
# Configuração de simulação
# -------------------------------------------------
NUM_REGISTROS = 50
timestamp_inicial = datetime.now(timezone.utc)

ultimo_valores = {
    "temperature": np.random.uniform(15, 26),
    "humidity": np.random.uniform(50, 60)
}

# -------------------------------------------------
# Gerar e publicar dados simulados
# -------------------------------------------------
for _ in range(NUM_REGISTROS):
    novos_dados = gerar_valores(timestamp_inicial, ultimo_valores)

    # Publicar cada campo em seu tópico
    client.publish(f"{TOPIC_BASE}/temperatura", str(novos_dados["temperature"]))
    client.publish(f"{TOPIC_BASE}/humidade", str(novos_dados["humidity"]))
    client.publish(f"{TOPIC_BASE}/fogo", str(novos_dados["fire"]))
    client.publish(f"{TOPIC_BASE}/colisao", str(novos_dados["colisao"]))
    client.publish(f"{TOPIC_BASE}/chuva", str(novos_dados["rain"]))
    client.publish(f"{TOPIC_BASE}/distancia", str(novos_dados["distance"]))
    client.publish(f"{TOPIC_BASE}/movimento", str(novos_dados["movement"]))
    client.publish(f"{TOPIC_BASE}/timestamp", novos_dados["time"])
    client.publish(f"{TOPIC_BASE}/car_id", str(novos_dados["car_id"]))

    # Atualiza valores base para próxima iteração
    ultimo_valores["temperature"] = novos_dados["temperature"]
    ultimo_valores["humidity"] = novos_dados["humidity"]

    # Incrementa o tempo em 2 segundos
    timestamp_inicial += timedelta(seconds=2)

# Finalizar
client.loop_stop()
client.disconnect()
print(f"{NUM_REGISTROS} publicações concluídas em {BROKER_HOST}:{BROKER_PORT}")
