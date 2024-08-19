import paho.mqtt.client as mqtt
import json
from config import parking_data

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Terhubung ke broker MQTT")
        parking_data.mqtt_connected = True
        client.subscribe("pnj_csc_TA_kel4")  # Langganan topik MQTT
    else:
        print(f"Gagal terhubung, kode hasil: {rc}")
        parking_data.mqtt_connected = False

def on_disconnect(client, userdata, rc):
    print(f"Terputus dari broker MQTT, kode hasil: {rc}")
    parking_data.mqtt_connected = False

def on_message(client, userdata, msg):
    print(f"Pesan diterima dari topik {msg.topic}: {msg.payload.decode()}")

    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
        # Memperbarui data spot parkir berdasarkan pesan MQTT yang diterima
        parking_data.update_data(data)
    except json.JSONDecodeError as e:
        print(f"Error saat mendekode JSON dari payload MQTT: {e}")

def setup_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    try:
        client.connect("192.168.100.220", 1883, 10)
    except Exception as e:
        print(f"Gagal terhubung ke broker MQTT: {e}")
    client.loop_start()
    return client
