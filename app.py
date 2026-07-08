from flask import Flask, render_template, request, redirect
import paho.mqtt.client as mqtt
import psycopg2
import json
import threading

app = Flask(__name__)


MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_DATOS = "bateria/datos"      # topic donde el ESP8266 publica las lecturas
MQTT_TOPIC_CONTROL = "bateria/control"  # topic donde Flask envía el color a encender

# ---------------------------------------------------------
# Conexión directa a la base de datos PostgreSQL de Supabase
# ---------------------------------------------------------
SUPABASE_CONN = "postgresql://postgres:benjita0627@db.astssmcfsitssxazvamn.supabase.co:5432/postgres"

# Diccionario con la última lectura recibida, usado para mostrar en la página
datos = {
    "voltaje": 0,
    "corriente": 0,
    "temperatura": 0,
    "humedad": 0,
    "salud": 0,
    "estado": "Sin datos"
}

# Lista con el historial de lecturas, para el monitor estilo terminal
log_terminal = []


# -------
# Calcula el porcentaje de salud de la batería según el voltaje.
# Rango asumido para batería LiPo de una celda: 3.0V (vacía) a 4.2V (llena).

def calcular_salud(voltaje):
    salud = ((voltaje - 3.0) / (4.2 - 3.0)) * 100.0
    if salud > 100:
        salud = 100.0
    if salud < 0:
        salud = 0.0
    return round(salud, 1)


# ----
# Traduce el porcentaje de salud a un color de estado

def calcular_estado(salud):
    if salud > 60:
        return "VERDE"
    elif salud > 30:
        return "AMARILLO"
    else:
        return "ROJO"


# ---------
# Inserta una lectura en la tabla eventos_bateria de Supabase.
# La columna fecha se completa sola con la hora del servidor (DEFAULT NOW()).
def guardar_en_supabase(d):
    try:
        conn = psycopg2.connect(SUPABASE_CONN)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO eventos_bateria (voltaje, corriente, temperatura, humedad, salud, estado) VALUES (%s, %s, %s, %s, %s, %s)",
            (d["voltaje"], d["corriente"], d["temperatura"], d["humedad"], d["salud"], d["estado"])
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("Guardado en Supabase OK")
    except Exception as e:
        print("Error guardando en Supabase:", e)


# ---------------------------------------------------------
# Se ejecuta una vez cuando Flask logra conectarse al MQTT.
# Aquí se hace la suscripción al topic donde llegan los datos del ESP8266.

def on_connect(client, userdata, flags, rc):
    print("Conectado a MQTT con código:", rc)
    client.subscribe(MQTT_TOPIC_DATOS)


# ---------------------------------------------------------
# Se ejecuta cada vez que llega un mensaje nuevo al topic bateria/datos.
# Procesa el JSON, calcula salud y estado, actualiza los LEDs y guarda en Supabase.

def on_message(client, userdata, msg):
    global datos
    try:
        d = json.loads(msg.payload.decode())

        salud = calcular_salud(d["voltaje"])
        estado = calcular_estado(salud)

        d["salud"] = salud
        d["estado"] = estado
        datos = d

        # Envía el estado calculado de vuelta al ESP8266 para que actúe sobre los LEDs
        mqtt_client.publish(MQTT_TOPIC_CONTROL, estado)

        # Agrega la lectura al historial que se muestra en el monitor terminal
        linea = f"[{estado}] V={d['voltaje']}V I={d['corriente']}mA T={d['temperatura']}C H={d['humedad']}% Salud={salud}%"
        log_terminal.insert(0, linea)
        if len(log_terminal) > 50:
            log_terminal.pop()

        print("Procesado:", linea)

        guardar_en_supabase(d)

    except Exception as e:
        print("Error procesando mensaje:", e)


# Cliente MQTT y asignación de las funciones que reaccionan a conexión y mensajes
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


# ---------------------------------------------------------
# Corre en un hilo aparte para no bloquear el servidor Flask.

def conectar_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()


threading.Thread(target=conectar_mqtt, daemon=True).start()


# -------------
# Página principal: muestra los datos actuales y el historial

@app.route('/')
def index():
    return render_template('index.html', datos=datos, log=log_terminal)


# ---------------------------------------------------------
# Recibe el formulario de activación manual de LEDs y publica
# el color elegido directamente al ESP8266 por MQTT

@app.route('/control', methods=['POST'])
def control():
    color = request.form.get('color')
    if color in ["VERDE", "AMARILLO", "ROJO"]:
        mqtt_client.publish(MQTT_TOPIC_CONTROL, color)
        log_terminal.insert(0, f"[COMANDO MANUAL] LED forzado a: {color}")
    return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)