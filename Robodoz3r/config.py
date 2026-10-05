"""Robodoz3r wiring and movement tuning for EV3 MicroPython."""

from pybricks.parameters import Direction, Port


LEFT_TRACK_PORT = Port.C
RIGHT_TRACK_PORT = Port.B
BLADE_PORT = Port.A
INFRARED_SENSOR_PORT = Port.S4

# Positive track speed must move forward; positive blade angle must lift.
LEFT_TRACK_DIRECTION = Direction.COUNTERCLOCKWISE
RIGHT_TRACK_DIRECTION = Direction.COUNTERCLOCKWISE
BLADE_DIRECTION = Direction.CLOCKWISE

DRIVE_SPEED = 240  # Motor degrees per second.
TURN_SPEED = 180
BLADE_SPEED = 120
BLADE_LIFT_ANGLE = 60  # Motor degrees above the manually set resting position.
BLADE_MOVE_TIME = 600  # Time allowed for each blade gesture.
OBSTACLE_DISTANCE = 55  # Infrared proximity units (0-100); allow for the recessed sensor.

# All times are milliseconds.
LOOP_DELAY = 50
GREETING_TIME = 800
BACKUP_TIME = 650
TURN_TIME = 700
DANCE_BEAT_TIME = 600
DANCE_INTERVAL_MIN = 12000
DANCE_INTERVAL_MAX = 20000
