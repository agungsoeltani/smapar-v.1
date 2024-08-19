from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt
import json
import cv2
import urllib.request
import numpy as np
import threading
import time
import signal
import sys
from util2 import Park_classifier  # Import kelas dari util2.py

# Flask Setup
app = Flask(__name__)

# MQTT Setup
mqtt_server = "192.168.100.220"
mqtt_topic = "pnj_csc_TA_kel4"
total_spots = 0
available_spots = 0
spots_json = {}
status_dict = {}

height_kotak = 80
width_kotak = 250

# Lock for thread-safe operations
lock = threading.Lock()

# Event untuk mengontrol thread berhenti
stop_event = threading.Event()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    if rc == 0:
        client.subscribe(mqtt_topic)
    else:
        print(f"Failed to connect, result code {rc}")

def on_disconnect(client, userdata, rc):
    print(f"Disconnected with result code {rc}")
    if rc != 0:
        print("Unexpected disconnection.")
        
def send_mqtt(client, topic):
    last_published = None
    while not stop_event.is_set():
        with lock:
            if status_dict:
                try:
                    status_json = json.dumps(status_dict)
                    if status_json != last_published:
                        print(f"Publishing to MQTT: {status_json}")
                        result = client.publish(topic, status_json)
                        if result.rc != mqtt.MQTT_ERR_SUCCESS:
                            print(f"Failed to send message to topic {topic}, return code: {result.rc}")
                        last_published = status_json
                except Exception as e:
                    print(f"Error while publishing to MQTT: {e}")
        time.sleep(1)


def on_message(client, userdata, msg):
    global total_spots, available_spots, spots_json, status_dict

    payload = msg.payload.decode()
    print(f"Message received: {payload}")

    try:
        new_spots_json = json.loads(payload)
        total_spots = len(new_spots_json)
        available_spots = sum([1 for spot in new_spots_json.values() if spot == 1])
        with lock:
            status_dict.update(new_spots_json)
            spots_json.update(new_spots_json)
        print(f"Updated status_dict: {status_dict}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/spots')
def spots():
    with lock:
        return jsonify({
            'availableSpots': available_spots,
            'totalSpots': total_spots,
            'spots': spots_json
        })

def run_flask():
    app.run(host='0.0.0.0', port=5002, debug=False)

def run_util2():
    rect_width, rect_height = width_kotak, height_kotak
    carp_park_positions_path = "CarParkPos"
    url = 'http://192.168.100.221'
    positions_with_labels = {
        (100, 200): "A1",
        (200, 200): "A2",
        (300, 200): "A3",
    }

    classifier = Park_classifier(carp_park_positions_path, rect_width, rect_height, positions_with_labels)
    client = mqtt.Client()
    mqtt_thread = threading.Thread(target=send_mqtt, args=(client, mqtt_topic))
    mqtt_thread.daemon = True
    mqtt_thread.start()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_server, 1883, 120)  # 120 detik keepalive
    client.loop_start()

    try:
        while not stop_event.is_set():
            try:
                imgResponse = urllib.request.urlopen(url)
                imgNp = np.array(bytearray(imgResponse.read()), dtype=np.uint8)
                img = cv2.imdecode(imgNp, -1)
                if img is None:
                    print("Error: Tidak dapat membaca gambar dari URL")
                    continue

                img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                processed_frame = classifier.implement_process(img)
                denoted_image, local_status_dict = classifier.classify(image=img, processed_image=processed_frame)

                with lock:
                    status_dict.update(local_status_dict)

            except Exception as e:
                print(f"Error in image processing: {e}")

    except KeyboardInterrupt:
        print("Stopping util2...")
    finally:
        client.loop_stop()
        print("util2 thread has stopped.")


def signal_handler(sig, frame):
    print("SIGINT received, stopping...")
    stop_event.set()  # Set the stop event to stop all threads
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    util2_thread = threading.Thread(target=run_util2)
    util2_thread.start()

    try:
        run_flask()
    finally:
        stop_event.set()  # Ensure that the threads are stopped
        util2_thread.join()  # Wait for util2_thread to finish before exiting
