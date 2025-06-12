#include <Wire.h>
#include <Adafruit_SHT31.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <time.h>

// Configurações WiFi
#define WIFI_SSID "LAP3"
#define WIFI_PASS "LAP3LAP3"

// Configurações do MQTT
// Se o broker estiver no mesmo dispositivo que o ESP8266, use "127.0.0.1"
// Caso contrário, use o IP do broker, por exemplo, "192.168.0.100"
const char* mqtt_server = "192.168.0.103";  
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Configurações NTP (opcional, para sincronizar o horário se precisar)
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;
const int daylightOffset_sec = 0;

// Instância do sensor SHT31
Adafruit_SHT31 sht31 = Adafruit_SHT31();

// Definições dos pinos dos sensores e atuadores
#define FLAME_SENSOR_PIN_DIGITAL D7  // Sensor de chama (entrada digital)
#define TRIG_PIN D6                  // Sensor ultrassônico trig (saída)
#define ECHO_PIN D5                  // Sensor ultrassônico echo (entrada)
#define PIR_SENSOR_PIN D8            // Sensor de movimento PIR (entrada)
#define FAN_PIN D3                   // Pino de controle do ventilador (saída)
#define BUZZER_PIN D0                // Pino de controle do buzzer (saída)

// Variáveis para controle de temporização
unsigned long ultimoTempo = 0;
const unsigned long intervaloLeitura = 4000;  // Leitura a cada 4 segundos

// Variáveis para armazenar os dados dos sensores
float temperatura = 0.0;
float humidade = 0.0;
long distancia = 0;
bool flame = false;
bool movimento = false;

// Função para reconectar ao broker MQTT
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Tentando conexão MQTT...");
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(" conectado!");
      // Se desejar, inscreva-se em tópicos para receber comandos
      // mqttClient.subscribe("nexcar/comando");
    } else {
      Serial.print(" falhou, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

// Função para medir a distância com o sensor ultrassônico
long medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duracao = pulseIn(ECHO_PIN, HIGH);
  // Conversão: velocidade do som ~0.034 cm/us, dividindo por 2 (ida e volta)
  return duracao * 0.034 / 2;
}

void setup() {
  Serial.begin(115200);
  
  // Inicia a comunicação I2C com o SHT31 (pinos SDA e SCL)
  Wire.begin(4, 5);
  
  // Inicializa o sensor SHT31
  if (!sht31.begin(0x44)) {
    Serial.println("Erro ao iniciar o SHT31!");
    while (1);
  }
  
  // Configura os pinos dos sensores e atuadores
  pinMode(FLAME_SENSOR_PIN_DIGITAL, INPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(PIR_SENSOR_PIN, INPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  // Conecta à rede WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Conectando ao WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  
  // Sincroniza o horário via NTP (opcional)
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  
  // Configura o cliente MQTT e define o broker
  mqttClient.setServer(mqtt_server, 1883);
}

void loop() {
  // Reconnecta ao MQTT, se necessário
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  unsigned long tempoAtual = millis();
  if (tempoAtual - ultimoTempo >= intervaloLeitura) {
    ultimoTempo = tempoAtual;
    
    // Leitura dos sensores
    temperatura = sht31.readTemperature();
    humidade = sht31.readHumidity();
    distancia = medirDistancia();
    flame = (digitalRead(FLAME_SENSOR_PIN_DIGITAL) == LOW);
    movimento = (digitalRead(PIR_SENSOR_PIN) == HIGH);
    
    // Publica os dados via MQTT
    // Publicando temperatura
    String payload = String(temperatura, 2);
    mqttClient.publish("nexcar/sensor/temperatura", payload.c_str());
    
    // Publicando humidade
    payload = String(humidade, 2);
    mqttClient.publish("nexcar/sensor/humidade", payload.c_str());
    
    // Publicando distância (sensor ultrassônico)
    payload = String(distancia);
    mqttClient.publish("nexcar/sensor/distancia", payload.c_str());
    
    // Publicando estado do sensor de chama (1 = chama, 0 = sem chama)
    payload = flame ? "1" : "0";
    mqttClient.publish("nexcar/sensor/chama", payload.c_str());
    
    // Publicando estado do sensor de movimento (1 = movimento, 0 = sem movimento)
    payload = movimento ? "1" : "0";
    mqttClient.publish("nexcar/sensor/movimento", payload.c_str());
    
    // Debug: Imprime os dados no Serial Monitor
    Serial.print("Temperatura: ");
    Serial.print(temperatura);
    Serial.print(" °C | Humidade: ");
    Serial.print(humidade);
    Serial.print(" % | Distância: ");
    Serial.print(distancia);
    Serial.print(" cm | Chama: ");
    Serial.print(flame ? "SIM" : "NÃO");
    Serial.print(" | Movimento: ");
    Serial.println(movimento ? "SIM" : "NÃO");
  }

  // Controle do ventilador baseado na temperatura
  digitalWrite(FAN_PIN, (temperatura > 25.0) ? HIGH : LOW);

  // Controle do buzzer baseado na distância
  unsigned long now = millis();
  static unsigned long lastBuzzerToggle = 0;
  static bool buzzerState = false;
  if (distancia < 5) {
    digitalWrite(BUZZER_PIN, HIGH);  // Buzzer ligado constantemente
  } else if (distancia < 15) {
    if (now - lastBuzzerToggle >= 200) {
      buzzerState = !buzzerState;
      lastBuzzerToggle = now;
      digitalWrite(BUZZER_PIN, buzzerState ? HIGH : LOW);
    }
  } else {
    digitalWrite(BUZZER_PIN, LOW);
  }
}
