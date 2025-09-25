import importlib
import types


def test_mock_get_state(monkeypatch):
    # Ensure gpiozero import fails to exercise mock behavior.
    # We'll reload the module after forcing an ImportError for gpiozero.
    monkeypatch.setitem(__import__('sys').modules, 'gpiozero', None)

    # Reload the module to pick up the monkeypatched import state.
    mod = importlib.reload(importlib.import_module('sensor.motion_sensor'))

    state = mod.get_state()
    assert isinstance(state, dict)
    assert 'motion' in state and 'error' in state
    # In mock mode motion should be a bool-like value (0/1/True/False)
    assert state['motion'] in (0, 1, True, False)
    assert state['error'] is None


def test_hardware_get_state_with_mocked_motion_sensor(monkeypatch):
    # Simulate gpiozero being available and MotionSensor providing motion_detected
    fake_gpio = types.SimpleNamespace()

    class FakeMotionSensor:
        def __init__(self, pin):
            self.motion_detected = True

    fake_gpio.MotionSensor = FakeMotionSensor

    # Insert fake gpiozero module into sys.modules so import in sensor module finds it
    monkeypatch.setitem(__import__('sys').modules, 'gpiozero', fake_gpio)

    # Reload the module so it uses the fake gpiozero
    mod = importlib.reload(importlib.import_module('sensor.motion_sensor'))

    state = mod.get_state()
    assert isinstance(state, dict)
    assert state['error'] is None
    # The FakeMotionSensor sets motion_detected True
    assert state['motion'] is True
import importlib
import sys
import types


def test_mock_state_when_gpiozero_missing(monkeypatch):
    # Ensure gpiozero is not importable
    monkeypatch.setitem(sys.modules, 'gpiozero', None)
    # reload the module to pick up the absence
    if 'sensor.motion_sensor' in sys.modules:
        del sys.modules['sensor.motion_sensor']
    mod = importlib.import_module('sensor.motion_sensor')
    state = mod.get_state()
    assert 'motion' in state
    assert state['error'] is None


def test_hardware_path_with_mocked_motion_sensor(monkeypatch):
    # Create a fake gpiozero.MotionSensor class
    class FakeMotionSensor:
        def __init__(self, pin):
            self._state = True

        @property
        def motion_detected(self):
            return self._state

    fake_gpio = types.SimpleNamespace(MotionSensor=FakeMotionSensor)
    monkeypatch.setitem(sys.modules, 'gpiozero', fake_gpio)

    # reload module
    if 'sensor.motion_sensor' in sys.modules:
        del sys.modules['sensor.motion_sensor']
    mod = importlib.import_module('sensor.motion_sensor')
    s = mod.get_state()
    assert s['error'] is None
    assert isinstance(s['motion'], bool)