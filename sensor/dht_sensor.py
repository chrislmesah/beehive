"""DHT sensor helper module.

Provides a `get_reading()` function that returns the latest temperature/humidity
or an error message. If the adafruit libraries or hardware are unavailable,
the module falls back to a deterministic mock for development and testing.
"""
from typing import Dict, Optional
import time
import random


# Try to import hardware-specific libraries. If unavailable, we'll use a mock.
try:
    import board  # type: ignore
    import adafruit_dht  # type: ignore
    _HARDWARE_AVAILABLE = True
except Exception:
    _HARDWARE_AVAILABLE = False


_DEVICE = None

def _init_device():
    """Initialize and cache the DHT device if hardware is available."""
    global _DEVICE
    if not _HARDWARE_AVAILABLE:
        return
    if _DEVICE is None:
        # Use DHT11 on GPIO4 (physical pin 7) by default to preserve original behavior.
        _DEVICE = adafruit_dht.DHT11(board.D4)


def _mock_reading() -> Dict[str, Optional[float]]:
    """Return a deterministic mock reading for development.

    The values vary slightly each call so the UI can show changes.
    """
    base_temp = 22.0
    base_hum = 55.0
    # small deterministic jitter
    jitter_t = (time.time() % 10 - 5) * 0.02
    jitter_h = (time.time() % 7 - 3.5) * 0.1
    return {
        "temperature_c": round(base_temp + jitter_t + (random.random() - 0.5) * 0.2, 1),
        "humidity": round(base_hum + jitter_h + (random.random() - 0.5) * 0.5, 1),
        "error": None,
    }


def get_reading() -> Dict[str, Optional[float]]:
    """Return a reading dict: {temperature_c, humidity, error}.

    If hardware is available the function attempts a read and returns any
    encountered error message in the `error` field. On failure or when
    hardware isn't available, the mock reading is returned and `error` may be set.
    """
    if not _HARDWARE_AVAILABLE:
        return _mock_reading()

    _init_device()
    try:
        # The Adafruit library exposes temperature and humidity properties.
        temperature_c = _DEVICE.temperature
        humidity = _DEVICE.humidity
        if temperature_c is None or humidity is None:
            return {"temperature_c": None, "humidity": None, "error": "Invalid sensor reading"}
        return {"temperature_c": round(float(temperature_c), 1), "humidity": round(float(humidity), 1), "error": None}

    except RuntimeError as e:
        # Common transient errors — return an error message but don't raise.
        return {"temperature_c": None, "humidity": None, "error": str(e)}
    except Exception as e:
        # For unexpected exceptions, try to clean up and return an error string.
        try:
            _DEVICE.exit()
        except Exception:
            pass
        return {"temperature_c": None, "humidity": None, "error": str(e)}


if __name__ == "__main__":
    # Simple CLI loop for manual testing.
    while True:
        r = get_reading()
        if r.get("error"):
            print("Error:", r["error"])
        else:
            print(f"Temp={r['temperature_c']:0.1f}°C  Humidity={r['humidity']:0.1f}%")
        time.sleep(2.0)
