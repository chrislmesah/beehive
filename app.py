from flask import Flask, render_template, jsonify, request
from flask import Response

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
	return render_template("index.html")



@app.route('/camera_feed')
def camera_feed():
	try:
		from sensor.camera_stream import get_camera, mjpeg_generator
	except ImportError:
		return "Camera not available", 503

	# Allow optional tuning via query params
	size = request.args.get('size', '640x480')
	framerate = int(request.args.get('framerate', '15'))
	quality = int(request.args.get('quality', '80'))
	try:
		w, h = [int(x) for x in size.split('x')]
	except Exception:
		w, h = 640, 480

	cam = get_camera(size=(w, h), framerate=framerate, quality=quality)
	return Response(mjpeg_generator(cam, quality=quality), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/api/sensor")
def sensor_api():
	# Import here to avoid failing import if hardware libs aren't present at module import time
	from sensor.dht_sensor import get_reading
	from sensor.motion_sensor import get_state as get_motion_state

	reading = get_reading()
	motion = get_motion_state()

	# merge motion info into the response
	reading["motion"] = motion.get("motion")
	if motion.get("error"):
		reading["motion_error"] = motion.get("error")

	# Add an explicit status string for easier UI handling
	if motion.get("motion") is True:
		reading["motion_status"] = "detected"
	elif motion.get("motion") is False:
		reading["motion_status"] = "none"
	else:
		reading["motion_status"] = "unknown"

	# Debug log to server console
	print(f"/api/sensor -> temp={reading.get('temperature_c')} hum={reading.get('humidity')} motion={reading.get('motion_status')}")

	return jsonify(reading)


@app.route('/dht_records')
def dht_records_page():
	from sensor.dht_sensor import read_saved_records
	records = read_saved_records(200)
	return render_template('dht_records.html', records=records)


@app.route('/camera')
def camera_page():
	return render_template('camera.html')


@app.route('/api/dht_record')
def dht_record_api():
	# Return a new interpreted reading and save it
	from sensor.dht_sensor import get_reading_with_interpretation
	r = get_reading_with_interpretation()
	return jsonify(r)


if __name__ == "__main__":
	# Run in debug mode by default for local development.
	app.run(host="0.0.0.0", port=5000, debug=True)
