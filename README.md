# Monitoreo de Batería IoT

Proyecto de la asignatura DCSH01, Evaluación Sumativa 3. Sistema que mide el estado de una batería en tiempo real y muestra los datos en una página web, guardando cada lectura en una base de datos en la nube.

## Qué hace el sistema

Una tarjeta NodeMCU ESP8266 tiene conectados dos sensores: un INA219, que mide el voltaje y la corriente que está entregando la batería, y un DHT11, que mide temperatura y humedad del ambiente donde está el sistema.

Cada tres segundos, el ESP8266 toma una lectura de estos sensores y la envía por MQTT a un broker Mosquitto instalado en una máquina virtual con AmogOS. Un servidor Flask, que corre en la misma máquina, recibe estos datos, calcula el porcentaje de salud de la batería según el voltaje, y decide un estado: verde si la batería está bien, amarillo si está a la mitad, o rojo si está baja.

Ese estado se envía de vuelta al ESP8266 por MQTT, que prende uno de tres LEDs físicos según corresponda. También se puede forzar manualmente cualquiera de los tres colores desde un formulario en la página web, sin necesidad de tocar el código ni usar JavaScript.

Cada lectura que llega se guarda en una tabla de Supabase (base de datos PostgreSQL en la nube), con fecha y hora exacta, para tener un historial de cómo se comportó la batería con el tiempo.

La página web muestra los datos actuales y un panel estilo consola de terminal con el historial de las últimas lecturas recibidas.

## Justificación del uso de la tarjeta

Como el proyecto se desarrolló de forma individual, se usa una sola tarjeta NodeMCU ESP8266, que cumple todos los roles necesarios: lectura de sensores, cálculo local no aplica (el cálculo de salud se dejó en el lado de Flask/Python para mantener el código del microcontrolador simple), envío de datos por MQTT, recepción de comandos de control y actuación sobre los LEDs. No se usó una segunda tarjeta porque el número de integrantes (1) es igual al número de tarjetas disponibles, cumpliendo el requisito de la pauta.

## Componentes usados

- NodeMCU ESP8266
- Sensor INA219 (voltaje y corriente)
- Sensor DHT11 (temperatura y humedad)
- 3 LEDs (verde, amarillo, rojo) con resistencias de 220 a 330 ohms
- Máquina virtual con AmogOS, Mosquitto y Python/Flask

## Cómo ejecutar el proyecto

1. Cargar el código `bateria.ino` en el NodeMCU desde Arduino IDE, ajustando el SSID, la contraseña de WiFi y la IP del broker Mosquitto.
2. Instalar Mosquitto en la máquina virtual y dejarlo escuchando en el puerto 1883 para toda la red (no solo localhost).
3. Crear un entorno virtual de Python e instalar las dependencias:
4. Crear en Supabase la tabla `eventos_bateria` con la siguiente estructura (voltaje, corriente, temperatura, humedad, salud, estado, fecha), y copiar el connection string del proyecto.
5. Configurar la variable de conexión a Supabase en `app.py`.
6. Ejecutar `python3 app.py` desde la carpeta del proyecto.
7. Abrir un navegador en la misma red y entrar a la IP de la máquina virtual en el puerto 5000, por ejemplo `http://192.168.100.34:5000`.
