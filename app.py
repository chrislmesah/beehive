from flask import Flask, render_template, jsonify, request
from flask import Response

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
	# Provide the last saved DHT record (if any) and an initial motion status
	# so the dashboard can display data immediately on page load.
	from sensor.dht_sensor import read_saved_records
	from sensor.motion_sensor import get_state as get_motion_state

	last = read_saved_records(1)
	last_record = last[-1] if last else None
	motion = get_motion_state()
	if motion.get("motion") is True:
		motion_status = "Detected"
	elif motion.get("motion") is False:
		motion_status = "None"
	else:
		motion_status = "Unknown"

	return render_template("index.html", last_record=last_record, initial_motion_status=motion_status)



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
	from sensor.dht_sensor import get_reading, get_reading_with_interpretation, read_saved_records
	from sensor.motion_sensor import get_state as get_motion_state

	# Attempt a live read first. If the live read contains actual numeric
	# temperature and humidity values we return that (and persist it). If the
	# live read failed, fall back to the last persisted valid record so the
	# UI always has something to display immediately.
	base = get_reading()
	reading = {}
	if base.get('temperature_c') is None or base.get('humidity') is None:
		# fallback to last saved
		saved = read_saved_records(1)
		if saved:
			last = saved[-1]
			reading['temperature_c'] = last.get('temperature_c')
			reading['humidity'] = last.get('humidity')
			reading['timestamp'] = last.get('timestamp')
			reading['interpretation'] = last.get('interpretation')
		else:
			reading['temperature_c'] = None
			reading['humidity'] = None
	else:
		# valid live read: obtain an interpreted record (this also persists it)
		rec = get_reading_with_interpretation()
		reading['temperature_c'] = rec.get('temperature_c')
		reading['humidity'] = rec.get('humidity')
		reading['timestamp'] = rec.get('timestamp')
		reading['interpretation'] = rec.get('interpretation')
	motion = get_motion_state()

	# merge motion info into the response
	reading["motion"] = motion.get("motion")
	# Do not expose transient error strings in the API response. Keep only
	# the measured values and motion boolean/status so the UI doesn't show
	# low-level error messages.

	# Add an explicit status string for easier UI handling
	if motion.get("motion") is True:
		reading["motion_status"] = "detected"
	elif motion.get("motion") is False:
		reading["motion_status"] = "none"
	else:
		reading["motion_status"] = "unknown"

	# Remove any transient 'error' keys from sensors before returning
	reading.pop('error', None)
	reading.pop('motion_error', None)

	# Debug log to server console (concise)
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


@app.route('/dht_graph')
def dht_graph_page():
	return render_template('dht_graph.html')


@app.route('/api/dht_records')
def dht_records_api():
	from sensor.dht_sensor import read_saved_records
	records = read_saved_records(1000)
	return jsonify(records)


@app.route('/api/dht_record')
def dht_record_api():
	# Return a new interpreted reading and save it
	from sensor.dht_sensor import get_reading_with_interpretation
	r = get_reading_with_interpretation()
	return jsonify(r)


if __name__ == "__main__":
	# Run in debug mode by default for local development.
	app.run(host="0.0.0.0", port=5000, debug=True)
