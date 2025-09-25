import cv2
import numpy as np
import time
import sys
import importlib

# Try to ensure system-installed libcamera bindings are available inside
# the project's virtualenv by adding common dist-packages locations.
for _p in ("/usr/lib/python3/dist-packages", "/usr/lib/python3.11/dist-packages"):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def is_camera_available():
    # Prefer picamera2/libcamera when available
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        time.sleep(1)
        picam2.stop()
        print("Camera detected (picamera2) ✅")
        return True
    except Exception as e:
        # Try OpenCV VideoCapture fallback
        try:
            cap = cv2.VideoCapture(0)
            if not cap or not cap.isOpened():
                print(f"Camera not detected ❌ (picamera2 and OpenCV failed): {e}")
                return False
            cap.release()
            print("Camera detected (OpenCV VideoCapture) ✅")
            return True
        except Exception as e2:
            print(f"Camera not detected ❌: {e} / fallback error: {e2}")
            return False

def get_camera_feed():
    # Try picamera2 first
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        time.sleep(1)
        frame = picam2.capture_array()
        picam2.stop()
        return frame
    except Exception as e:
        # Fallback to OpenCV VideoCapture
        try:
            cap = cv2.VideoCapture(0)
            if not cap or not cap.isOpened():
                print(f"Error getting camera feed: picamera2 failed and OpenCV can't open camera: {e}")
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
                print("OpenCV capture failed: no frame returned")
                return None
            return frame
        except Exception as e2:
            print(f"Error getting camera feed: {e} / fallback error: {e2}")
            return None

# --- Settings ---
SAVE_IMAGES = False       # Set to True if you want to store pictures
motion_threshold = 5      # how many consecutive frames before we trigger detection
sensitivity = 200         # contour area threshold (lower = more sensitive)

# Initialize camera
if __name__ == "__main__":
    available = is_camera_available()
    if available:
        print("Camera feed test: capturing one frame...")
        frame = get_camera_feed()
        if frame is not None:
            print("Frame captured successfully.")
        else:
            print("Failed to capture frame.")
    else:
        print("Camera not available. Exiting.")
    # End of test run. For continuous monitoring use `sensor.camera_stream` or
    # import and call the functions in this module from another script.
