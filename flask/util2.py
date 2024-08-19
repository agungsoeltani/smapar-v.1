import cv2
import urllib.request
import pickle
import numpy as np
import json
import paho.mqtt.client as mqtt
import threading
import time

height_kotak = 80
widht_kotak = 250

class Park_classifier:
    def __init__(self, carp_park_positions_path: str, rect_width: int = None, rect_height: int = None, positions_with_labels: dict = None):
        self.car_park_positions = self._read_positions(carp_park_positions_path)
        self.rect_height = height_kotak if rect_height is None else rect_height
        self.rect_width = widht_kotak if rect_width is None else rect_width
        self.positions_with_labels = positions_with_labels if positions_with_labels else {}

    def _read_positions(self, car_park_positions_path: str) -> list:
        try:
            car_park_positions = pickle.load(open(car_park_positions_path, 'rb'))
        except Exception as e:
            print(f"Error: {e}\nIt raised while reading the car park positions file.")
            car_park_positions = []
        return car_park_positions

    def classify(self, image: np.ndarray, processed_image: np.ndarray, threshold: int = 900) -> (np.ndarray, dict):
        empty_car_park = 0
        status_dict = {}

        for idx, (x, y) in enumerate(self.car_park_positions):
            col_start, col_stop = x, x + self.rect_width
            row_start, row_stop = y, y + self.rect_height
            crop = processed_image[row_start:row_stop, col_start:col_stop]
            count = cv2.countNonZero(crop)

            if count < threshold:
                empty_car_park += 1
                color, thick = (0, 255, 0), 5
                status = 1
            else:
                color, thick = (0, 0, 255), 2
                status = 0

            start_point, stop_point = (x, y), (x + self.rect_width, y + self.rect_height)
            cv2.rectangle(image, start_point, stop_point, color, thick)
            label = self.positions_with_labels.get((x, y), f"Spot {idx + 1}")
            label_text = f"{label}: {status}"
            cv2.putText(image, label_text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            status_dict[label] = status

        cv2.rectangle(image, (45, 30), (250, 75), (180, 0, 180), -1)
        ratio_text = f'Free: {empty_car_park}/{len(self.car_park_positions)}'
        cv2.putText(image, ratio_text, (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        return image, status_dict

    def implement_process(self, image: np.ndarray) -> np.ndarray:
        kernel_size = np.ones((3, 3), np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 1)
        thresholded = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
        blur = cv2.medianBlur(thresholded, 5)
        dilate = cv2.dilate(blur, kernel_size, iterations=1)
        return dilate

def send_mqtt(client, topic, status_dict):
    while True:
        if status_dict:
            try:
                status_json = json.dumps(status_dict)
                print(f"Publishing to MQTT: {status_json}")
                result = client.publish(topic, status_json)
                status = result.rc
                if status == 0:
                    print(f"Successfully published message to topic {topic}")
                else:
                    print(f"Failed to send message to topic {topic}")
            except Exception as e:
                print(f"Error while publishing to MQTT: {e}")
        else:
            print("Status dict is empty, not publishing to MQTT")
        time.sleep(1)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

def demostration(status_dict):
    rect_width, rect_height = widht_kotak, height_kotak
    carp_park_positions_path = "CarParkPos"
    url = 'http://192.168.100.221'
    positions_with_labels = {
        (100, 200): "A1",
        (200, 200): "A2",
        (300, 200): "A3",
        # Tambahkan lebih banyak posisi dan label sesuai kebutuhan Anda
    }

    classifier = Park_classifier(carp_park_positions_path, rect_width, rect_height, positions_with_labels)
    broker_address = "192.168.100.220"
    broker_port = 1883
    topic = "pnj_csc_TA_kel4"

    client = mqtt.Client("CarParkPublisher")
    client.on_connect = on_connect
    client.connect(broker_address, broker_port)
    client.loop_start()

    mqtt_thread = threading.Thread(target=send_mqtt, args=(client, topic, status_dict))
    mqtt_thread.daemon = True
    mqtt_thread.start()

    while True:
        try:
            imgResponse = urllib.request.urlopen(url)
            imgNp = np.array(bytearray(imgResponse.read()), dtype=np.uint8)
            img = cv2.imdecode(imgNp, -1)
            if img is None:
                print("Error: Tidak dapat membaca gambar dari URL")
                continue

            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            processed_frame = classifier.implement_process(img)
            denoted_image, status_dict = classifier.classify(image=img, processed_image=processed_frame)

            # Hapus atau nonaktifkan bagian ini agar tidak menampilkan gambar
            # cv2.imshow("Car Park Image which drawn According to empty or occupied", denoted_image)

            # Hapus atau nonaktifkan bagian ini agar tidak memerlukan input dari pengguna
            # k = cv2.waitKey(1)
            # if k & 0xFF == ord('q'):
            #     break
            # if k & 0xFF == ord('s'):
            #     cv2.imwrite("output.jpg", denoted_image)
            
            # Jika ingin menyimpan gambar hasil, aktifkan baris ini:
            # cv2.imwrite("output.jpg", denoted_image)

        except Exception as e:
            print(f"Error in main loop: {e}")

    # Hapus atau nonaktifkan ini karena tidak ada jendela yang dibuka
    # cv2.destroyAllWindows()
    client.loop_stop()
