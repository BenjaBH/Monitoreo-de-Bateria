#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_INA219.h>
#include <DHT.h>

// ---------------------------------------------------------
// Datos de la red WiFi y del broker MQTT
// ---------------------------------------------------------
const char* ssid = "TU_RED_WIFI";
const char* password = "TU_PASSWORD";
const char* mqtt_server = "192.168.100.34";
const int mqtt_port = 1883;

// Pines donde están conectados los LEDs de estado
const int LED_VERDE = D5;
const int LED_AMARILLO = D6;
const int LED_ROJO = D7;

// Pin de datos del sensor DHT11
#define DHTPIN D4
#define DHTTYPE DHT11

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_INA219 ina219;
DHT dht(DHTPIN, DHTTYPE);


// ---------------------------------------------------------
// Conecta la tarjeta a la red WiFi y espera hasta lograrlo

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado");
}


// ---------------------------------------------------------
// Se ejecuta cada vez que llega un mensaje al topic bateria/control.
// El mensaje es un texto simple: VERDE, AMARILLO o ROJO.
// Apaga los tres LEDs y enciende solo el que corresponde.

void callback(char* topic, byte* payload, unsigned int length) {
  String mensaje = "";
  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }
  Serial.println("Comando recibido: " + mensaje);

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARILLO, LOW);
  digitalWrite(LED_ROJO, LOW);

  if (mensaje == "VERDE") digitalWrite(LED_VERDE, HIGH);
  else if (mensaje == "AMARILLO") digitalWrite(LED_AMARILLO, HIGH);
  else if (mensaje == "ROJO") digitalWrite(LED_ROJO, HIGH);
}



void reconnect() {
  while (!client.connected()) {
    Serial.print("Conectando a MQTT...");
    if (client.connect("ESP8266_Bateria")) {
      Serial.println("conectado");
      client.subscribe("bateria/control");
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}


void setup() {
  Serial.begin(115200);

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARILLO, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  Wire.begin();       // inicia el bus I2C para el INA219
  ina219.begin();
  dht.begin();
}


void loop() {
  // Si se pierde la conexión MQTT, intenta reconectar antes de seguir
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Envía una lectura nueva cada 3 segundos
  static unsigned long lastMsg = 0;
  if (millis() - lastMsg > 3000) {
    lastMsg = millis();

    float voltaje = ina219.getBusVoltage_V();
    float corriente = ina219.getCurrent_mA();
    float temperatura = dht.readTemperature();
    float humedad = dht.readHumidity();

    // Arma el mensaje en formato JSON para que Flask lo pueda leer fácilmente
    String payload = "{";
    payload += "\"voltaje\":" + String(voltaje, 2) + ",";
    payload += "\"corriente\":" + String(corriente, 2) + ",";
    payload += "\"temperatura\":" + String(temperatura, 1) + ",";
    payload += "\"humedad\":" + String(humedad, 1);
    payload += "}";

    client.publish("bateria/datos", payload.c_str());
    Serial.println("Publicado: " + payload);
  }
}