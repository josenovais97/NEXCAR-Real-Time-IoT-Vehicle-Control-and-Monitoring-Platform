#include <Adafruit_MPU6050.h>        // Biblioteca para o sensor MPU6050
#include <Adafruit_Sensor.h>         // Biblioteca base para sensores Adafruit
#include <Wire.h>                    // Biblioteca para comunicação I2C
#include <Servo.h>                   // Biblioteca para controle do servo
#include <ESP8266WiFi.h>             // Biblioteca para conexão WiFi no ESP8266
#include <PubSubClient.h>            // Biblioteca para conexão MQTT
#include <time.h>                    // Biblioteca para sincronização e manipulação de data/hora via NTP

// Definições dos pinos utilizados
#define SENSOR_CHUVA D2              // Pino digital conectado ao sensor de chuva
#define VCC_CHUVA D7                 // Pino para fornecer alimentação ao sensor de chuva
#define LDR_PIN 14                   // Pino analógico para o sensor de luz (LDR)
#define LED_PIN 12                   // Pino digital para controlar o LED

// Configuração de rede e MQTT
#define WIFI_SSID "LAP3"             // Nome da rede WiFi
#define WIFI_PASS "LAP3LAP3"         // Senha da rede WiFi
const char* mqtt_server = "192.168.0.103";  // IP do broker MQTT

// Instanciação dos objetos para o sensor MPU6050, servo e MQTT
Adafruit_MPU6050 mpu;
Servo meuServo;
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// DETECÇÃO DE COLISÃO
const float JERK_THRESHOLD = 100.0; // Limiar para variação de aceleração (jerk)
const float GYRO_THRESHOLD = 100.0; // Limiar para detecção de impacto via giroscópio
const int HIT_CONFIRMATION = 3;     // Número de leituras consecutivas para confirmar a colisão
int consecutiveHits = 0;

// Variáveis auxiliares para o cálculo do jerk
unsigned long lastTimeForCollision = 0;  // Para medir o intervalo entre leituras
float lastAccelX = 0, lastAccelY = 0, lastAccelZ = 0;

// Offsets de calibração do MPU6050
float accelOffsetX = 0, accelOffsetY = 0, accelOffsetZ = 0;

// Intervalos para operações (em milissegundos)
const unsigned long printInterval = 4000;  // Intervalo para leitura/impressão dos sensores
const unsigned long sendInterval  = 15000; // Intervalo para envio dos dados via MQTT

unsigned long startTime = 0;          // Tempo inicial para timestamp relativo
unsigned long nextPrintTime = 0;      // Próximo instante para impressão dos dados
unsigned long nextSendTime = 0;       // Próximo instante para envio dos dados via MQTT

// Variável para armazenar o valor atual da aceleração no eixo X (caso precise)
float currentAccelX = 0.0;

// Flag para evitar impressões repetidas do sensor de chuva
bool rainPrinted = false;

// Função para sincronização via NTP
void setupTime() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("A aguardar a sincronização do NTP...");
    delay(1000);
  }
  Serial.println("NTP sincronizado!");
}

// Calibração do MPU6050: coleta amostras para calcular os offsets
void calibrateSensor() {
  Serial.println("A calibrar o MPU6050...");
  float sumX = 0, sumY = 0, sumZ = 0;
  const int samples = 100;
  for (int i = 0; i < samples; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    sumX += a.acceleration.x;
    sumY += a.acceleration.y;
    sumZ += a.acceleration.z;
    delay(10);
  }
  accelOffsetX = sumX / samples;
  accelOffsetY = sumY / samples;
  accelOffsetZ = (sumZ / samples) - 9.81;
  Serial.println("Calibração concluída!");
}

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

