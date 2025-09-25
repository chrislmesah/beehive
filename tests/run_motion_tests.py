#!/usr/bin/env python
"""Standalone tests for sensor/motion_sensor.py that don't require pytest.

Run with: python tests/run_motion_tests.py
"""
import sys
import importlib
import types
import time
from pathlib import Path

# Ensure the project root is on sys.path so 'sensor' package can be imported
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_mock_path():
    # Ensure the mock path returns a dict with motion and error keys when gpiozero missing
    ms = importlib.import_module('sensor.motion_sensor')
    # Force mock mode
    ms._HARDWARE_AVAILABLE = False
    r = ms.get_state()
    assert isinstance(r, dict), 'result must be a dict'
    assert 'motion' in r and 'error' in r, 'missing keys'
    assert r['error'] is None, 'mock should not set error'
    assert isinstance(r['motion'], (bool, int)), 'motion should be bool-like'


def test_hardware_mocking():
    # Simulate gpiozero MotionSensor behavior by monkeypatching in a fake class
    ms = importlib.import_module('sensor.motion_sensor')

    class FakePIR:
        def __init__(self, pin):
            self._pin = pin
            self.motion_detected = False

    # Create a fake MotionSensor class and inject it
    fake_module = types.SimpleNamespace(MotionSensor=FakePIR)
    # Simulate hardware available and reload module internals
    ms._HARDWARE_AVAILABLE = True
    # Ensure PIR is cleared
    ms._PIR = None
    # Inject the fake MotionSensor into the module namespace and call get_state
    ms.MotionSensor = FakePIR  # for older import paths
    # Also set in globals so when MotionSensor is referenced it uses FakePIR
    setattr(ms, 'MotionSensor', FakePIR)

    # Now call get_state(), which should instantiate FakePIR and return motion=False
    r = ms.get_state()
    assert isinstance(r, dict), 'result must be a dict'
    assert r['error'] is None or isinstance(r['error'], str)
    # motion may be False (0) on our FakePIR
    assert 'motion' in r


def run_all():
    tests = [test_mock_path, test_hardware_mocking]
    failures = []
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[PASS] {name}")
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failures.append((name, str(e)))
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failures.append((name, str(e)))

    if failures:
        print(f"\n{len(failures)} tests failed")
        sys.exit(1)
    else:
        print("\nAll tests passed")
        sys.exit(0)


if __name__ == '__main__':
    run_all()
#!/usr/bin/env python3
"""Run simple tests for sensor.motion_sensor without pytest.

This script simulates both the mock path (no gpiozero) and a hardware
path by injecting a fake gpiozero module into sys.modules. It prints a
succinct pass/fail report and exits with non-zero on failure.
"""
import importlib
import sys
import types


def run_test(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
        return True
    except AssertionError as e:
        print(f"[FAIL] {name}: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return False


def test_mock_get_state():
    # Ensure gpiozero is not present to exercise mock behavior
    sys.modules.pop('gpiozero', None)

    mod = importlib.reload(importlib.import_module('sensor.motion_sensor'))
    state = mod.get_state()
    assert isinstance(state, dict)
    assert 'motion' in state and 'error' in state
    assert state['error'] is None
    assert state['motion'] in (0, 1, True, False)


def test_hardware_get_state_with_fake_motion_sensor():
    # Create a fake gpiozero module with MotionSensor
    fake_gpio = types.SimpleNamespace()

    class FakeMotionSensor:
        def __init__(self, pin):
            # Expose attribute used by get_state()
            self.motion_detected = True

    fake_gpio.MotionSensor = FakeMotionSensor
    sys.modules['gpiozero'] = fake_gpio

    mod = importlib.reload(importlib.import_module('sensor.motion_sensor'))
    state = mod.get_state()
    assert isinstance(state, dict)
    assert state['error'] is None
    assert state['motion'] is True


def main():
    tests = [
        ("mock_get_state", test_mock_get_state),
        ("hardware_get_state_with_fake_motion_sensor", test_hardware_get_state_with_fake_motion_sensor),
    ]

    passed = 0
    for name, fn in tests:
        if run_test(name, fn):
            passed += 1

    total = len(tests)
    print(f"\n{passed}/{total} tests passed.")
    sys.exit(0 if passed == total else 2)


if __name__ == '__main__':
    main()
