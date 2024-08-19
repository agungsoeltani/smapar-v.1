from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Contoh variabel global untuk data
available_spots = 10
total_spots = 20

@app.route('/')
def index():
    return render_template('index.html', available_spots=available_spots, total_spots=total_spots)

@app.route('/spots')
def spots():
    # Ganti dengan logika yang sesuai untuk mengembalikan data dalam format JSON
    return jsonify({
        'availableSpots': available_spots,
        'totalSpots': total_spots,
        'spots': {}  # Ganti dengan data spot yang sesuai
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
