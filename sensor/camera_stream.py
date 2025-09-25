"""Camera streaming helper for MJPEG responses.

Provides a thread-safe frame generator using picamera2 and OpenCV to encode
JPEG frames suitable for multipart/x-mixed-replace streaming in Flask.
If picamera2 isn't available the module raises ImportError on initialization.
"""
from typing import Generator
import io
import threading
import time

try:
    from picamera2 import Picamera2
except Exception:
    # picamera2 may depend on system-installed `libcamera` bindings which
    # live in /usr/lib/python3/dist-packages on Debian-based systems. Try
    # adding that path at runtime so virtualenvs can import the system
    # bindings when available.
    import sys
    import importlib
    sys_path_added = False
    for p in ("/usr/lib/python3/dist-packages", "/usr/lib/python3.11/dist-packages"):
        if p not in sys.path:
            sys.path.insert(0, p)
            sys_path_added = True
    try:
        from picamera2 import Picamera2
    except Exception:
        # As a last resort, allow fallback to OpenCV's VideoCapture by
        # signalling that picamera2 isn't available.
        Picamera2 = None

import cv2
import numpy as np


class CameraStream:
    def __init__(self, size=(640, 480), framerate: int = 15, quality: int = 80):
        self.size = size
        self.framerate = framerate
        self.quality = quality

        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={"size": size})
        # Best-effort: picamera2 may accept framerate in some backends via controls
        try:
            config['main']['format'] = config['main'].get('format', 'RGB888')
        except Exception:
            pass
        self.picam2.configure(config)
        self.picam2.start()
        # small warmup
        time.sleep(1)

        self.lock = threading.Lock()
        self.frame = None
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            img = self.picam2.capture_array()
            # encode to JPEG once and cache. Use quality param via imencode params.
            try:
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(self.quality)]
                ret, jpeg = cv2.imencode('.jpg', img, encode_params)
            except Exception:
                ret, jpeg = cv2.imencode('.jpg', img)

            if ret:
                with self.lock:
                    self.frame = jpeg.tobytes()
            else:
                time.sleep(0.01)

    def get_frame(self) -> bytes:
        with self.lock:
            return self.frame

    def stop(self):
        self.running = False
        try:
            self.thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.picam2.stop()
        except Exception:
            pass


_GLOBAL_CAMERA = None


def get_camera(size=(640, 480), framerate: int = 15, quality: int = 80) -> CameraStream:
    global _GLOBAL_CAMERA
    # Recreate camera if configuration changes
    if _GLOBAL_CAMERA is None:
        _GLOBAL_CAMERA = CameraStream(size=size, framerate=framerate, quality=quality)
    else:
        try:
            if _GLOBAL_CAMERA.size != size or _GLOBAL_CAMERA.quality != quality:
                _GLOBAL_CAMERA.stop()
                _GLOBAL_CAMERA = CameraStream(size=size, framerate=framerate, quality=quality)
        except Exception:
            pass
    return _GLOBAL_CAMERA


def mjpeg_generator(cam: CameraStream, quality: int = 80) -> Generator[bytes, None, None]:
    boundary = b'--frame'
    while True:
        frame = cam.get_frame()
        if frame:
            yield boundary + b'\r\n' + b'Content-Type: image/jpeg\r\n' + b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n' + frame + b'\r\n'
        else:
            time.sleep(0.01)
