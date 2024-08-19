from threading import Lock

class ParkingData:
    def __init__(self):
        self.available_spots = 1 
        self.total_spots = 10
        self.spots = {
            "Spot 1": 0,
            "Spot 2": 0,
            "Spot 3": 0,
            "Spot 4": 0,
            "Spot 5": 0,
            "Spot 6": 0,
            "Spot 7": 0,
            "Spot 8": 0,
            "Spot 9": 0,
            "Spot 10": 0,
        }
        self.mqtt_connected = False
        self.lock = Lock()  # Lock untuk menghindari akses bersamaan

    def update_data(self, data):
        with self.lock:
            # Update data berdasarkan payload yang diterima
            if 'availableSpots' in data:
                self.available_spots = data['availableSpots']
            if 'totalSpots' in data:
                self.total_spots = data['totalSpots']
            if 'spots' in data:
                # Menyimpan data spot yang diterima dari MQTT
                self.spots.update(data['spots'])
                # Mengurutkan spots setelah update
                self.spots = dict(sorted(self.spots.items(), key=lambda item: int(item[0].split('Spot ')[-1])))

    def get_serializable_data(self):
        with self.lock:
            return {
                'availableSpots': self.available_spots,
                'totalSpots': self.total_spots,
                'spots': self.spots
            }

# Instance global dari ParkingData
parking_data = ParkingData()

