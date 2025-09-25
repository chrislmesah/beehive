"""Motion sensor helper module.

Provides a `get_state()` function returning {'motion': bool, 'error': Optional[str]}.
When run as __main__ it will attach event handlers and block waiting for events
to preserve original behavior.
"""
from typing import Dict, Optional
from datetime import datetime

_HARDWARE_AVAILABLE = True
_PIR = None
_last_state = None  # tracks last known motion state (True/False/None)
_LED = None

try:
    from gpiozero import MotionSensor  # type: ignore
    from gpiozero import LED  # type: ignore
except Exception:
    # gpiozero may not be available in test or non-RPi environments.
    _HARDWARE_AVAILABLE = False


def timestamp() -> str:
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def _mock_state() -> Dict[str, Optional[object]]:
    # Simple deterministic mock: alternate based on seconds parity
    motion = int(datetime.now().timestamp()) % 10 < 5
    return {"motion": motion, "error": None}


def get_state() -> Dict[str, Optional[object]]:
    """Return current PIR state.

    Returns a dict: {"motion": bool or None, "error": str or None}.
    """
    if not _HARDWARE_AVAILABLE:
        return _mock_state()

    global _PIR
    if _PIR is None:
        try:
            _PIR = MotionSensor(17)
        except Exception as e:
            return {"motion": None, "error": str(e)}

    try:
        motion = bool(_PIR.motion_detected)
        # Keep _last_state and LED in sync when queried
        _update_state(motion)
        return {"motion": motion, "error": None}
    except Exception as e:
        return {"motion": None, "error": str(e)}


def motion_detected():
    # Called by gpiozero when motion starts. Use the updater to avoid repeated messages.
    _update_state(True)


def motion_stopped():
    # Called by gpiozero when motion stops. Use the updater to avoid repeated messages.
    _update_state(False)


def _update_state(new_state: Optional[bool]):
    """Update the last-known state and print only if it changed.

    new_state: True => motion detected, False => no motion, None => unknown/error
    """
    global _last_state, _LED
    if new_state == _last_state:
        return
    _last_state = new_state

    # Ensure LED object exists (best-effort)
    if _LED is None and _HARDWARE_AVAILABLE:
        try:
            _LED = LED(2)
        except Exception:
            _LED = None

    # Toggle LED according to motion
    try:
        if _LED is not None:
            if new_state is True:
                _LED.on()
            else:
                _LED.off()
    except Exception:
        pass

    if new_state is True:
        print(f"{timestamp()} Motion detected")
    elif new_state is False:
        print(f"{timestamp()} Motion stopped")
    else:
        print(f"{timestamp()} Motion state unknown")


if __name__ == "__main__":
    # Attach event handlers and block, preserving original script behavior.
    if not _HARDWARE_AVAILABLE:
        print(f"{timestamp()} gpiozero not available — running in mock mode")
        try:
            while True:
                s = get_state()
                # Use the same state updater so messages only print on changes
                _update_state(bool(s['motion']) if s.get('motion') is not None else None)
                import time

                time.sleep(2)
        except KeyboardInterrupt:
            pass
    else:
        _PIR = MotionSensor(17)
        _PIR.when_motion = motion_detected
        _PIR.when_no_motion = motion_stopped
        print(f"{timestamp()} PIR sensor activated. Waiting for motion...")
        from signal import pause

        pause()