"""DHT sensor helper module.

Provides a `get_reading()` function that returns the latest temperature/humidity
or an error message. If the adafruit libraries or hardware are unavailable,
the module falls back to a deterministic mock for development and testing.
"""
from typing import Dict, Optional
import time
import random
import json
import os
from datetime import datetime


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


# Interpretation rules and persistence
RECORDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dht_records.json")
os.makedirs(os.path.dirname(RECORDS_PATH), exist_ok=True)


def interpret_reading(reading: Dict[str, Optional[float]]) -> Dict[str, Optional[str]]:
    """Interpret temperature and humidity according to hive rules.

    Returns a dict with 'temperature_status' and 'humidity_status' keys.
    """
    temp = reading.get("temperature_c")
    hum = reading.get("humidity")
    temp_status = None
    hum_status = None

    if temp is None:
        temp_status = "unknown"
    else:
        if 32 <= temp <= 36:
            temp_status = "ideal"
        elif temp < 30:
            temp_status = "too_cold"
        elif temp > 38:
            temp_status = "overheating"
        else:
            temp_status = "warning"

    if hum is None:
        hum_status = "unknown"
    else:
        if 50 <= hum <= 65:
            hum_status = "ideal"
        elif hum < 40:
            hum_status = "too_dry"
        elif hum > 70:
            hum_status = "too_damp"
        else:
            hum_status = "warning"

    return {"temperature_status": temp_status, "humidity_status": hum_status}


def _save_record(record: Dict) -> None:
    try:
        records = []
        if os.path.exists(RECORDS_PATH):
            with open(RECORDS_PATH, "r", encoding="utf-8") as f:
                try:
                    records = json.load(f)
                except Exception:
                    records = []
        records.append(record)
        with open(RECORDS_PATH, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception:
        # Persistence errors shouldn't crash the sensor read path
        pass


def get_reading_with_interpretation() -> Dict:
    """Return a reading augmented with interpretation and save it with timestamp.

    Output shape:
    {
      "timestamp": "2025-09-25T12:34:56Z",
      "temperature_c": 33.2,
      "humidity": 56.1,
      "error": None,
      "interpretation": { ... }
    }
    """
    base = get_reading()
    interp = interpret_reading(base)
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "temperature_c": base.get("temperature_c"),
        "humidity": base.get("humidity"),
        "error": base.get("error"),
        "interpretation": interp,
    }
    _save_record(record)
    return record


def read_saved_records(limit: int = 100) -> list:
    """Return saved records (most recent last)."""
    if not os.path.exists(RECORDS_PATH):
        return []
    try:
        with open(RECORDS_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
            return records[-limit:]
    except Exception:
        return []
