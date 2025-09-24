from flask import Flask, render_template, jsonify

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
	return render_template("index.html")


@app.route("/api/sensor")
def sensor_api():
	# Import here to avoid failing import if hardware libs aren't present at module import time
	from sensor.dht_sensor import get_reading

	reading = get_reading()
	return jsonify(reading)


if __name__ == "__main__":
	# Run in debug mode by default for local development.
	app.run(host="0.0.0.0", port=5000, debug=True)