void setup() {
  Serial.begin(115200);
  
  // Inicializa a comunicação I2C e o MPU6050
  Wire.begin(D4, D1);
  Serial.println("A iniciar MPU6050...");
  if (!mpu.begin()) {
    Serial.println("Erro ao encontrar MPU6050!");
    while (1) delay(10);
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);
  calibrateSensor();
  
  // Configura os pinos dos sensores e atuadores
  pinMode(SENSOR_CHUVA, INPUT);
  pinMode(VCC_CHUVA, OUTPUT);
  digitalWrite(VCC_CHUVA, HIGH);
  meuServo.attach(D3);  // Conecta o servo ao pino D3
  pinMode(LDR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  
  // Conecta-se à rede WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("A estabelecer ligação WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());
  
  // Sincroniza o horário via NTP
  setupTime();
  
  Serial.println("Sistema iniciado...");
  
  // Inicializa os timestamps
  startTime = millis();
  nextPrintTime = startTime;
  nextSendTime = startTime;
  lastTimeForCollision = millis();
  
  // Configura o cliente MQTT e define o broker
  mqttClient.setServer(mqtt_server, 1883);
}

void loop() {
  // Garante que o MQTT esteja conectado
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
  
  verificarColisao();
  verificarLuz();
  verificarChuva();
  
  // Envio de dados via MQTT a cada 15 segundos
  if (millis() >= nextSendTime) {
    enviarMQTT();
    nextSendTime += sendInterval;
  }
  
  // Impressão dos dados dos sensores (exceto chuva) a cada 4 segundos
  if (millis() >= nextPrintTime) {
    unsigned long timestamp = nextPrintTime - startTime;
    nextPrintTime += printInterval;
    
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    float accelX = a.acceleration.x - accelOffsetX;
    float accelY = a.acceleration.y - accelOffsetY;
    float accelZ = a.acceleration.z - accelOffsetZ;
    currentAccelX = accelX;
    
    int luz = digitalRead(LDR_PIN);
    
    Serial.print("["); Serial.print(timestamp); Serial.print(" ms] ");
    Serial.print("AccelX: "); Serial.print(accelX);
    Serial.print(" | AccelY: "); Serial.print(accelY);
    Serial.print(" | AccelZ: "); Serial.print(accelZ);
    Serial.print(" | Luz: "); Serial.println(luz ? "Claro" : "Escuro");
  }
  
  // Impressão imediata do sensor de chuva quando detecta chuva
  if (digitalRead(SENSOR_CHUVA) == LOW && !rainPrinted) {
    unsigned long rainTimestamp = millis() - startTime;
    Serial.print("["); Serial.print(rainTimestamp); Serial.print(" ms] ");
    Serial.println("Chuva detetada!");
    rainPrinted = true;
  }
  // Limpa a flag quando não há chuva
  if (digitalRead(SENSOR_CHUVA) == HIGH) {
    rainPrinted = false;
  }
}

// Função para enviar dados via MQTT
// Publica o valor do LDR, do sensor de chuva e, se desejar, a aceleração X
void enviarMQTT() {
  // Publicar sensor de chuva (1 = chuva, 0 = sem chuva)
  int waterDetected = (digitalRead(SENSOR_CHUVA) == LOW) ? 1 : 0;
  mqttClient.publish("nexcar/sensor/chuva", String(waterDetected).c_str());

  // Publicar LDR (1 = claro, 0 = escuro)
  int luz = digitalRead(LDR_PIN); 
  mqttClient.publish("nexcar/sensor/luz", String(luz).c_str());

  // (Opcional) publicar aceleração X no mesmo tópico de colisão? 
  // Se quiser mandar a aceleração no lugar do "1" ou "0", pode fazer:
  // mqttClient.publish("nexcar/sensor/colisao", String(currentAccelX, 2).c_str());

  // Log no Serial
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    char timeString[64];
    strftime(timeString, sizeof(timeString), "%Y-%m-%d %H:%M:%S", &timeinfo);
    Serial.print("["); Serial.print(timeString); Serial.print("] ");
    Serial.println("Dados (chuva/luz) enviados via MQTT!");
  } else {
    Serial.println("Dados (chuva/luz) enviados via MQTT! (Falha ao obter hora)");
  }
}

// Função para verificar colisões utilizando os dados do MPU6050
void verificarColisao() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  
  unsigned long currentTime = millis();
  float deltaTime = (currentTime - lastTimeForCollision) / 1000.0;
  lastTimeForCollision = currentTime;
  
  float correctedX = a.acceleration.x - accelOffsetX;
  float correctedY = a.acceleration.y - accelOffsetY;
  float correctedZ = a.acceleration.z - accelOffsetZ;
  currentAccelX = correctedX;
  
  float jerkX = abs((correctedX - lastAccelX) / deltaTime);
  float jerkY = abs((correctedY - lastAccelY) / deltaTime);
  float jerkZ = abs((correctedZ - lastAccelZ) / deltaTime);
  
  lastAccelX = correctedX;
  lastAccelY = correctedY;
  lastAccelZ = correctedZ;
  
  bool gyroImpact = (abs(g.gyro.x) > GYRO_THRESHOLD || 
                     abs(g.gyro.y) > GYRO_THRESHOLD || 
                     abs(g.gyro.z) > GYRO_THRESHOLD);
  
  if (jerkX > JERK_THRESHOLD || jerkY > JERK_THRESHOLD || jerkZ > JERK_THRESHOLD || gyroImpact) {
    consecutiveHits++;
  } else {
    consecutiveHits = 0;
  }
  
  // Se o número de leituras consecutivas for atingido, publicamos "1" no tópico de colisão
  if (consecutiveHits >= HIT_CONFIRMATION) {
    unsigned long collisionTime = millis() - startTime;
    Serial.print("["); Serial.print(collisionTime); Serial.println(" ms] COLISÃO DETECTADA! 🚨");

    // Publica o evento de colisão via MQTT (somente "1")
    mqttClient.publish("nexcar/sensor/colisao", "1");

    consecutiveHits = 0;
  }
}

// Função para verificar o sensor de chuva e acionar as escovas (servo)
void verificarChuva() {
  if (digitalRead(SENSOR_CHUVA) == LOW) {
    ativarEscovas();
  } else {
    meuServo.write(0);  // Garante que o servo pare se não houver chuva
  }
}

// Função para acionar as escovas (servo) em caso de chuva
void ativarEscovas() {
  meuServo.write(180);
  delay(1000);
  meuServo.write(0);
  delay(1000);
}

// Função para verificar o sensor de luz e controlar o LED
void verificarLuz() {
  int luz = digitalRead(LDR_PIN);
  digitalWrite(LED_PIN, luz ? LOW : HIGH);
}