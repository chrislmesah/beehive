from gpiozero import MotionSensor
from signal import pause
from datetime import datetime

pir = MotionSensor(17)  # GPIO17

def timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def motion_detected():
    print(f"{timestamp()} Motion detected!")

def motion_stopped():
    print(f"{timestamp()} Motion stopped.")

pir.when_motion = motion_detected
pir.when_no_motion = motion_stopped

print(f"{timestamp()} PIR sensor activated. Waiting for motion...")
pause()